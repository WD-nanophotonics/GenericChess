# F94-R5 P0 disjoint pilot PREP and executor

Status: the repaired, provenance-bound v2 PREP was executed once through the
approved small/medium Heavy gate. The ignored RESULT completed exactly six
Arena invocations, six pairs, twelve games, and twelve action traces. It is
descriptive pilot evidence only; no Stage 1 or 216-game R5 RESULT was launched.

Execution binding: sandbox `d62edb33a28603d41822c8d922f6611c8c2fa952`, plan
`f94-r5-p0-disjoint-pilot-20260912-v2` SHA
`f2ccacb3bd5e306c082d0c944741c2384b7fb2244d1f28cc8550cdf749850978`, envelope
SHA `8f78d8ba510edd23c05f3f1243d353e324c13801815f44174491119d689f6139`, and
v2 PREP SHA `466044894331091d716bcdf709e5b3b780d133b861fa03cdfeb39ac0ca08a395`.
The ignored RESULT SHA is
`ca9da01bbac668972be3a81e5da279298f11cb0c1c4e7d84dd5d159de8d19d27`.

## Frozen pilot contract

`GENERICCHESS_F94_R5_P0_DISJOINT_PILOT_PREP.json` (schema v2) defines an independent
descriptive probe for Built-in Western Chess and Built-in Standard Shogi. It
uses three deterministic pilot tape seeds (`9501`, `9502`, `9503`) and one
role-swapped strongest-vs-weakest pair per tape: 4096 versus 256 nodes per
move, depth 12, 8 MiB TT, and workers=1. The authoritative R5 tape seeds
(`9401`, `9402`, `9403`) and all of their opening rows are rejected as pilot
inputs. The F86N-R1 boundary remains an A/C prerequisite short circuit with
zero native compilation and zero Arena work.

The pilot has exactly six invocations, six pairs, twelve games, and twelve
action traces. Its direction is descriptive only: all three tape scores above
0.5 are `POSITIVE_DIRECTION`, all three below 0.5 are `NEGATIVE_DIRECTION`,
and ties or mixed signs are `MIXED_OR_UNCERTAIN`. Explicit fallback/censor or
operational failure takes precedence. Depth censoring requires a strongest-
versus-weakest child-only completed-depth hit fraction of at least 0.5;
horizon censoring requires a strongest-vs-weakest max-ply hit fraction of at
least 0.5. These fractions are retained per tape as descriptors, then pooled
over all three tapes before applying either censor gate (3/6 is the boundary).
An isolated per-tape hit therefore does not invalidate the pilot. The PREP
records matching `source_sandbox_sha` and `protocol_source_sha`; the latter is
the prior immutable commit containing the repaired executor and generator.

## Observed pilot result

The Western candidate was `HORIZON_CENSORED`: all six strongest-vs-weakest
games reached max ply (pooled horizon fraction `6/6`), while pooled child
depth hits were `6/2994`. The Standard Shogi candidate was
`MIXED_OR_UNCERTAIN`, with pooled horizon `0/6` and child-depth `0/206`. The
F86N-R1 boundary remained `PREREQUISITE_A_C_NOT_PASS` with zero Arena work and
zero native compilation. These observations remain non-poolable with R2, R3,
and authoritative R5 and do not authorize Stage 1 or Layer-D PASS.

## Executor boundary

`scripts/f94_r5_pilot_executor.py` validates the frozen PREP fingerprint,
protocol provenance, source R5
identity, disjoint corpus/opening identities, candidate/checkpoint/evaluator
identity, seat-swapped pair completeness, and all twelve action traces before
writing ignored pilot RESULT evidence. It never imports or calls the full R5
`measure_strength_response()` reducer. The RESULT is marked
`not_layer_d_authority=true`, `observed_not_poolable=true`, and keeps R2, R3,
and authoritative R5 observations out of the pilot namespace. Stage 1 is never
automatically authorized.

## Verification

