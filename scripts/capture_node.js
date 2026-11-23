// lewitt — node capture driver (requires the `playwright` npm module).
// Isolation: launchPersistentContext in a throwaway profile => no inherited login state.
// Evaluation: CDP Runtime.evaluate (see eval_cdp.js).
// Env: DD_JOBS (JSON array), DD_EXTRACT (path to extract.js)
const { chromium } = require(process.env.LEWITT_PLAYWRIGHT || 'playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');
const lewittEvaluate = require('./eval_cdp');

const VIEWPORT = { width: 1440, height: 900 };

async function launchIsolated() {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'lewitt-profile-'));
  global.__lewittProfile = profile;
  const opts = { headless: true, viewport: VIEWPORT, ignoreHTTPSErrors: true };
  try {
    return await chromium.launchPersistentContext(profile, opts);
  } catch (e) {
    if (!/Executable doesn't exist|is not found/.test(String(e))) throw e;
    // stale Playwright pin: use the system Chrome once, and say so in the job result
    const ctx = await chromium.launchPersistentContext(profile, { ...opts, channel: 'chrome' });
    ctx.__channel = 'chrome';
    return ctx;
  }
}

(async () => {
  const jobs = JSON.parse(process.env.LEWITT_JOBS || '[]');
  const extractSrc = fs.readFileSync(process.env.LEWITT_EXTRACT, 'utf8');
  const ctx = await launchIsolated();
  const channel = ctx.__channel || 'chromium';
  const results = [];
  try {
    for (const job of jobs) {
      const page = await ctx.newPage();
      await page.goto(job.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(job.wait || 3000);
      await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
      await page.screenshot({ path: job.png, type: 'png' });
      const fullHeight = await lewittEvaluate(page, '() => document.documentElement.scrollHeight');
      let fullPng = null;
      if (job.full && fullHeight <= VIEWPORT.height * 6) {
        await page.screenshot({ path: job.fullPng, type: 'png', fullPage: true });
        fullPng = job.fullPng;
      }
      const dom = await lewittEvaluate(page, extractSrc);
      fs.writeFileSync(job.json, JSON.stringify(dom, null, 2));
      const extra = [];
      if (job.linksExpr && (job.maxPages || 1) > 1) {
        let links = [];
        try {
          links = (await lewittEvaluate(page, job.linksExpr)) || [];
        } catch (e) {
          extra.push({ index: 0, url: null, error: 'nav extraction failed: ' + String(e).slice(0, 200) });
        }
        let i = 1;
        for (const link of links) {
          if (i >= job.maxPages) break;
          i += 1;
          const p2 = await ctx.newPage();
          try {
            await p2.goto(link, { waitUntil: 'domcontentloaded', timeout: 45000 });
            await p2.waitForTimeout(2500);
            const png2 = path.join(path.dirname(job.png), `viewport-${i}.png`);
            await p2.screenshot({ path: png2, type: 'png' });
            const dom2 = await lewittEvaluate(p2, extractSrc);
            fs.writeFileSync(path.join(path.dirname(job.png), `dom-${i}.json`), JSON.stringify(dom2, null, 2));
            extra.push({ index: i, url: link, png: png2, json: path.join(path.dirname(job.png), `dom-${i}.json`) });
          } catch (e) {
            extra.push({ index: i, url: link, error: String(e).slice(0, 200) });
          } finally {
            await p2.close();
          }
        }
      }
      results.push({ url: job.url, png: job.png, fullPng, fullHeight, channel, dom, extra });
      await page.close();
    }
  } finally {
    await ctx.close();
    // the profile is throwaway: leaving it behind leaks state and fills the temp dir
    try { fs.rmSync(global.__lewittProfile, { recursive: true, force: true }); } catch (e) {}
  }
  process.stdout.write(JSON.stringify(results));
})().catch((e) => {
  console.error(String(e && e.stack ? e.stack : e));
  process.exit(1);
});
