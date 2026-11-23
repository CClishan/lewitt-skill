# VERIFY — Linear

Renders are deterministic re-encodings of `dna.json`: byte-equality proves the artifacts were not edited after rendering, not that every authored value is faithful. Fidelity stays `unverified` until a comparison is recorded.

| Check | Result | Detail |
| --- | --- | --- |
| dna.json contract | PASS | SSOT valid (evidence/measurements/patterns/taste/tokens) |
| token resolution | PASS | all aliases resolve, no cycles |
| single source (R3) | PASS | all artifacts are deterministic renders of dna.json, no post-render edits |
| incremental freeze | PASS | no frozen block changed since the last render |
| evidence coverage | PASS | 28 evidence entries cited |
| restraint guardrails | PASS | 2/2 restraint principles carry machine-readable guardrails |
| anti-slop (authored prose) | PASS | 0 hit(s) |
| guardrail (generated code) | unverified | no --check-code supplied |
| visual fidelity | unverified | requires specimen comparison at matching viewports |
| full system/ site | n/a | DNA mode does not build system/ |

Generated at 2026-11-23T12:21:29+00:00.
