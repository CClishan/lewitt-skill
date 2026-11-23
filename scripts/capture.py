#!/usr/bin/env python3
"""design-dna — browser capture adapter. Prefers an isolated, fresh browser context.

Order of preference (see references/sense.md):
  1. node playwright  — launchPersistentContext in a throwaway profile (auto, if `playwright` resolves)
  2. external driver  — any command you supply (--driver / DD_CAPTURE_CMD) that opens, evals, shots
No silent fallback: if neither is available the capture FAILS instead of measuring a
logged-in or wrong surface (R1: no fabricated evidence).

Writes into `<out>/capture/`:
  dom.json            raw extract.js payload for the main page
  viewport.png        primary visual reference (screenshot is the composition truth)
  fullpage.png        when the page is <= 6 viewports tall
  dom-<n>.json        extra pages when --pages > 1
  meta.json           capture provenance for dna.json meta

Examples:
  npm i playwright   # one-time, anywhere; pass --node-cwd
  python3 capture.py linear.app --dest ./out --node-cwd ~/.dd
  python3 capture.py https://linear.app --pages 3 --node-cwd ~/.dd
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import os
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTRACT = HERE / "extract.js"
SKIP = r"/^(login|logout|signup|sign-in|register|auth|account|checkout|cart|password|reset)(/|$)/"
NAV_LINKS = (
    "() => { const seen = new Set([location.pathname]); const re = new RegExp(" + json.dumps(SKIP) + ");"
    " const out = [];"
    " document.querySelectorAll('nav a, header a, [role=navigation] a').forEach(a => {"
    "   try { const u = new URL(a.href);"
    "     if (u.hostname !== location.hostname) return;"
    "     if (re.test(u.pathname)) return;"
    "     if (seen.has(u.pathname)) return;"
    "     if (u.pathname === '/' && location.pathname !== '/') return;"
    "     if (!(a.innerText || '').trim()) return;"
    "     seen.add(u.pathname); out.push(u.origin + u.pathname);"
    "   } catch (e) {} });"
    " return out.slice(0, 8); }"
)


def normalize(url: str) -> str:
    if "://" not in url:
        url = "https://" + url
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(parts._replace(fragment=""))


def domain_of(url: str) -> str:
    host = urllib.parse.urlsplit(normalize(url)).hostname or url
    return host[4:] if host.startswith("www.") else host


# ---------------------------------------------------------------- external driver (optional)
class External:
    """Any command that can navigate/evaluate in its own isolated context.

    DD_CAPTURE_CMD carries the executable; the adapter speaks to it with three verbs:
      <cmd> open <url> | <cmd> eval <file-or-expr> | <cmd> shot <path> [--full]
    Most people do not need this: install `playwright` (node) and the node driver is used.
    """

    def __init__(self, cmd: str):
        self.cmd = cmd.split()

    def run(self, *args: str, timeout: int = 180) -> str:
        proc = subprocess.run(self.cmd + list(args), capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"{' '.join(self.cmd + list(args))} failed: {proc.stderr.strip()[-400:]}")
        return proc.stdout

    def open(self, url: str) -> None:
        self.run("open", url)

    def js(self, expr: str) -> str:
        return unwrap(self.run("eval", expr))

    def screenshot(self, path: Path, full: bool = False) -> None:
        self.run("shot", str(path), *(["--full"] if full else []))


def find_npm_root(binary: str) -> str | None:
    """Playwright's browser binaries are version-matched to an installed npm module; surface it."""
    if shutil.which(binary.split()[0]) and binary.endswith(".sh") and "npx" in Path(binary).read_text(errors="ignore"):
        return str(Path.home() / ".npm-global/lib/node_modules")
    for base in (Path.home() / "node_modules", Path.home() / ".codex/node_modules"):
        if (base / "playwright").exists():
            return str(base)
    try:
        out = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, env={**__import__("os").environ, "npm_config_cache": "/tmp/dd-npm-cache"})
        if out.returncode == 0 and (Path(out.stdout.strip()) / "playwright").exists():
            return out.stdout.strip()
    except Exception:
        pass
    return None


def unwrap(cli_out: str) -> str:
    """playwright-cli prints `### Result` then the value; be tolerant across versions."""
    text = cli_out.strip()
    if "### Result" in text:
        text = text.split("### Result", 1)[1]
        text = text.split("###", 1)[0].strip()
    for line in text.splitlines():
        if line.strip().startswith(("{", "[", '"')):
            return line.strip()
    return text.strip()


def newest_png() -> Path | None:
    roots = [Path.cwd(), Path.home() / ".cache" / "playwright-cli", Path.home() / ".playwright-cli",
             Path.home() / ".local" / "share" / "playwright-cli"]
    candidates: list[Path] = []
    for root in roots:
        if root.exists():
            candidates.extend(root.rglob("*.png"))
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


