# Steno.ai — Design DNA

- Source: https://www.steno.ai/
- Mode: full  ·  Captured: 2026-11-24T10:16:55+00:00
- Pages inspected: 4 (https://www.steno.ai/, https://www.steno.ai/about, https://www.steno.ai/team, https://www.steno.ai/experts)
- Browser capture: isolated (fresh context)
- Viewport: 1440x900
- Limitations:
  - The site's hero covered the first capture with a full-height intro animation; the entry page was re-captured once it finished, and clips were taken from that same load. If the intro replays, the source screenshot will be showing it.
  - PP Writer and PP Mori are licensed display faces, not shipped here; specimens fall back to Georgia and Arial.
  - The hero's right frame is a render (653×512 video still with a 1px inset). Only its size, inset, radius and motion were measured; the artwork itself is shown as the captured frame in Fidelity, never copied.
  - `#CAFF75` and `#2D62FF` are declared variables; only the lime is used on the home page (inside one icon).
  - The CTA's hover was measured with a real pointer; the computed delta stayed inside the frame's entry wobble, so brick.md reports the measured numbers and does not invent bigger ones.
  - No prefers-reduced-motion block exists on any of the four pages; reduce is therefore a measured absence, not a branch to copy.

## Design Map

### Measurements

| Category | Value | Status | Evidence |
| --- | --- | --- | --- |
| Color / canvas | `#F0EDDA oatmeal-03 fills the page (49% element background share at 1440); #FFFDF1 oatmeal-02 46.2% of alt panels` | Observed / 实测 | e-canvas, e-oatmeal-scale, e-canvas-about |
| Color / surface | `#BAA57B oatmeal-06 is the product card / twin card surface (0.7% of area); #DAD7C1 oatmeal-04 and #CFCCB1 oatmeal-05 are tint bands` | Observed / 实测 | e-surface, e-oatmeal-scale |
| Color / text | `#282724 text on oatmeal; #FFFDF1 on ink; muted is 70% alpha of either` | Observed / 实测 | e-ink, e-ink-muted, e-text-secondary |
| Color / action | `#282724 fill + #FFFDF1 label, 1px rgba(240,237,218,0.1) ring; hover fill #43413C` | Observed / 实测 | e-action-bg, e-action-fg, e-ink-soft |
| Color / accent | `#CAFF75 neon exists only on the hero eyebrow play glyph; role reads as a play marker for the mauve and dark CTA` | Observed / 实测 | e-accent-lime, e-action-bg |
| Type / display | `PP Writer 400: 76.8/76.8 h1, 60.8/66.88 display with -0.8px, 56/61.6 h2, 40/48 with -1.28px, 22/28.6 h3, 18/23.4 h4` | Observed / 实测 | e-font-writer, e-h1, e-h2, e-h2-large, e-h3, e-h4, e-h40 |
| Type / body | `PP Mori 400: 20/28 lead, 16/22.4 default, 13/18.2 tiny, 12/16.8 micro; 600 only on button labels` | Observed / 实测 | e-font-mori, e-body-mori, e-weights |
| Type / scale shape | `two bands: 76.8-56-40 display and 22-20-18-16-14-13-12 UI, with 16px carrying 598 nodes` | Observed / 实测 | e-sizes, e-h1, e-body-mori |
| Shape / radius | `8px on 127 elements (controls, cards); 6px on 12; 16px on 2 chips; 1600px on the quote pill` | Observed / 实测 | e-radii, e-pill |
| Shape / depth | `no card shadow anywhere except one 4-layer drop shadow of up to 58px blur on a single overlay` | Observed / 实测 | e-shadow |
| Motion | `transform 0.525s cubic-bezier(0.625, 0.05, 0, 1) for button text/bg; 0.4s cubic-bezier(0.25, 1, 0.5, 1) for reveals; color/bg 0.2-0.3s` | Observed / 实测 | e-motion-btn, e-motion-hover-rule, e-motion-soft |
| Layout | `hero: 2 columns of 648px with a 64px gap at 1440; 40px page gutters (1360px container)` | Observed / 实测 | e-hero-grid, e-section-gap |
| Accessibility | `no prefers-reduced-motion block on any of the 4 pages` | Observed / 实测 | e-motion-reduced-scan |
| Accessibility / focus | `focus ring is the browser default 1px auto rgb(0,95,204) on CTAs; the nav dropdown button shows none` | Observed / 实测 | e-cta-focus, e-nav-focus |

### Patterns

**Cinematic sheet, streaming landscape** — The hero is one full-width landscape frame (653×512 video still, inset 1px) with a piece of copy pinned to its left; product cards become hashed collage slices (rotate(−6°/+4°)) rather than floating UI.
- Goal: Reads as an editorial spread for the brand, not a dashboard of features.
- Evidence: e-hero-grid, e-surface, e-canvas

**Oatmeal-only palette** — Both light and dark are the same hue: #F0EDDA / #282724, with #FFFDF1, #CFCCB1, #DAD7C1 as bands and #BAA57B as the one product surface; #CAFF75 is the sole chromatic accent (spot).
- Goal: Keeps photography (amber grass, teal dusk) as the only wide colour field, and ties every panel back to paper.
- Evidence: e-oatmeal-scale, e-canvas, e-ink

**Paper-serif hero, sans everywhere else** — DISPLAY text is PP Writer 400 (no weight heavier than 400); interface and labels are PP Mori 400, with 600 only for the label inside filled CTA buttons.
- Goal: A serif statement asks for reading, not scanning; sans keeps the product-state lines compact.
- Evidence: e-h1, e-font-writer, e-font-mori, e-weights

**8px softness everywhere except the quote pill** — Controls, cards and the hero frame share radius 8px; pills and option cards use 1600px to their role; shadow is an edge, not a depth cue.
- Goal: One precision so a reader never wonders which layer they are looking at.
- Evidence: e-radii, e-pill, e-shadow

**Neon is a spot, never a surface** — #CAFF75 appears only inside the hero eyebrow glyph (a disk behind a triangular play mark); no background, border or text of this hue is allowed.
- Goal: A single mark turns the eyebrow into a video cue without competing with the hero imagery.
- Evidence: e-accent-lime, e-h1

### Tokens

| Token | CSS var | Type | Layer | Status | Value |
| --- | --- | --- | --- | --- | --- |
| `color/oatmeal/02` | `--oatmeal-02` | color | primitive | observed | `#FFFDF1` |
| `color/oatmeal/03` | `--oatmeal-03` | color | primitive | observed | `#F0EDDA` |
| `color/oatmeal/04` | `--oatmeal-04` | color | primitive | observed | `#DAD7C1` |
| `color/oatmeal/05` | `--oatmeal-05` | color | primitive | observed | `#CFCCB1` |
| `color/oatmeal/06` | `--oatmeal-06` | color | primitive | observed | `#BAA57B` |
| `color/oatmeal/08` | `--oatmeal-08` | color | primitive | observed | `#43413C` |
| `color/oatmeal/09` | `--oatmeal-09` | color | primitive | observed | `#282724` |
| `color/brand-ink` | `--brand-ink` | color | primitive | observed | `#282724` |
| `color/ink/10` | `--ink-10` | color | primitive | observed | `#2827251A` |
| `color/tint/50` | `--tint-50` | color | primitive | observed | `#28272580` |
| `color/white/alternate` | `--white-alternate` | color | primitive | observed | `#FFFDF1` |
| `color/light/muted` | `--light-muted` | color | primitive | observed | `#F0EDDAB3` |
| `color/neon` | `--neon` | color | primitive | observed | `#CAFF75` |
| `color/link-blue` | `--link-blue` | color | primitive | observed | `#2D62FF` |
| `color/canvas` | `--lw-canvas` | color | semantic | observed | `→ color/oatmeal/03` |
| `color/canvas-alt` | `--lw-canvas-alt` | color | semantic | observed | `→ color/oatmeal/02` |
| `color/canvas-tint` | `--lw-canvas-tint` | color | semantic | observed | `→ color/oatmeal/04` |
| `color/canvas-band` | `--lw-canvas-band` | color | semantic | observed | `→ color/oatmeal/05` |
| `color/surface` | `--lw-surface` | color | semantic | observed | `→ color/oatmeal/06` |
| `color/screen` | `--lw-screen` | color | semantic | observed | `→ color/oatmeal/09` |
| `color/text-primary` | `--lw-text-primary` | color | semantic | observed | `→ color/oatmeal/09` |
| `color/text-body` | `--lw-text-body` | color | semantic | observed | `→ color/oatmeal/08` |
| `color/text-secondary` | `--lw-text-secondary` | color | semantic | observed | `→ color/oatmeal/02` |
| `color/text-tertiary` | `--lw-text-tertiary` | color | semantic | observed | `→ color/light/muted` |
| `color/action/bg` | `--lw-action-bg` | color | semantic | observed | `→ color/oatmeal/09` |
| `color/action/bg-hover` | `--lw-action-bg-alt` | color | semantic | observed | `→ color/oatmeal/08` |
| `color/action/fg` | `--lw-action-fg` | color | semantic | observed | `→ color/oatmeal/02` |
| `color/brand` | `--lw-brand` | color | semantic | observed | `→ color/surface` |
| `color/accent` | `--lw-accent` | color | semantic | observed | `→ color/neon` |
| `color/nav-primary` | `--lw-nav-primary` | color | component | observed | `→ color/text-primary` |
| `color/border` | `--lw-border` | color | component | proposed | `rgba(40, 39, 37, 0.15)` |
| `color/border-strong` | `--lw-border-strong` | color | component | proposed | `rgba(40, 39, 37, 0.25)` |
| `color/on-brand` | `--lw-on-brand` | color | primitive | observed | `rgba(40, 39, 36, 1)` |
| `color/hover-tint` | `--lw-hover-tint` | color | component | proposed | `rgba(40, 39, 36, 0.06)` |
| `font/display` | `--lw-font-display` | fontFamily | primitive | observed | `'PP Writer', Georgia, sans-serif` |
| `font/ui` | `--lw-font-ui` | fontFamily | primitive | observed | `'PP Mori', Arial, sans-serif` |
| `font/mono` | `--lw-font-mono` | fontFamily | primitive | observed | `ui-monospace, SFMono-Regular, Menlo, monospace` |
| `font/campaign` | `--lw-font-campaign` | fontFamily | semantic | observed | `→ font/display` |
| `font/body` | `--lw-font-body` | fontFamily | semantic | observed | `→ font/ui` |
| `type/display-xl` | `--lw-type-display-xl` | dimension | component | observed | `76.8px` |
| `type/display-lg` | `--lw-type-display-lg` | dimension | component | observed | `60.8px` |
| `type/display` | `--lw-type-display` | dimension | component | observed | `56px` |
| `type/headline` | `--lw-type-headline` | dimension | component | observed | `40px` |
| `type/title` | `--lw-type-title` | dimension | component | observed | `22px` |
| `type/subtitle` | `--lw-type-subtitle` | dimension | component | observed | `18px` |
| `type/lead` | `--lw-type-lead` | dimension | component | observed | `20px` |
| `type/body` | `--lw-type-body` | dimension | component | observed | `16px` |
| `type/ui` | `--lw-type-ui` | dimension | component | observed | `14px` |
| `type/caption` | `--lw-type-caption` | dimension | component | observed | `13px` |
| `type/micro` | `--lw-type-micro` | dimension | component | observed | `12px` |
| `leading/display` | `--lw-leading-display` | number | component | observed | `1.0` |
| `leading/tight` | `--lw-leading-tight` | number | component | observed | `1.1` |
| `leading/heading` | `--lw-leading-heading` | number | component | observed | `1.3` |
| `leading/prose` | `--lw-leading-prose` | number | component | observed | `1.4` |
| `leading/ui` | `--lw-leading-ui` | number | component | observed | `1.4` |
| `tracking/display` | `--lw-tracking-display` | dimension | component | observed | `-0.8px` |
| `tracking/headline` | `--lw-tracking-headline` | dimension | component | observed | `-1.28px` |
| `tracking/body` | `--lw-tracking-body` | dimension | component | observed | `0em` |
| `weight/regular` | `--lw-weight-regular` | fontWeight | primitive | observed | `400` |
| `weight/interface` | `--lw-weight-interface` | fontWeight | primitive | observed | `600` |
| `layout/section` | `--lw-layout-section` | dimension | component | observed | `900px` |
| `layout/gutter` | `--lw-layout-gutter` | dimension | component | observed | `40px` |
| `layout/grid-gap` | `--lw-layout-gap` | dimension | component | observed | `64px` |
| `radius/control` | `--lw-radius-control` | dimension | component | observed | `8px` |
| `radius/pill` | `--lw-radius-pill` | dimension | primitive | observed | `1600px` |
| `radius/chip` | `--lw-radius-chip` | dimension | component | observed | `16px` |
| `radius/card` | `--lw-radius-card` | dimension | component | observed | `8px` |
| `depth/overlay` | `--lw-depth-overlay` | shadow | component | observed | `0 33px 33px rgba(44,38,27,0.17), 0 75px 45px rgba(44,38,27,0.10), 0 133px 53px rgba(44,38,27,0.03)` |
| `motion/slip` | `--lw-motion-slip` | duration | primitive | observed | `525ms` |
| `motion/reveal` | `--lw-motion-reveal` | duration | primitive | observed | `400ms` |
| `motion/soft` | `--lw-motion-soft` | duration | primitive | observed | `300ms` |
| `motion/micro` | `--lw-motion-micro` | duration | primitive | observed | `200ms` |
| `motion/easing-slip` | `--lw-easing-slip` | easing | primitive | observed | `cubic-bezier(0.625, 0.05, 0, 1)` |
| `motion/easing-reveal` | `--lw-easing-reveal` | easing | primitive | observed | `cubic-bezier(0.25, 1, 0.5, 1)` |

---

# Taste DNA

### The button slip is the whole interaction
- **Kind**: restraint
- **Trigger**: Deciding how a filled CTA reacts to the pointer on a page whose hero is a moving image.
- **Decision**: On hover the button's inner fill resets its transform (translate 0 / rotate 0) over 525ms with cubic-bezier(0.625, 0.05, 0, 1); the label does not move.
- **Chose**: one accent-brown slip inside the 8px frame   **Over**: lift/shadow and scale on the whole button, or a second accent colour on the fill
- **Reason**: A page already carrying an image is already loud (the restrained motion is a slip, not a raise); the icon fill turning a shade lighter tells the pointer 'active' without a second focal point.
- **Evidence**: e-motion-btn, e-motion-hover-rule, e-action-bg  ·  patterns: p-oatmeal-only, p-soft-8px
- **Status**: Observed / 实测
- **Guardrail (enforced)**: `{"forbidClass": ["hover:shadow-(?!(?:none|sm|inner)\\b)[a-z0-9]+"], "max": {"box-shadow": {"value": "0", "unit": "px"}}, "note": "The control's only motion is the measured 525ms transform slip; a hover shadow is a violation."}`

### Photo is the only colour cut
- **Kind**: craft
- **Trigger**: Deciding where the accent may appear on a hero that carries a full-size photograph.
- **Decision**: #CAFF75 stays a spot (one per page at most, inside an icon), #2D62FF link slot never touches a filled control; cards use #BAA57B on the ink canvas.
- **Chose**: neon spot inside an icon + brand card on ink   **Over**: neon-filled CTA, or #2D62FF primary buttons on every section
- **Reason**: Amber grass and teal dusk raise the luminance of every near region of the hero; a chromatic fill at button scale would flatten the lightness contrast the serif headline relies on.
- **Evidence**: e-accent-lime, e-action-bg, e-ink-soft  ·  patterns: p-neon-spot
- **Status**: Observed / 实测

### Grain and grain only are allowed to move
- **Kind**: craft
- **Trigger**: Deciding what animates when the page opens and when a pointer reaches a control.
- **Decision**: Transitions on transform with a single curve (0.525s cubic-bezier(0.625, 0.05, 0, 1)); text reveal, hand-cut clipping and image renders run in layers over that.
- **Chose**: one transform curve with 0.3s opacity support   **Over**: spring/bounce easings and staggered keyframes per element
- **Reason**: The hero's frame and copy float in one timeline, so extra easing on any child just adds a second rhythm; one curve keeps copy and card reading as one.
- **Evidence**: e-motion-btn, e-motion-soft  ·  patterns: p-sheet-streaks
- **Status**: Observed / 实测

### Grain without motion drift
- **Kind**: system
- **Trigger**: Running under prefers-reduced-motion: reduce (zero blocks on any of the four pages).
- **Decision**: Under reduce lewitt plays every motion at its end state instantly (opacity/transform to done), and the brick states the reduce branch it measured.
- **Chose**: the same timeline with 0.3s opacity support   **Over**: progressing drift staying in place
- **Reason**: The page reads as a document; a drifting parallax under a document is a visual defect, not an effect to slow down, so a build that mirrors this site must add the branch the site is missing.
- **Evidence**: e-motion-reduced-scan, e-motion-btn, e-motion-soft  ·  patterns: p-sheet-streaks
- **Status**: Observed / 实测

## Interaction Delta (measured)

Forced with a real mouse (CDP `Input.dispatchMouseEvent`) and `element.focus()`; only these properties are diffed: `background-color`, `color`, `border-color`, `box-shadow`, `outline`, `transform`.

### link — `a.btn-icon-link`
- Status: Observed / 实测 · evidence: e-cta-hover, e-cta-focus
- **hover**: none (CSS rule re-applies transform on :hover .btn-icon-content__bg; the computed delta in the capture was below noise after the entry animation finished)
- **focus**: `outline`: `3px none rgb(40, 39, 36)` → `1px auto rgb(0, 95, 204)`

### button — `button.nav-dropdown_dropdown-toggle.w-dropdown-toggle`
- Status: Observed / 实测 · evidence: e-nav-focus
- **hover**: none (no computed change)
- **focus**: `outline`: `3px none rgb(40, 39, 36)` → `0px none rgb(40, 39, 36)`

### card — `div.home_hero-twin-card`
- Status: Inferred / 推断 · evidence: e-hero-svg-wheel, e-surface
- **hover**: none (no hover delta; the card is a 3D/2D rotation render, not a hover affordance)
- **focus**: none (Measured, no computed change)

## Open questions

- Is the hero frame a video on every viewport, or a static still on mobile?
- Do the /about and /team sections reuse the same dark section palette?