The focused pilot suite passed (26 tests), including pooled 1/6 and 3/6 horizon
and depth boundaries, isolated-hit direction, evaluator mismatch rejection
before native compilation, exact invocation/game/trace counts, and protocol
provenance:

```text
tests/test_f94_r5_pilot_executor.py
tests/test_f94_r5_result_executor.py
tests/test_strength_response.py
```

The test runner used injected fake Arena summaries only. The single production
pilot run used the approved P0 Heavy command; no adjacent compute or tuning was
started.

## Western termination-semantics audit

This is a static, code-derived audit requested after the pilot. It made no
Arena/Heavy run, Stage 1 run, Layer-E work, evaluator/search tuning, or change
to the built-in ruleset. The production identity remains the Western
fingerprint `7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35`.

The evidence is the canonical builder in
`generic_chess/rules/western_chess.py`, the generic schema in
`generic_chess/rules/schema.py`, and the shared/semantic terminal paths in
`generic_chess/core/terminal.py` and `generic_chess/core/semantic_executor.py`:

* Western sets `repetition_limit=100000`, `repetition_policy="draw"`,
  `max_ply=1000`, and `stalemate_result="draw"`.
* Western supplies no `automatic_adjudications`. The schema has no separate
  threefold/fivefold, 50-move/75-move, or insufficient-material fields, and the
  Western builder does not declare any such rule.
* Both terminal implementations first classify a position with no legal move
  as checkmate or stalemate, then check repetition, automatic adjudication,
  and finally `max_ply`. The semantic executor follows the same precedence.
* A path bounded by `max_ply=1000` can contain at most 1001 position
  occurrences including the initial sentinel, so the configured repetition
  threshold of 100000 is unreachable before the max-ply boundary. Thus the
  observed Western `max_ply` tails do not establish repetition; the actual
  reachable terminal rules are checkmate, stalemate, and max-ply (with the
  no-legal-move check taking precedence at the boundary).

The repository history shows the `100000/1000` pair was introduced with the
single productization commit and contains no rationale that would justify
guessing a different intent. The audit therefore does not alter the ruleset.
The compatibility choices are explicit: (A) changing production Western
semantics would require a new fingerprint, compatibility review for old
artifacts, and recalibration of downstream Layer-C/Layer-D evidence; (B)
keeping the product identity and adding a separate mature qualification
control (for example `western_chess_qualification_control_v1`) preserves old
artifacts and isolates any standards-oriented terminal contract. Under this
work order, B is the safer follow-on boundary, but no new control or gameplay
rule is implemented here. The existing F24F perft fixture remains the
historical certification control.

Standard Shogi is unchanged: its product ruleset separately declares
`repetition_limit=4`, `repetition_policy="continuous_check_loss"`, and the
500-ply no-contest automatic adjudication. Its pilot observation remains
`OBSERVED_NOT_POOLABLE`.

## Western qualification-control PREP

The follow-on qualification-only control is now frozen without running it.
`western_chess_qualification_control_v1` is implemented in
`scripts/f94_r5_western_qualification_control.py` and is deliberately absent
from the public built-in catalog. It is mechanically derived from
`build_western_chess_ruleset()` with exactly one gameplay delta:
`repetition_limit: 100000 -> 5`. Board, pieces, movement, promotion,
castling, en-passant, `repetition_policy="draw"`, `max_ply=1000`, and the
evaluator family remain unchanged.

Frozen identities:

* production Western fingerprint:
  `7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35`
* qualification-control fingerprint:
  `314729d06f8a47fc653779fe5b1eab6e6b9f2e923436c1c79a6f06cd12812e14`
* qualification checkpoint:
  `9ff9facc235577e3631c499cee549916935153d47ef12dd2a6bfc18409ba9b74`
* evaluator identity: `learnable-material-v1`

