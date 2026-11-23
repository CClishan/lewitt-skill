# Binance — Design DNA

- Source: https://www.binance.com/en
- Mode: full  ·  Captured: 2026-11-23T12:28:11+00:00
- Pages inspected: 4 (https://www.binance.com/en, https://www.binance.com/en/crypto/convert, https://www.binance.com/en/markets/overview, https://www.binance.com/en/futures/home)
- Browser capture: isolated (fresh context)
- Viewport: 1440x900
- Limitations:
  - binance.com redirects to www.binance.com/en; output folder keeps the requested binance.com name.
  - Menu dropdowns and modals were not opened (reversible-state risk); their states are unknown.
  - The homepage h1 is a 16px utility node, so display sizes were read from the hero figure and h2, not semantic tags.
  - prefers-reduced-motion was found on 2 of 4 pages; the CSSOM scan disagrees page to page.
  - BinancePlex appears on only 2 of 4 pages, so its role is inferred.

## Design Map

### Measurements

| Category | Value | Status | Evidence |
| --- | --- | --- | --- |
| Color / canvas | `#181A20 = rgb(24,26,32) on 93.8% (home) and 98.3% (markets); #0B0E11 floor covers 52.2% of futures` | Observed / 实测 | e-canvas, e-canvas-markets, e-surface-floor, e-canvas-futures |
| Color / surfaces | `raised #29313D (2.2%), input well #1E2329 (3.5%), border #333B47, stronger border #3D4452` | Observed / 实测 | e-surface-raised, e-surface-deep, e-stroke-strong, e-stroke-subtle |
| Color / text | `#EAECEF body, #929AA5 secondary, #707A8A tertiary, #202630 on yellow` | Observed / 实测 | e-ink, e-ink-muted, e-ink-faint, e-ink-on-brand |
| Color / brand | `#F0B90B for logo and hero figure, #FCD535 for filled CTA; fill reaches 5.3% of the futures page` | Observed / 实测 | e-brand, e-brand-other, e-display-72 |
| Color / semantic | `up #2EBD85, down #F6465D, always as text colour` | Observed / 实测 | e-up, e-down |
| Typography / families | `BinanceNova everywhere (669 / 969 nodes); BinancePlex on only 2 of 4 pages, 10 nodes` | Observed / 实测 | e-font-nova, e-font-nova-other, e-font-plex |
| Typography / scale | `72px figure, 40px/600 headline, 32px/700 page title, 18px/500 card title, 14px UI, 12px body, 8px legal` | Observed / 实测 | e-display-72, e-h2, e-h1-markets, e-h3, e-body, e-body-markets, e-sizes, e-sizes-markets |
| Typography / weights | `400 x91 and 500 x77 dominate; 600 x16 for headlines; 700 x8 (hero figure, markets h1)` | Observed / 实测 | e-weights, e-weights-markets |
| Shape / radius | `buttons 10px, cards/tabs/pills 8px, option tiles 16px, chips 4px, coin icons 50%, badges 9999px` | Observed / 实测 | e-radii-home, e-radii-markets, e-radii-futures |
| Shape / depth | `one shadow in the whole sample (cookie overlay); every other layer separated by a #333B47 hairline on a #29313D fill` | Observed / 实测 | e-shadow, e-stroke-strong, e-surface-raised |
| Motion | `0.7s transform cubic-bezier(0,0,0.2,1); 0.2s color/bg/border cubic-bezier(0.4,0,0.2,1); 0.15s linear micro-states` | Observed / 实测 | e-motion, e-motion-markets |
| Interaction affordances | `:focus-visible on all sampled pages; prefers-reduced-motion on pages 1 and 3 but not 2 and 4` | Observed / 实测 | e-focus, e-focus-other |
| Spacing | `8px x82, 16px x55, 20px x27, 4px x27, 24px gutters, 64px block spacing` | Observed / 实测 | e-space |
| Layout | `1440px container with 24px padding (home), 1200px content (markets), 3 x 376px cards with 48/36 gaps (futures)` | Observed / 实测 | e-container, e-container-markets, e-grid |

### Patterns

**Yellow is an amount, not a mood** — Brand yellow is confined to the CTA fill, the hero statistic, the active-tab underline and a few links; it never fills a section or sets body copy.
- Goal: On a page showing dozens of numbers, yellow can only mean 'this is the figure' or 'this is the action'.
- Evidence: e-brand, e-canvas, e-stroke-strong

**Yellow expands with density** — Yellow fill is 0.3% of the marketing home page and 5.3% of the trading floor.
- Goal: Marketing reads dark with a highlight; the trading product reads brand-forward because product mode replaces marketing mode.
- Evidence: e-brand, e-brand-other, e-canvas-futures

**Three dark layers, no shadows** — Canvas #181A20, card #29313D, well #1E2329, separated by #333B47 hairlines; a single shadow exists in the sample.
- Goal: Depth survives on OLED and dim screens without blur halos over 12px price text.
- Evidence: e-surface-raised, e-surface-deep, e-stroke-strong, e-shadow

**Numbers get the largest type** — The hero figure is 72px while headlines are 40px and body 12px — a 6x ratio between statistic and prose.
- Goal: A reader scanning for a number never hunts; hierarchy is data > headline > body.
- Evidence: e-display-72, e-h2, e-body, e-sizes

**One UI family, one earned display face** — BinanceNova carries every surface; BinancePlex appears on 10 nodes in 2 of 4 pages.
- Goal: Keeps product pages uniform while letting campaign pages differ slightly.
- Evidence: e-font-nova, e-font-nova-other, e-font-plex

**A two-colour direction axis** — Gains use #2EBD85 and losses #F6465D, always as text, never as a filled badge.
- Goal: Direction stays legible at 12px without competing with the brand yellow.
- Evidence: e-up, e-down

**Radii track role** — Buttons 10px, cards and tabs 8px, large option tiles 16px, inline chips 4px.
- Goal: Silhouette alone tells a card from a button from a tile.
- Evidence: e-radii-home, e-radii-markets, e-radii-futures

**Hover is fast, panels are slow** — Colour and border hovers run at 0.15-0.2s; panel and image transforms at 0.7s.
- Goal: Interface feedback is immediate while promotional movement stays calm enough to read.
- Evidence: e-motion, e-motion-markets

### Tokens

| Token | CSS var | Type | Layer | Status | Value |
| --- | --- | --- | --- | --- | --- |
| `color/dark/900` | `--lw-dark-900` | color | primitive | observed | `#181A20` |
| `color/dark/1000` | `--lw-dark-1000` | color | primitive | observed | `#0B0E11` |
| `color/slate/700` | `--lw-slate-700` | color | primitive | observed | `#29313D` |
| `color/slate/800` | `--lw-slate-800` | color | primitive | observed | `#1E2329` |
| `color/slate/600` | `--lw-slate-600` | color | primitive | observed | `#333B47` |
| `color/slate/500` | `--lw-slate-500` | color | primitive | observed | `#3D4452` |
| `color/grey/100` | `--lw-grey-100` | color | primitive | observed | `#EAECEF` |
| `color/grey/400` | `--lw-grey-400` | color | primitive | observed | `#929AA5` |
| `color/grey/500` | `--lw-grey-500` | color | primitive | observed | `#707A8A` |
| `color/gold/400` | `--lw-gold-400` | color | primitive | observed | `#F0B90B` |
| `color/gold/300` | `--lw-gold-300` | color | primitive | observed | `#FCD535` |
| `color/on-gold` | `--lw-on-gold` | color | primitive | observed | `#202630` |
| `color/up` | `--lw-up` | color | primitive | observed | `#2EBD85` |
| `color/down` | `--lw-down` | color | primitive | observed | `#F6465D` |
| `color/canvas` | `--lw-canvas` | color | semantic | observed | `→ color/dark/900` |
| `color/surface` | `--lw-surface` | color | semantic | observed | `→ color/slate/700` |
| `color/well` | `--lw-well` | color | semantic | observed | `→ color/slate/800` |
| `color/border` | `--lw-border` | color | semantic | observed | `→ color/slate/600` |
| `color/border-strong` | `--lw-border-strong` | color | semantic | observed | `→ color/slate/500` |
| `color/text/primary` | `--lw-text-primary` | color | semantic | observed | `→ color/grey/100` |
| `color/text/secondary` | `--lw-text-secondary` | color | semantic | observed | `→ color/grey/400` |
| `color/text/tertiary` | `--lw-text-tertiary` | color | semantic | observed | `→ color/grey/500` |
| `color/brand` | `--lw-brand` | color | semantic | observed | `→ color/gold/400` |
| `color/action/bg` | `--lw-action-bg` | color | semantic | observed | `→ color/gold/300` |
| `color/action/fg` | `--lw-action-fg` | color | semantic | observed | `→ color/on-gold` |
| `color/trend/up` | `--lw-trend-up` | color | semantic | observed | `→ color/up` |
| `color/trend/down` | `--lw-trend-down` | color | semantic | observed | `→ color/down` |
| `font/ui` | `--lw-font-ui` | fontFamily | primitive | observed | `'BinanceNova', -apple-system, 'Helvetica Neue', Arial, sans-serif` |
| `font/display` | `--lw-font-display` | fontFamily | primitive | observed | `'BinancePlex', 'BinanceNova', -apple-system, sans-serif` |
| `font/body` | `--lw-font-body` | fontFamily | semantic | observed | `→ font/ui` |
| `font/campaign` | `--lw-font-campaign` | fontFamily | semantic | observed | `→ font/display` |
| `type/figure` | `--lw-type-figure` | dimension | component | observed | `72px` |
| `type/headline` | `--lw-type-headline` | dimension | component | observed | `40px` |
| `type/title` | `--lw-type-title` | dimension | component | observed | `18px` |
| `type/ui` | `--lw-type-ui` | dimension | component | observed | `14px` |
| `type/body` | `--lw-type-body` | dimension | component | observed | `12px` |
| `type/legal` | `--lw-type-legal` | dimension | component | observed | `8px` |
| `leading/body` | `--lw-leading-body` | number | component | observed | `1.33` |
| `weight/regular` | `--lw-weight-regular` | fontWeight | primitive | observed | `400` |
| `weight/medium` | `--lw-weight-medium` | fontWeight | primitive | observed | `500` |
| `weight/semibold` | `--lw-weight-semibold` | fontWeight | primitive | observed | `600` |
| `weight/bold` | `--lw-weight-bold` | fontWeight | primitive | observed | `700` |
| `radius/button` | `--lw-radius-button` | dimension | semantic | observed | `10px` |
| `radius/card` | `--lw-radius-card` | dimension | semantic | observed | `8px` |
| `radius/option` | `--lw-radius-option` | dimension | semantic | observed | `16px` |
| `radius/chip` | `--lw-radius-chip` | dimension | semantic | observed | `4px` |
| `radius/pill` | `--lw-radius-pill` | dimension | primitive | observed | `9999px` |
| `depth/overlay` | `--lw-depth-overlay` | shadow | component | observed | `-2px 0 14px rgba(0, 0, 0, 0.4), 0 0 6px rgba(0, 0, 0, 0.2)` |
| `motion/micro` | `--lw-motion-micro` | duration | primitive | observed | `150ms` |
| `motion/hover` | `--lw-motion-hover` | duration | primitive | observed | `200ms` |
| `motion/panel` | `--lw-motion-panel` | duration | primitive | observed | `700ms` |
| `motion/easing-standard` | `--lw-easing-standard` | easing | primitive | observed | `cubic-bezier(0.4, 0, 0.2, 1)` |
| `motion/easing-panel` | `--lw-easing-panel` | easing | primitive | observed | `cubic-bezier(0, 0, 0.2, 1)` |
| `space/unit` | `--lw-space-unit` | dimension | primitive | observed | `8px` |
| `space/block` | `--lw-space-block` | dimension | component | observed | `64px` |
| `layout/container` | `--lw-layout-container` | dimension | component | observed | `1440px` |
| `layout/container-pad` | `--lw-layout-pad` | dimension | component | observed | `24px` |

---

# Taste DNA

### Colour is assigned by role, not by hierarchy
- **Kind**: system
- **Trigger**: Designing a screen that shows prices, price changes, actions and promotions at once.
- **Decision**: One accent for brand and action, green/red for direction, blue-greys for everything else.
- **Chose**: a three-role colour system (brand, direction, neutral)   **Over**: a hue per category (per-coin colours, per-section accents, coloured badges)
- **Reason**: In a list of fifty numbers, a colour that could mean anything stops carrying meaning; three roles keep a glance reliable.
- **Evidence**: e-brand, e-up, e-down, e-ink  ·  patterns: p-semantic-pair, p-yellow-ratio
- **Status**: Observed / 实测

### Depth is a hairline, not a shadow
- **Kind**: restraint
- **Trigger**: Layering cards and inputs on a near-black canvas.
- **Decision**: Separate layers with #333B47 1px borders over a #29313D fill; one shadow exists in the whole sample.
- **Chose**: 1px hairlines plus a lifted fill   **Over**: a drop shadow on every card and panel
- **Reason**: On a dark canvas a shadow is invisible until it is strong enough to smear the 12px digits sitting on it.
- **Evidence**: e-surface-raised, e-stroke-strong, e-shadow  ·  patterns: p-nested-surfaces
- **Status**: Observed / 实测
- **Guardrail (enforced)**: `{"forbidCss": [], "forbidClass": ["(^|-)shadow-(?!none|sm|inner)[a-z]+-[a-z]+"], "max": {"box-shadow": {"value": "0", "unit": "px"}}, "note": "Exception: the single floating overlay panel measured at 14px/6px blur. Everything else is a 1px border."}`

### Data outranks copy
- **Kind**: craft
- **Trigger**: Deciding what to enlarge on a landing page that also has to sell a product.
- **Decision**: Scale the statistic to 72px, the headline to 40px/600, prose to 12px.
- **Chose**: a 72/40/12 scale biased toward numbers   **Over**: a balanced 48/28/16 marketing scale where copy and data compete
- **Reason**: The promise of an exchange is a number; making it the largest object lets a screenshot-free page still read as a product.
- **Evidence**: e-display-72, e-h2, e-body, e-sizes  ·  patterns: p-number-first
- **Status**: Observed / 实测

### The display face is earned, not standard
- **Kind**: restraint
- **Trigger**: Choosing type families across marketing and trading surfaces.
- **Decision**: BinanceNova everywhere; BinancePlex only on 10 nodes in 2 of 4 pages.
- **Chose**: a single UI family with a sparing display face   **Over**: a display/body pairing applied site-wide
- **Reason**: A second family used everywhere splits product identity from marketing; used sparingly it signals that this surface is different.
- **Evidence**: e-font-nova, e-font-plex  ·  patterns: p-one-frame-two-families
- **Status**: Observed / 实测
- **Guardrail (enforced)**: `{"forbidCss": [], "forbidClass": ["(^|-)font-(serif|display|mono)$"], "max": {}, "note": "A display face is allowed only on campaign blocks, never on tables, prices or controls."}`

## Open questions

- Is #FCD535 a pressed state of #F0B90B or a separate brand token?
- Does the futures floor #0B0E11 imply a second theme mode?
