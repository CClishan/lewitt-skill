# Stripe — Design DNA

- Source: https://stripe.com/
- Mode: full  ·  Captured: 2026-11-23T12:17:46+00:00
- Pages inspected: 4 (https://stripe.com/, https://stripe.com/pricing, https://stripe.com/products, https://stripe.com/contact/sales)
- Incremental run: scope taste; frozen meta, evidence, measurements, patterns, tokens (at 2026-11-23T12:41:19+00:00)
- Browser capture: isolated (fresh context)
- Viewport: 1440x900
- Limitations:
  - stripe.com redirects to /en-sg on this network; copy and pricing are the SG locale.
  - The hero gradient is an image (1392x975); its colours are sampled from pixels, not CSS.
  - Rendered font is sohne-var; the loaded face filename was not inspected.
  - Home page CSSOM scan found no :focus-visible/reduced-motion, while the pricing page did — scanning is per-page.
  - contact/sales (page 4) is a short form page and contributes little signal.

## Design Map

### Measurements

| Category | Value | Status | Evidence |
| --- | --- | --- | --- |
| Color / canvas | `white (62%) with two pale bands #E5EDF5 and #F8FAFD; pricing page is #F6F9FC under white cards` | Observed / 实测 | e-canvas-light, e-canvas-pricing, e-sections-tinted |
| Color / text | `#061B31 headings (RGB 6,27,49), #50617A body, #64748D muted — all blue-tinted, no pure grey` | Observed / 实测 | e-ink, e-ink-body, e-ink-other |
| Color / accent | `#533AFD primary fills and linked words (0.2% of surface), #635BFF CTA on pricing; secondary CTA is 1px purple outline` | Observed / 实测 | e-purple, e-buttons |
| Color / hero | `full-bleed gradient band (pink/orange/lilac) occupying the hero's right half; decorative, 0% as a control colour` | Observed / 实测 | e-hero-band |
| Typography / families | `sohne-var (1986 nodes) + SourceCodePro for code/keys` | Observed / 实测 | e-font-sohne, e-font-mono |
| Typography / scale | `H1 48/300/-0.96px, H2 32/300/-0.64px, H3 26/300/-0.26px, body 16-17px, prose 32px/300` | Observed / 实测 | e-h1, e-h2, e-h3, e-body-type, e-size-dist |
| Typography / UI | `pricing/product UI sits at 15px x531 and 14px; 10px x93 on the home page is metadata, not body` | Observed / 实测 | e-size-dist, e-size-dist-pricing |
| Typography / weights | `300 body/display dominates (x302 / x506), 400 secondary, 425/500 only in pricing UI; 700 only in 3 nodes` | Observed / 实测 | e-weights, e-weights-pricing |
| Shape / radius | `4px controls, 6px secondary, 16.5px cards on pricing, 8px on secondary cards` | Observed / 实测 | e-radii, e-radii-pricing |
| Shape / depth | `layered tinted shadows: rgba(50,50,93,.12) 0 16px 32px for floats; pricing cards rgba(50,50,93,.25) 0 13px 27px -5px + rgba(0,0,0,.3) 0 8px 16px` | Observed / 实测 | e-shadow-soft, e-shadow-layered |
| Shape / hairline | `button rings: inset 0 0 0 2px white, 0 0 0 1px purple on products` | Observed / 实测 | e-ring |
| Motion | `0.24s opacity (cubic-bezier(.45,.05,.55,.95)), 0.3s color (cubic-bezier(.25,1,.5,1)), 0.4s grid-template-rows reveal` | Observed / 实测 | e-motion |
| Spacing | `8px base; 128px between sections on product pages, home hero→logos 160px then 408px` | Observed / 实测 | e-space, e-gaps-home, e-gaps-products |
| Layout / grid | `12 x 88px with 16px gutters (footer + content), 1080px pricing container` | Observed / 实测 | e-grid, e-container |

### Patterns

**Text is blue-black, never grey** — Headings #061B31 and body #50617A sit on a blue hue axis; muted text is a lighter blue, not a neutral.
- Goal: Keeps a light page from looking half-finished and ties copy to the indigo CTA.
- Evidence: e-ink, e-ink-body, e-ink-other

**One indigo for actions and linked words only** — rgb(83,58,253) covers ~0.2% of the surface: filled CTA, 1px outlined CTA, inline links. No indigo surfaces, headers or decoration.
- Goal: Action colour stays unambiguous while the page stays mostly white.
- Evidence: e-purple, e-canvas-light, e-buttons

**One gradient, spent on the hero** — A single full-bleed pink/orange/lilac band covers the hero; every section below is flat white or a pale tint.
- Goal: Delivers a memorable first screen, then removes colour so product detail is readable.
- Evidence: e-hero-band, e-canvas-light, e-sections-tinted

**Light weights at every size** — 300 carries display and body (x302 home, x506 pricing); 400 for UI, 425/500 only inside pricing controls.
- Goal: Keeps 48px headlines airy so gradient and product shots carry the emotion.
- Evidence: e-weights, e-weights-pricing, e-h1

**Controls small, cards large** — Buttons and chips 4-6px; cards 16.5px on pricing and 8px elsewhere. No pill buttons in the primary flow.
- Goal: Distinguishes clickable controls from content containers by silhouette.
- Evidence: e-radii, e-radii-pricing

**Shadows tinted to the canvas, not black** — Elevation uses rgba(50,50,93,·) plus a second layer, mostly 1-2px tight, with 13-16px blur on floats.
- Goal: Product screenshots float on white without grey halos.
- Evidence: e-shadow-soft, e-shadow-layered, e-ring

**Three motion tiers by job** — 0.24s for opacity, 0.3s for colour, 0.4s for the grid reveal; reduced-motion and focus-visible are present on the pricing stylesheet.
- Goal: Colour is instant enough to feel responsive, layout reveals stay calm.
- Evidence: e-motion, e-motion-support

**Fixed 128px section rhythm on inner pages** — Product pages repeat a 128px gap seven times; the home page uses 160px then a 408px break around the logos.
- Goal: Inner pages read as one steady column; only the home page gets dramatic spacing.
- Evidence: e-gaps-products, e-gaps-home, e-space

### Tokens

| Token | CSS var | Type | Layer | Status | Value |
| --- | --- | --- | --- | --- | --- |
| `color/ink/900` | `--lw-ink-900` | color | primitive | observed | `#061B31` |
| `color/ink/700` | `--lw-ink-700` | color | primitive | observed | `#50617A` |
| `color/ink/600` | `--lw-ink-600` | color | primitive | observed | `#64748D` |
| `color/blue-tint/100` | `--lw-tint-100` | color | primitive | observed | `#E5EDF5` |
| `color/blue-tint/50` | `--lw-tint-50` | color | primitive | observed | `#F8FAFD` |
| `color/blue-tint/25` | `--lw-page-tint` | color | primitive | observed | `#F6F9FC` |
| `color/white` | `--lw-white` | color | primitive | observed | `#FFFFFF` |
| `color/indigo/600` | `--lw-indigo-600` | color | primitive | observed | `#533AFD` |
| `color/indigo/500` | `--lw-indigo-500` | color | primitive | observed | `#635BFF` |
| `color/canvas` | `--lw-canvas` | color | semantic | observed | `→ color/white` |
| `color/canvas-tint` | `--lw-canvas-tint` | color | semantic | observed | `→ color/blue-tint/25` |
| `color/surface-subtle` | `--lw-surface-subtle` | color | semantic | observed | `→ color/blue-tint/50` |
| `color/text/heading` | `--lw-text-heading` | color | semantic | observed | `→ color/ink/900` |
| `color/text/body` | `--lw-text-body` | color | semantic | observed | `→ color/ink/700` |
| `color/text/muted` | `--lw-text-muted` | color | semantic | observed | `→ color/ink/600` |
| `color/action/bg` | `--lw-action-bg` | color | semantic | observed | `→ color/indigo/600` |
| `color/action/bg-alt` | `--lw-action-bg-alt` | color | semantic | observed | `→ color/indigo/500` |
| `color/action/fg` | `--lw-action-fg` | color | semantic | observed | `→ color/white` |
| `color/link` | `--lw-link` | color | semantic | observed | `→ color/indigo/600` |
| `font/sans` | `--lw-font-sans` | fontFamily | primitive | observed | `'sohne-var', -apple-system, system-ui, 'Segoe UI', sans-serif` |
| `font/mono` | `--lw-font-mono` | fontFamily | primitive | observed | `'SourceCodePro', ui-monospace, SFMono-Regular, monospace` |
| `font/body` | `--lw-font-body` | fontFamily | semantic | observed | `→ font/sans` |
| `font/code` | `--lw-font-code` | fontFamily | semantic | observed | `→ font/mono` |
| `type/hero` | `--lw-type-hero` | dimension | component | observed | `48px` |
| `type/h2` | `--lw-type-h2` | dimension | component | observed | `32px` |
| `type/h3` | `--lw-type-h3` | dimension | component | observed | `26px` |
| `type/body` | `--lw-type-body` | dimension | component | observed | `16px` |
| `type/ui` | `--lw-type-ui` | dimension | component | observed | `15px` |
| `type/caption` | `--lw-type-caption` | dimension | component | observed | `10px` |
| `tracking/hero` | `--lw-tracking-hero` | dimension | component | observed | `-0.02em` |
| `tracking/h2` | `--lw-tracking-h2` | dimension | component | observed | `-0.015em` |
| `leading/prose` | `--lw-leading-prose` | number | component | observed | `1.2` |
| `weight/light` | `--lw-weight-light` | fontWeight | primitive | observed | `300` |
| `weight/regular` | `--lw-weight-regular` | fontWeight | primitive | observed | `400` |
| `weight/ui-strong` | `--lw-weight-ui-strong` | fontWeight | primitive | observed | `500` |
| `radius/control` | `--lw-radius-control` | dimension | semantic | observed | `4px` |
| `radius/control-alt` | `--lw-radius-control-alt` | dimension | semantic | observed | `6px` |
| `radius/card` | `--lw-radius-card` | dimension | semantic | observed | `16.5px` |
| `depth/float` | `--lw-depth-float` | shadow | component | observed | `0 16px 32px rgba(50, 50, 93, 0.12)` |
| `depth/float-strong` | `--lw-depth-float-strong` | shadow | component | observed | `0 13px 27px -5px rgba(50, 50, 93, 0.25), 0 8px 16px -8px rgba(0, 0, 0, 0.3)` |
| `depth/ring` | `--lw-depth-ring` | shadow | component | observed | `0 0 0 1px #533AFD` |
| `depth/ring-inset` | `--lw-depth-ring-inset` | shadow | component | observed | `inset 0 0 0 2px #FFFFFF` |
| `motion/fast` | `--lw-motion-fast` | duration | primitive | observed | `240ms` |
| `motion/base` | `--lw-motion-base` | duration | primitive | observed | `300ms` |
| `motion/reveal` | `--lw-motion-reveal` | duration | primitive | observed | `400ms` |
| `motion/easing-in-out` | `--lw-easing-in-out` | easing | primitive | observed | `cubic-bezier(0.45, 0.05, 0.55, 0.95)` |
| `motion/easing-out` | `--lw-easing-out` | easing | primitive | observed | `cubic-bezier(0.25, 1, 0.5, 1)` |
| `space/section` | `--lw-space-section` | dimension | component | observed | `128px` |
| `layout/container` | `--lw-layout-container` | dimension | component | inferred | `1080px` |

---

# Taste DNA

### Colour is a once-per-page event
- **Kind**: restraint
- **Trigger**: Making a payments brand feel alive without breaking legibility of dense product shots.
- **Decision**: One full-bleed gradient band in the hero; below it every surface is white or a pale blue tint.
- **Chose**: a single decorative gradient confined to the hero   **Over**: gradient text, gradient buttons, and gradient section backgrounds (the common fintech treatment)
- **Reason**: Readers need to trust the screenshots more than the scenery; once colour stops, the product becomes the subject.
- **Evidence**: e-hero-band, e-canvas-light, e-sections-tinted  ·  patterns: p-hero-gradient
- **Status**: Observed / 实测
- **Guardrail (enforced)**: `{"forbidCss": [], "forbidClass": ["(?:^|[^a-z0-9-])bg-(?:gradient-to-|linear-to-|radial-to-|conic-to-)", "shadow-(?!(?:none|sm|inner)\\b)[a-z0-9]+"], "max": {"border-width": {"value": "1", "unit": "px"}}, "note": "Gradients outside the hero band and any non-ring shadow class are violations; hairlines (1px) are the intended depth signal."}`

### One indigo, only where you can click
- **Kind**: restraint
- **Trigger**: Deciding how much of a light page the brand colour may occupy.
- **Decision**: Indigo only on the filled CTA, the outlined CTA border, and linked words; everything else is ink or tint.
- **Chose**: indigo restricted to actions and links   **Over**: indigo section backgrounds, indigo icons, and indigo headings
- **Reason**: At ~0.2% of the surface, indigo always means 'do something'; a larger share would make the page a brand poster and slow scanning.
- **Evidence**: e-purple, e-canvas-light  ·  patterns: p-accent-share
- **Status**: Observed / 实测
- **Guardrail (enforced)**: `{"forbidCss": [], "forbidClass": ["(?:^|[^a-z0-9-])bg-(?:indigo|violet|purple)-(?:4|5|6|7)\\d\\d$", "(?:^|[^a-z0-9-])bg-(?:gradient-to-|linear-to-|radial-to-|conic-to-)"], "max": {}, "note": "Allowed on buttons/links only; never on a section or card background."}`

### Light weights carry the headline
- **Kind**: craft
- **Trigger**: Setting a 48px headline beside a saturated gradient.
- **Decision**: 300 weight at 48/32/26px with -0.96/-0.64/-0.26px tracking; weight steps up only inside pricing controls (425/500).
- **Chose**: variable 300 at every display size   **Over**: 600-700 headline weights with a 1.33x type ramp
- **Reason**: A light face over a heavy gradient leaves the gradient as the loudest thing; bold type would fight the artwork and the screenshots.
- **Evidence**: e-weights, e-h1, e-h2, e-h3  ·  patterns: p-light-weights
- **Status**: Observed / 实测

### Blue-black ink instead of grey
- **Kind**: craft
- **Trigger**: Choosing text colours for a white page with a cold indigo accent.
- **Decision**: #061B31 headings and #50617A body — every neutral carries a blue hue.
- **Chose**: blue-tinted neutrals   **Over**: pure greys (#111, #666) or neutral-warm text
- **Reason**: Grey text on a white page beside indigo reads as unfinished; shared hue makes the colour look chosen rather than added.
- **Evidence**: e-ink, e-ink-body  ·  patterns: p-ink-tint
- **Status**: Observed / 实测

### Motion is tiered by job
- **Kind**: system
- **Trigger**: Animating a page with hover states, colour changes and a reveal.
- **Decision**: 0.24s opacity, 0.3s colour, 0.4s grid reveal, each with its own cubic-bezier; focus-visible and reduced-motion respected.
- **Chose**: three job-specific durations   **Over**: one global 200ms ease on everything
- **Reason**: Colour has to feel immediate on hover while a layout reveal needs room to read; one duration would make one of them wrong.
- **Evidence**: e-motion, e-motion-support  ·  patterns: p-motion-tiered
- **Status**: Observed / 实测

## Interaction Delta (measured)

Forced with a real mouse (CDP `Input.dispatchMouseEvent`) and `element.focus()`; only these properties are diffed: `background-color`, `color`, `border-color`, `box-shadow`, `outline`, `transform`.

### button — `button.hds-button.CookieSettings_CookieSettings__HelmButton__69vhe`
- Status: Observed / 实测 · evidence: e-buttons, e-purple
- **hover**: `color`: `rgb(83, 58, 253)` → `rgb(46, 43, 140)`; `border-color`: `rgb(214, 217, 252)` → `rgb(64, 50, 200)`
- **focus**: `outline`: `0px solid rgba(0, 0, 0, 0)` → `3px solid rgba(84, 82, 251, 0.75)`

### button — `button.hds-ui-button.announcement-bar__dismiss`
- Status: Observed / 实测 · evidence: e-buttons
- **hover**: none (no computed change on the icon-only dismiss button)
- **focus**: `outline`: `0px solid rgba(0, 0, 0, 0)` → `3px solid rgba(0, 0, 0, 0)`

### card — `div.payments-graphic__checkout-item-card`
- Status: Inferred / 推断 · evidence: e-shadow-soft
- **hover**: none (No computed change; the card sits inside an animated illustration, so observed ≠ no hover style exists)
- **focus**: none (Not focusable)

## Open questions

- Is the hero gradient CSS or an image asset on other locales?
- Does the dark footer section count as a second surface mode?