The result-free PREP is
`docs/architecture/GENERICCHESS_F94_R5_WESTERN_QUALIFICATION_CONTROL_PREP.json`
with PREP fingerprint
`8bdcbe0aa3723394c62b3a190dcb3662b5933c053dd13400ad6fe28e87f14b51`.
Its source/protocol SHA is `eee600237685edf67be646e6d7eaa91b48b691ce`, and it
freezes disjoint tape seeds `9601/9602/9603`, one role-swapped pair per tape,
4096 versus 256 nodes, depth 12, 8 MiB TT, and workers=1. The PREP records
`3` invocations, `3` pairs, `6` games, and `6` action traces as a future
budget only; no Arena, Heavy, or result file was run or created. It is marked
`OBSERVED_NOT_POOLABLE` and must not be merged with the old P0, R2, R3, or
authoritative R5 samples.

The cheap regression suite proves that the production builder and public
catalog are unchanged, the only serialized gameplay delta is the repetition
limit, all existing F24G canonical perft counts remain exact at their
certified depths, and a reversible knight cycle reaches five occurrences and
returns `REPETITION` at ply 16 before `max_ply`. The new control and PREP are
qualification evidence only; they do not authorize Layer-D PASS or a
production ruleset change.

## Qualification-control executor

The qualification-only executor is now implemented at
`scripts/f94_r5_western_qualification_executor.py`. It is fail-closed on the
frozen PREP schema, source/protocol commit, PREP fingerprint, production and
qualification fingerprints, checkpoint/evaluator identity, exact `5`
repetition delta, public-catalog exclusion, and disjoint tape seeds. It
validates all three opening-corpus identities before invoking an injected or
real Arena runner, requires one seat-swapped pair per tape, retains action
traces, pools depth/horizon descriptors at candidate level, and emits
`QUALIFICATION_CONTROL_RESULT_COMPLETE` only for the exact 3-invocation,
3-pair, 6-game, 6-trace shape. Results are explicitly
`control_only`, `not_layer_d_authority`, `observed_not_poolable`, and
`production_changed=false`.

This work package exercised only injected fake Arena summaries. The focused
publish gate passed 9 tests across the executor, qualification-control
identity/repetition/perft contracts, and Western termination audit. No real
qualification control pilot, Arena, Heavy envelope, Stage 1, Layer-E, or
216-game RESULT was generated or run.

## Qualification-control executor R1

Chat's R1 review found authority gaps in the first executor implementation.
They are closed in
`scripts/f94_r5_western_qualification_executor.py` without changing the
qualification-control design or running its pilot:

* The loader requires the exact frozen PREP path and byte SHA
  `bf5b0189aec82766d1095be8ee3396e05e0a9ed8a029bbbae3312621c78286b2`
  before parsing JSON. Protocol/source SHA is fixed to
  `eee600237685edf67be646e6d7eaa91b48b691ce`; the P0 and R5 source artifact
  paths and byte SHAs are fixed as well.
* Production Western fingerprint, exact serialized gameplay delta
  `["repetition_limit"]`, `100000 -> 5`, and public-catalog exclusion are
  runtime guards before native compilation.
* One `compile_ruleset_for_execution()` object is now the authority for
  evaluator profile/checkpoint, native compilation, opening generation, and
  any future Arena call. All three frozen opening corpora are validated before
  the first runner invocation.
* RESULT provenance now includes protocol/source/result sandbox SHAs,
  executor path and byte SHA, exact PREP byte SHA, and explicit
  `p0/r2/r3/r5_observations_pooled=false` fields. Operational failure produces
  an incomplete, unresolved result rather than `COMPLETE`.

The R1 focused suite passed 18 tests covering byte/protocol tamper, exact
source paths, production/delta/catalog guards, pre-run corpus validation,
single executable-object authority, 1/6 versus 3/6 pooled horizon and depth
censoring, positive/negative/mixed direction, fallback precedence,
operational failure, six complete traces, evaluator mismatch, and RESULT
provenance. No Heavy envelope or qualification pilot was created or run.

## Qualification-control pilot execution

