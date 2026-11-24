# VERIFY — Binance

Renders are deterministic re-encodings of `dna.json`: byte-equality proves the artifacts were not edited after rendering, not that every authored value is faithful. Fidelity stays `unverified` until a comparison is recorded.

| Check | Result | Detail |
| --- | --- | --- |
| dna.json contract | PASS | SSOT valid (evidence/measurements/patterns/taste/tokens) |
| token resolution | PASS | all aliases resolve, no cycles |
| single source (R3) | PASS | all artifacts are deterministic renders of dna.json, no post-render edits |
| guardrail static conflicts | PASS | no bound forbids the property it bounds |
| guardrail pattern self-test | PASS | every forbidClass pattern compiles and catches a known violation |
| system/ colour scope | PASS | canvas token #181A20 (dark); chrome shell light |
| interaction delta | unverified | no interactions block (schema 1.0 run or capture without probe) |
| shadcn theme slots | PASS | all required slots mapped |
| clip bricks | n/a | no clips/ directory |
| preview.html (self-contained) | PASS | single file, same-folder tokens.css, no remote assets |
| incremental freeze | PASS | no frozen block changed since the last render |
| evidence coverage | PASS | 46 evidence entries cited |
| restraint guardrails | PASS | 2/2 restraint principles carry machine-readable guardrails |
| anti-slop (authored prose) | PASS | 0 hit(s) |
| guardrail (generated code) | unverified | no --check-code supplied |
| visual fidelity | unverified | no fidelity.json — requires a side-by-side comparison at matching viewports |
| full system/ site | PASS | app shell present (rail + canvas + panel routing) |

Generated at 2026-11-24T04:46:01+00:00.