# ---------------------------------------------------------------- playwright (node) driver
class NodePW:
    SCRIPT = (HERE / "capture_node.js").read_text()

    def __init__(self, cwd: Path | None = None):
        self.cwd = cwd

    def available(self) -> bool:
        try:
            out = subprocess.run(["node", "-e", "require.resolve('playwright')"], capture_output=True, text=True, cwd=self.cwd)
            return out.returncode == 0
        except Exception:
            return False

    def run(self, jobs: list[dict]) -> list[dict]:
        proc = subprocess.run(
            ["node", str(HERE / "capture_node.js")],
            env={**os.environ, "DD_JOBS": json.dumps(jobs), "DD_EXTRACT": str(EXTRACT),
                 "DD_PLAYWRIGHT": str(Path(self.cwd or HERE) / "node_modules" / "playwright")},
            cwd=self.cwd,
            capture_output=True, text=True, timeout=600,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip()[-800:])
        return json.loads(proc.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--dest", default=".")
    ap.add_argument("--pages", type=int, default=1, help="total pages to inspect (1 + up to 3 representative)")
    ap.add_argument("--wait", type=int, default=3000)
    ap.add_argument("--node-cwd", default=str(Path.home() / ".dd"),
                    help="dir where the `playwright` npm module is resolvable")
    ap.add_argument("--driver", default=None, help="external driver command (open/eval/shot verbs); default: node playwright")
    args = ap.parse_args()

    url = normalize(args.url)
    domain = domain_of(url)
    out = Path(args.dest).expanduser().resolve() / domain
    cap = out / "capture"
    cap.mkdir(parents=True, exist_ok=True)
    meta = {
        "source": url, "domain": domain,
        "capturedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "driver": None, "isolated": False, "isolationNote": None,
        "pages": [], "crawl": {"pages": [url], "budget": "1+3"}, "errors": [],
    }

    jobs = [{
        "url": url, "png": str(cap / "viewport.png"), "fullPng": str(cap / "fullpage.png"),
        "full": True, "json": str(cap / "dom.json"), "wait": args.wait,
        "linksExpr": NAV_LINKS, "maxPages": max(1, args.pages),
    }]

    node_pw = NodePW(cwd=args.node_cwd)
    used = None
    if node_pw.available():
        try:
            first = node_pw.run(jobs)[0]
            for extra in first.get("extra", []):
                if extra.get("error"):
                    meta["errors"].append(f"page {extra.get('index')} {extra.get('url')}: {extra['error']}")
                    continue
                meta["pages"].append({"url": extra["url"], "shot": Path(extra["png"]).name})
            meta["isolated"] = True
            used = f"playwright(node 1.65+ via CDP evaluate; throwaway profile, channel={first.get('channel')})"
        except Exception as exc:
            meta["errors"].append(f"node playwright: {str(exc)[-400:]}")
    else:
        meta["errors"].append("node playwright: module not resolvable (npm i playwright)")

    if used is None and (args.driver or os.environ.get("DD_CAPTURE_CMD")):
        drv = External(args.driver or os.environ["DD_CAPTURE_CMD"])
        try:
            drv.open(url)
            drv.screenshot(cap / "viewport.png")
            (cap / "dom.json").write_text(drv.js(EXTRACT.read_text()), encoding="utf-8")
            used = f"external driver: {drv.cmd[0]}"
            meta["isolated"] = True          # only if the driver guarantees a fresh context
            meta["isolationNote"] = "external driver: verify it starts from a fresh context"
        except Exception as exc:
            print(f"FAIL: external driver: {exc}", file=sys.stderr)
            return 3

    if used is None:
        meta["captureIsolated"] = False
        meta["isolationNote"] = "no isolated driver available; capture did NOT run"
        (cap / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print("FAIL: no browser driver. Install playwright:\n"
              "  mkdir -p ~/.dd && cd ~/.dd && npm i playwright && npx playwright install chromium\n"
              "then rerun (defaults to --node-cwd ~/.dd) or provide --driver.\n"
              f"existing tooling (never used silently): {sorted(s for s in ('playwright-cli', 'chrome') if shutil.which(s))}",
              file=sys.stderr)
        return 2

    meta["driver"] = used
    meta["crawl"]["pages"] = [url] + [p["url"] for p in meta["pages"]]
    for p in meta["crawl"]["pages"]:
        if p not in [x["url"] for x in meta["pages"]]:
            meta["pages"].append({"url": p})

    dom_path = cap / "dom.json"
    if dom_path.exists():
        dom = json.loads(dom_path.read_text())
        vp = dom.get("viewport", {})
        meta["viewport"] = f"{vp.get('width')}x{vp.get('height')}"
        meta["title"] = dom.get("title")
        for e in dom.get("errors", []):
            meta["errors"].append(f"extract.{e['section']}: {e['error']}")
        if dom.get("truncated"):
            meta["errors"].append("extract payload truncated (>60KB); low-signal fields trimmed")
        if not dom.get("url"):
            print("FAIL: extractor returned no data (driver evaluated JS but got nothing back)", file=sys.stderr)
            return 4
    else:
        print("FAIL: capture produced no dom.json", file=sys.stderr)
        return 4

    (cap / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps({
        "dest": str(out), "domain": domain, "driver": used, "isolated": meta["isolated"],
        "pages": meta["crawl"]["pages"], "errors": meta["errors"],
        "files": sorted(p.name for p in cap.iterdir()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
