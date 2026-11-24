# VERIFY — Stripe

Renders are deterministic re-encodings of `dna.json`: byte-equality proves the artifacts were not edited after rendering, not that every authored value is faithful. Fidelity stays `unverified` until a comparison is recorded.

Last run: **incremental** — scope `taste`; frozen `meta, evidence, measurements, patterns, tokens`.

| Check | Result | Detail |
| --- | --- | --- |
| dna.json contract | PASS | SSOT valid (evidence/measurements/patterns/taste/tokens) |
| token resolution | PASS | all aliases resolve, no cycles |
| single source (R3) | PASS | all artifacts are deterministic renders of dna.json, no post-render edits |
| system/ colour scope | PASS | canvas token #FFFFFF (light); chrome shell light |
| interaction delta | PASS | 2/3 targets recorded a hover/focus delta |
| shadcn theme slots | PASS | all required slots mapped; 1 declared UNMAPPED: --destructive |
| preview.html (self-contained) | PASS | single file, same-folder tokens.css, no remote assets |
| incremental freeze | PASS | no frozen block changed since the last render — scope ['taste'], frozen ['meta', 'evidence', 'measurements', 'patterns', 'tokens'] |
| evidence coverage | PASS | 32 evidence entries cited |
| restraint guardrails | PASS | 2/2 restraint principles carry machine-readable guardrails; incremental targets=['taste'] frozen=['meta', 'evidence', 'measurements', 'patterns', 'tokens'] |
| anti-slop (authored prose) | PASS | 0 hit(s) |
| guardrail (generated code) | PASS | 0 violation(s) — scanned stripe.com/system |
| visual fidelity | PARTIAL | 1 composition(s), 4 recorded deviation(s), status=partial |
| full system/ site | PASS | app shell present (rail + canvas + panel routing) |

Generated at 2026-11-24T03:03:36+00:00.
