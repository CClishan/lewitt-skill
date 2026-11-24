# Linear — Design DNA

- Source: https://linear.app
- Mode: dna  ·  Captured: 2026-11-23T12:15:26+00:00
- Pages inspected: 3 (https://linear.app, https://linear.app/customers, https://linear.app/pricing)
- Browser capture: isolated (fresh context)
- Viewport: 1440x900
- Limitations:
  - Computed styles resolve CSS variables, so original token names are Inferred.
  - Hover/press/keyboard states were not forced; e-focus-rm comes from a CSSOM scan only.
  - The hero app frame is a product mockup: its chrome is observed, its behaviour is not.

## Design Map

### Measurements

| Category | Value | Status | Evidence |
| --- | --- | --- | --- |
| Color / canvas | `rgb(8, 9, 10) = #08090A` | Observed / 实测 | e-home-bg, e-pricing-bg |
| Color / surface | `rgb(15, 16, 17) = #0F1011 (20.6% area), rgb(24,25,26) on stories, rgba(255,255,255,0.05) on plan cards` | Observed / 实测 | e-home-surface, e-customers-surface, e-pricing-surface |
| Color / text scale | `#F7F8F8 primary, #D0D6E0 body, #8A8F98 / #62666D muted` | Observed / 实测 | e-text-primary, e-text-body, e-text-muted |
| Color / accent share | `0 saturated accent roles; accentCandidates are grey/white; #F79CE0 appears once in hero word (<5% surface)` | Observed / 实测 | e-nav-cta, e-text-pink-hero |
| Typography / families | `Inter Variable (2266 el) + Berkeley Mono (259 el)` | Observed / 实测 | e-font-display, e-font-mono |
| Typography / scale | `12/13/14/15/16 px UI band + 20/32/48/64 px display; H1 64/64, H2 48/48, H3 20/26.6, body 15/24` | Observed / 实测 | e-h1, e-h2, e-h3, e-body, e-size-dist, e-size-dist-customers, e-size-dist-pricing |
| Typography / tracking | `H1 -1.408px (-2.2%), H2 -1.056px (-2.2%), body normal` | Observed / 实测 | e-h1, e-h2 |
| Typography / weights | `400 body, 510 emphasis (141 uses), 590 subhead (8 uses); no 700+ anywhere` | Observed / 实测 | e-weight-dist, e-weight-dist-other |
| Shape / radius | `pill 9999px, 8px controls, 4px chips, 50% avatars; 6/9/12px minority` | Observed / 实测 | e-radii |
| Shape / depth | `1px rings (rgba(0,0,0,0.2) and rgb(35,37,42) inset / rgba(255,255,255,0.05) inset); one soft 0 2px 32px rgba(0,0,0,0.25) for floating panels` | Observed / 实测 | e-shadows, e-shadows-other |
| Motion | `100ms and 160ms, cubic-bezier(0.25,0.46,0.45,0.94); :focus-visible and prefers-reduced-motion present` | Observed / 实测 | e-motion, e-focus-rm |
| Layout / rhythm | `10px between three consecutive sections; one 224px breathing band before the closing block` | Observed / 实测 | e-gaps |
| Layout / grid | `232px 1072px two-column app frame; 18 multi-column grids on the home page; 3x384 / 6x224 on subpages` | Observed / 实测 | e-grid |
| Layout / width | `containerMaxWidth none (fluid); header padding 72px top; content sits inside cards, not inside a centred container` | Inferred / 推断 | e-grid, e-home-surface |

### Patterns

**White-only action color** — The only saturated accent is a one-off hero word; every actionable surface resolves to white-on-near-black or 1px rings.
- Goal: Lets emphasis come from position and weight, so the product mock stays the brightest thing on the page.
- Evidence: e-nav-cta, e-text-pink-hero, e-text-primary

**Weight and tracking beat size jumps** — Hierarchy is carried by 400/510/590 and -2.2% tracking at display sizes, not by bold weights or a long type scale.
- Goal: Keeps headings calm at 64px so a dense product screenshot can sit underneath without competing.
- Evidence: e-weight-dist, e-weight-dist-other, e-h1

**Tight UI band, wide display jumps** — 86% of text sits in 12-16px; display sizes jump straight to 20/32/48/64 with no intermediate steps.
- Goal: Treats UI chrome as one texture and the marketing headline as a poster line — nothing in between competes.
- Evidence: e-size-dist, e-size-dist-pricing

**Rings instead of shadows** — Depth is a 1px inset/outset ring at 3-20% alpha; only genuinely floating panels get a soft shadow.
- Goal: Keeps dark surfaces from looking muddy and stops cards from stacking into a shadow ladder.
- Evidence: e-shadows, e-shadows-other

**Breathing room lives inside sections** — Section-to-section gap is 10px; the 224px of air is padding inside a band, not margin between bands.
- Goal: Makes the page read as one continuous dark canvas rather than a stack of cards.
- Evidence: e-gaps, e-home-bg

**Real product UI is the illustration** — The hero visual is a rendered app frame (232px sidebar + 1072px canvas) with real states, not abstract art.
- Goal: Shows the actual workflow at the exact density users buy the product for.
- Evidence: e-grid, e-font-mono

**Feedback motion only** — Transitions are 100-160ms on border/background/color, with :focus-visible and a reduced-motion branch present.
- Goal: Confirms interaction without delaying it; state stays legible with motion disabled.
- Evidence: e-motion, e-focus-rm

### Tokens

| Token | CSS var | Type | Layer | Status | Value |
| --- | --- | --- | --- | --- | --- |
| `color/neutral/950` | `--ds-neutral-950` | color | primitive | observed | `#08090A` |
| `color/neutral/900` | `--ds-neutral-900` | color | primitive | observed | `#0F1011` |
| `color/neutral/850` | `--ds-neutral-850` | color | primitive | observed | `#23252A` |
| `color/white` | `--ds-white` | color | primitive | observed | `#FFFFFF` |
| `color/grey/200` | `--ds-grey-200` | color | primitive | observed | `#F7F8F8` |
| `color/grey/400` | `--ds-grey-400` | color | primitive | observed | `#D0D6E0` |
| `color/grey/600` | `--ds-grey-600` | color | primitive | observed | `#8A8F98` |
| `color/grey/700` | `--ds-grey-700` | color | primitive | observed | `#62666D` |
| `color/highlight/one-off` | `--ds-highlight-one-off` | color | primitive | observed | `#F79CE0` |
| `color/canvas` | `--ds-canvas` | color | semantic | observed | `→ color/neutral/950` |
| `color/surface` | `--ds-surface` | color | semantic | observed | `→ color/neutral/900` |
| `color/ring` | `--ds-ring` | color | semantic | observed | `→ color/neutral/850` |
| `color/text/primary` | `--ds-text-primary` | color | semantic | observed | `→ color/grey/200` |
| `color/text/body` | `--ds-text-body` | color | semantic | observed | `→ color/grey/400` |
| `color/text/muted` | `--ds-text-muted` | color | semantic | observed | `→ color/grey/600` |
| `color/action/bg` | `--ds-action-bg` | color | semantic | observed | `→ color/white` |
| `color/action/fg` | `--ds-action-fg` | color | semantic | observed | `→ color/neutral/950` |
| `font/sans` | `--ds-font-sans` | fontFamily | primitive | observed | `'Inter Variable', Inter, system-ui, sans-serif` |
| `font/mono` | `--ds-font-mono` | fontFamily | primitive | observed | `'Berkeley Mono', ui-monospace, SFMono-Regular, monospace` |
| `font/body` | `--ds-font-body` | fontFamily | semantic | observed | `→ font/sans` |
| `font/code` | `--ds-font-code` | fontFamily | semantic | observed | `→ font/mono` |
| `type/display-1` | `--ds-type-display-1` | dimension | component | observed | `64px` |
| `type/display-2` | `--ds-type-display-2` | dimension | component | observed | `48px` |
| `type/title` | `--ds-type-title` | dimension | component | observed | `20px` |
| `type/body` | `--ds-type-body` | dimension | component | observed | `15px` |
| `type/ui` | `--ds-type-ui` | dimension | component | observed | `13px` |
| `type/caption` | `--ds-type-caption` | dimension | component | observed | `12px` |
| `leading/display` | `--ds-leading-display` | number | component | observed | `1` |
| `leading/body` | `--ds-leading-body` | number | component | observed | `1.6` |
| `tracking/display` | `--ds-tracking-display` | dimension | component | observed | `-0.022em` |
| `weight/body` | `--ds-weight-body` | fontWeight | primitive | observed | `400` |
| `weight/emphasis` | `--ds-weight-emphasis` | fontWeight | primitive | observed | `510` |
| `weight/subhead` | `--ds-weight-subhead` | fontWeight | primitive | observed | `590` |
| `radius/pill` | `--ds-radius-pill` | dimension | primitive | observed | `9999px` |
| `radius/md` | `--ds-radius-md` | dimension | primitive | observed | `8px` |
| `radius/sm` | `--ds-radius-sm` | dimension | primitive | observed | `4px` |
| `radius/control` | `--ds-radius-control` | dimension | semantic | observed | `→ radius/md` |
| `depth/ring` | `--ds-depth-ring` | shadow | component | observed | `0 0 0 1px #23252A` |
| `depth/ring-inset` | `--ds-depth-ring-inset` | shadow | component | observed | `inset 0 0 0 1px rgba(255, 255, 255, 0.05)` |
| `depth/float` | `--ds-depth-float` | shadow | component | observed | `0 2px 32px rgba(0, 0, 0, 0.25)` |
| `motion/duration-fast` | `--ds-motion-fast` | duration | primitive | observed | `100ms` |
| `motion/duration` | `--ds-motion-duration` | duration | primitive | observed | `160ms` |
| `motion/easing` | `--ds-motion-easing` | easing | primitive | observed | `cubic-bezier(0.25, 0.46, 0.45, 0.94)` |
| `space/section-adjacent` | `--ds-space-section-adjacent` | dimension | component | observed | `10px` |
| `space/section-breath` | `--ds-space-section-breath` | dimension | component | observed | `224px` |
| `layout/sidebar` | `--ds-layout-sidebar` | dimension | component | observed | `232px` |

---

# Taste DNA

### Brand lives in white, not in colour
- **Kind**: restraint
- **Trigger**: Deciding the action colour on a near-black marketing page.
- **Decision**: Use white (#FFFFFF) on #08090A for the only high-contrast action and let everything else be grey.
- **Chose**: white-on-black primary action   **Over**: a branded accent hue (Linear purple) across CTAs, links and states
- **Reason**: On #08090A a white pill is already the loudest possible element; a coloured button would read as a template and compete with the product screenshot.
- **Evidence**: e-nav-cta, e-text-pink-hero, e-text-primary  ·  patterns: p-accent-restraint
- **Status**: Observed / 实测
- **Guardrail (enforced)**: `{"forbidCss": [], "forbidClass": ["(?:^|[^a-z0-9-])bg-(?!white\\b|black\\b|transparent\\b|gray\\b|neutral\\b|zinc\\b|slate\\b|none\\b)[a-z]+-(?:4|5|6|7)\\d\\d$", "(^|-)text-(?!white|black|transparent)[a-z]+-(4|5|6)\\d\\d$"], "max": {}, "note": "Any saturated fill/stroke belongs to illustration only, never to a control."}`

### Voice comes from weight, not from size
- **Kind**: craft
- **Trigger**: Making a 64px headline feel authoritative without shouting.
- **Decision**: Set display text at weight 510 with -2.2% tracking and subheads at 590; never go past 590.
- **Chose**: 510/590 variable weights with negative tracking   **Over**: 700/800 bold headings with a 1.25 modular scale
- **Reason**: Heavy weights at 64px turn into a wall that drowns the dense product screenshot directly below.
- **Evidence**: e-weight-dist, e-h1, e-h2, e-h3  ·  patterns: p-weight-not-size
- **Status**: Observed / 实测

### One texture for UI, a poster line for marketing
- **Kind**: system
- **Trigger**: Choosing the type scale for a page that mixes marketing copy and a UI mock.
- **Decision**: Keep 86% of text in 12-16px and jump straight to 20/32/48/64.
- **Chose**: two-band scale (12-16 UI, 48-64 display) with nothing in between   **Over**: a smooth 1.25x ramp (16/20/25/31/39/48)
- **Reason**: Intermediate sizes would make the app mock's own UI text compete with marketing headings.
- **Evidence**: e-size-dist, e-size-dist-customers, e-size-dist-pricing  ·  patterns: p-ui-band
- **Status**: Observed / 实测

### Depth is a ring, never a shadow ladder
- **Kind**: restraint
- **Trigger**: Separating cards and panels on a near-black canvas.
- **Decision**: Use 1px inset/outset rings at 3-20% alpha; reserve soft blur for genuinely floating panels.
- **Chose**: 1px rings at low alpha   **Over**: layered box-shadows (0 4px 12px rgba(0,0,0,.3)) on every card
- **Reason**: On #08090A a drop shadow is invisible and a strong one muddies the surface; a hairline ring holds the edge without stacking depth.
- **Evidence**: e-shadows, e-shadows-other, e-home-surface  ·  patterns: p-ring-depth
- **Status**: Observed / 实测
- **Guardrail (enforced)**: `{"forbidCss": [], "requireCss": [], "forbidClass": ["shadow-(?!(?:none|sm|inner)\\b)[a-z0-9]+"], "max": {"box-shadow": {"value": "1", "unit": "px"}}, "note": "Offsets must stay 0; blur is allowed only on floating overlays."}`

## Open questions

- Is the hero app frame a live component or a recorded demo?
- Do the light-on-light story panels get a dark-mode variant?