The first and only authorized qualification-control run was executed after
R1 hardening under the exact versioned small-or-medium resource envelope and
compute plan. The run was bound to sandbox
`8e92f933dcab91be6d566c9d6e030e1a059562f0`, PREP byte SHA
`bf5b0189aec82766d1095be8ee3396e05e0a9ed8a029bbbae3312621c78286b2`, compute
plan SHA `43f55b12b47d5eb29f6ec168a9769b2c3470cf03114f9eb534c5db83f6c8ccaa`,
and resource-envelope SHA
`09ad2f979f23d07e8510c5522f74f8c45b66e932b3aa719b0b32a7667488e19a`. Heavy
run `f94-r5-western-qualification-control-20260912-v1-36701320ec5f`
completed with exit code 0; the ignored result artifact has SHA256
`76ba0ae0b0692481262b7f7c2c52b96215fb94b195d09b89931becce683539f4`.

The result is `QUALIFICATION_CONTROL_RESULT_COMPLETE` and remains explicitly
control-only, not Layer-D authority, not poolable with P0/R2/R3/R5, and leaves
the production ruleset unchanged. It contains exactly 3 role-swapped pairs,
6 games, and 6 action traces. Pooled pair score is `0.9166666666666666` with
`POSITIVE_DIRECTION`; tape scores are `9601: 1.0`, `9602: 1.0`, and
`9603: 0.75`. All six games avoided the 1000-ply and child-depth ceilings;
five ended in checkmate and one ended in the qualification control's expected
`repetition` result. Pooled horizon and child-depth censoring are both zero.

This is qualification evidence only. It does not authorize a production
ruleset change, Layer-D PASS, Stage 1, full R5, additional games, or pooling
with any prior pilot.

## Qualification-control Stage-1 PREP and executor

Chat's next phase is frozen as a result-free Stage-1 calibration, with no
Arena or Heavy execution in this work package. The PREP is
`docs/architecture/GENERICCHESS_F94_R5_WESTERN_QUALIFICATION_CONTROL_STAGE1_PREP.json`
with schema
`generic-chess-f94-r5-western-qualification-control-stage1-prep-v1`, PREP
fingerprint
`eaa79501376c37fb2493743447929cfae6813d3a17e631456ed93e0c107b8f3d`, and
byte SHA
`18775f480c7602b535ac4ebbc234a0deeb11ce29cbfb66eaaf31d51a2cc5deee`.
Its protocol/source commit is `f037acdffc1021efa946db16803b880648568085`.

Stage-1 uses only new tapes `9701/9702/9703` and explicitly rejects the old
`9401/9402/9501/9502/9601/9602/9603` seeds and corpora. It freezes the same
qualification-control identity (`repetition_limit=5`, checkpoint
`9ff9facc235577e3631c499cee549916935153d47ef12dd2a6bfc18409ba9b74`, and
`learnable-material-v1`) with child `4096` nodes/move, parent `256`, depth
`12`, TT `8 MiB`, and workers `1`. Each tape has six role-swapped pairs, for
exactly 3 Arena invocations, 18 pairs, 36 games, and 36 action traces. The
old pilot is permanently excluded from every effect estimate, confidence
interval, and pool.

The executor is
`scripts/f94_r5_western_qualification_stage1_executor.py`. It validates all
18 frozen opening identities before native compilation, uses one compiled
ruleset object through profile/checkpoint/native/opening/Arena, and fails
closed on identity, count, fallback, censor, or operational mismatches. It
computes a deterministic 10,000-resample, 95% percentile bootstrap over the
Stage-1 18 pair scores only (`seed=9701001`). Classification is unresolved for
fallback, explicit censor, or operational failure; depth/horizon censoring
uses pooled fractions at `0.5`; otherwise `STABLE_POSITIVE_CONTROL` requires
all three tape means above `0.5` and the independent 18-pair bootstrap lower
bound above `0.5`, with `MIXED_OR_UNCERTAIN` otherwise. The result remains
control-only and cannot produce Layer-D PASS.

The Stage-1 focused suite covers exact shape and disjointness, deterministic
bootstrap, single-object authority, unresolved precedence, operational
failure, and pre-run opening validation. This phase intentionally creates no
Arena result, Heavy envelope, or Stage-1 evidence.
