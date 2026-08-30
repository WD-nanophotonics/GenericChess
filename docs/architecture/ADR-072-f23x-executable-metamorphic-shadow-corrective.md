# ADR-072: F23X executable metamorphic shadow corrective

## Status

The F23X corrective R1 audit is complete as an audit-only checkpoint. Phase A
passed all executable semantic contracts. Phase B ran, but its primary quality
comparison was correctly withheld because the candidate did not complete the
2048-node budget within the outer watchdog. The selected boundary is
`F23Y_EVALUATOR_REPRESENTATION_REASSESSMENT`.

## Decision and invariants

This corrective reran the same five-feature hypothesis with coefficients
`[1,1,1,1,1]` and score form `S * sum(feature_i)`. It added no production
evaluator, search, Native, rules, feature, coefficient, or workflow changes.
The candidate remains an audit-only shadow.

RuleSet-derived profile/type/value/engine/normalization data is built once per
candidate evaluator instance. The permanent counter is one in all eight
non-terminal context parity cases and in the candidate fixed-node/time runs.
Each leaf builds a read-only semantic context from that static profile; the
five feature consumers use that context and do not rebuild the profile.

## Phase A: executable semantic evidence

The audit constructs actual before/after `GameState` pairs and obtains both
feature vectors from those states. It does not enter expected numeric feature
values or deltas. Each result records a semantic witness, the preserved
condition, the actual before/after vectors, and the measured delta. All ten
contracts M1–M10 passed, including material removal, inventory/drop controls,
path unblocking, opponent-action suppression, anchor attack/safety, profitable
capture, history-sensitive recapture, promotion capability, and legal drops.
Type-ID renaming-equivalence passed for every contract. The eight-state
candidate context matched the corrected R1 vector and score exactly under the
`1e-12` tolerance, and the complexity audit found five feature consumers with
no game-name branch or concrete-piece parameter table.

This is `SEMANTIC_CONTRACT_EVIDENCE`, not a playing-strength or Elo claim.

## Phase B: controlled shadow evidence

The audit used the frozen F22 Standard Shogi source at commit
`3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38`, with the unchanged v1 search
harness. Native creation was attempted under the same policy for v1 and the
candidate. The environment returned `PYTHON_AUTHORITY_FALLBACK`; no Native
provider was forced off. The v1 harness parity passed on all ten positions at
512 nodes.

Fixed-node budgets were 128, 512, and 2048 with an outer watchdog. Both
evaluators completed all ten positions at 128 and 512. The candidate did not
complete the 2048 budget within the watchdog, so the progressive run stopped
there. Root-rank instrumentation was unavailable and is recorded as
`ROOT_RANK_HARNESS_UNAVAILABLE`; no rank values were invented. Consequently
the primary quality gate is invalid, with no top-1 delta or control conclusion.

Fixed-time budgets were 0.25s and 1.0s, three repetitions per position and
evaluator, for 120 complete runs. The cost decomposition records evaluator,
context, aggregation, and profile-build measurements. Candidate median
evaluator-time fractions were approximately 0.901 and 0.946; candidate/v1
median NPS ratios were approximately 0.061 and 0.098. Both performance gates
failed. Playing-strength evidence was not run.

These results are `REAL_GAME_BENCHMARK_EVIDENCE`; they do not authorize
production routing, feature tuning, or an Elo claim.

## Boundary and provenance

Because the executable contracts passed but the candidate could not sustain the
primary equal-node budget and fixed-time cost gates failed, the next action is
the minimal evaluator representation reassessment at F23Y. No F23X R2 is
created. The original F23X first-pass script, fixture, test, and ADR remain
byte-identical to commit `1b042de7e1a48bacd9301f506bcd4c3152dd1374`.
Historical F23W strategy bookkeeping remains 13 criteria, maximum 65, with
historical totals 60/46/35/23.
