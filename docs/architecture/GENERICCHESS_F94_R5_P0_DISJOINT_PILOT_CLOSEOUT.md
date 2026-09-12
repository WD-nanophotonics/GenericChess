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
