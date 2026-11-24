# Model — dna.json and the token layers

`dna.json` is the only authored file. Six root blocks, no extras:

```
schemaVersion · meta · evidence · measurements · patterns · taste · tokens · interactions
```

`schemaVersion` is `"1.1"`; the full contract (including the optional `interactions` block) ships
as `dna.schema.json` at the repo root so other tools can validate without running Python.

`build_artifacts.py` validates all of it before rendering. Read the error, fix the source,
rerun. Never patch a rendered file.

## meta

| Field | Required | Notes |
| --- | --- | --- |
| `name`, `source`, `domain` | yes | domain = host without `www.`; used for the output folder |
| `mode` | yes | `dna` or `full` |
| `capturedAt`, `viewport` | recommended | from `capture/meta.json` |
| `captureIsolated` | yes (if false) | `false` requires `isolationNote` |
| `crawl.pages` | recommended | >4 pages needs `crawl.budget: "user-expanded"` |
| `limitations` | recommended | one line per known blind spot |
| `openQuestions` | optional | things a follow-up run should resolve |
| `incremental` | set by tooling | `{targets[], frozen[], updatedAt}` — the declared scope of the last run; never author by hand |

## evidence

See `sense.md`. Ids are stable; every `observed`/`inferred` item in every block references them,
and `validate()` rejects dangling ids.

## measurements / patterns / taste

Shapes are defined in `infer-measure.md`, `infer-pattern.md`, `infer-taste.md`. Required
relations enforced by the validator:

- `pattern.evidence` → existing evidence ids;
- `taste.evidence` → existing evidence ids, `taste.patterns` → existing pattern ids;
- at least one `taste.kind == "restraint"`, and each restraint has a non-empty `guardrail`;
- `taste.chose != taste.over`.

## interactions (schema 1.1)

```json
{"locator": "button.hds-button.primary", "kind": "button", "status": "observed",
 "evidence": ["e-buttons"],
 "hover": {"measured": true, "delta": {"color": ["rgb(83, 58, 253)", "rgb(46, 43, 140)"]}},
 "focus": {"measured": true, "delta": {"outline": ["0px solid rgba(0, 0, 0, 0)", "3px solid rgba(84, 82, 251, 0.75)"]}}}
```

- `locator` is `tag` plus up to two classes, resolvable with `querySelector`;
- `kind` is `button | link | card | input`;
- only the six diffed properties are legal inside `delta`, always `[before, after]`;
- a phase that produced nothing carries `{"measured": true, "note": "no computed change"}`;
- an unmeasured phase carries `{"measured": false, "note": "not focusable"}` and must not claim `delta`;
- omit the whole block when nothing was measured — an empty array is a schema error.

## tokens — three layers

| Layer | Is | Example |
| --- | --- | --- |
| `primitive` | a raw value with no meaning attached | `color/neutral/950 = #08090A` |
| `semantic` | a role, aliased to a primitive | `color/canvas → color/neutral/950` |
| `component` | a reusable part or multi-property recipe alias | `radius/control → radius/md` |

Rules:

- every token has `id`, `css` (`--kebab-case`, unique), `type`, `layer`, `status`, `values`;
- `status` is `observed | inferred | proposed` — **`unknown` never appears in tokens**; an
  unknowable value stays in prose or a measurement;
- `values` maps mode → literal or `{"alias": "<id>"}`; every declared mode must resolve;
- aliases must target an existing token **of the same type** and produce no cycles (the
  validator walks every chain);
- `dimension` and `duration` literals need explicit units (`px`, `rem`, `%`, `s`, `ms`) — `"4"`
  is rejected so a render cannot silently emit a unitless length;
- prose in token values is banned: values are CSS-usable strings.

Types: `color, dimension, number, duration, fontFamily, fontWeight, shadow, gradient, easing,
string`. `fontWeight` holds the weight only; the family lives in a `fontFamily` token and the
pairing lives in a `semantic` alias such as `font/display`.

### Naming

- `color/<role>/<state>` for semantics: `color/text/primary`, `color/action/bg`;
- keep the source's own names when you can read them; when you cannot, names are `inferred` and
  the reason goes in `evidence`;
- do not invent a 50–950 palette, a dark mode, or a second theme "for completeness" — propose
  them explicitly with `status: proposed` and a `reason`.

## Modes

`meta.modes` defaults to `["default"]`. A dark section is not a site-wide dark mode: only add a
mode when the same component genuinely renders differently in a named context, and every token
then must define that mode.

## What the validator will not tell you

It proves internal consistency — ids, references, cycles, units, statuses, drift. It cannot prove
a value is faithful to the site, that a naming is right, or that the guardrails are well judged.
Those stay your responsibility and belong in `VERIFY.md` as `unverified` when untested.
