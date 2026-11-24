# VERIFY — Steno.ai

Renders are deterministic re-encodings of `dna.json`: byte-equality proves the artifacts were not edited after rendering, not that every authored value is faithful. Fidelity stays `unverified` until a comparison is recorded.

| Check | Result | Detail |
| --- | --- | --- |
| dna.json contract | PASS | SSOT valid (evidence/measurements/patterns/taste/tokens) |
| token resolution | PASS | all aliases resolve, no cycles |
| single source (R3) | PASS | all artifacts are deterministic renders of dna.json, no post-render edits |
| guardrail static conflicts | PASS | no bound forbids the property it bounds |
| guardrail pattern self-test | PASS | every forbidClass pattern compiles and catches a known violation |
| system/ colour scope | PASS | canvas token #F0EDDA (light); chrome shell light |
| interaction delta | PASS | 2/3 targets recorded a hover/focus delta |
| shadcn theme slots | PASS | all required slots mapped; 1 declared UNMAPPED: --destructive |
| clip bricks | PASS | 1 brick(s) valid |
| preview.html (self-contained, dual view) | PASS | single file, same-folder tokens.css, no remote assets |
| incremental freeze | PASS | no frozen block changed since the last render |
| evidence coverage | PASS | 44 evidence entries cited |
| restraint guardrails | PASS | 1/1 restraint principles carry machine-readable guardrails |
| generated-code script scope | PASS | duplicate var names and undeclared identifiers are both caught (injected probes) |
| anti-slop (authored prose) | PASS | 0 hit(s) |
| guardrail (generated code) | PASS | 0 violation(s) — scanned steno.ai/system |
| visual fidelity | unverified | no fidelity.json — requires a side-by-side comparison at matching viewports |
| full system/ site | PASS | dual view present (top bar + Live Preview 01-05 + Specs) |

Generated at 2026-11-24T12:05:20+00:00.
