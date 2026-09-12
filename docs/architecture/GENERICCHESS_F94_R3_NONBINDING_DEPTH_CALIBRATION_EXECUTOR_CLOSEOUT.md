# GenericChess F94-R3 nonbinding depth-calibration executor

Status: the result-free executor is published for review; no R3 Arena, Heavy
computation, Stage 1, 216-game schedule, tuning, or adjacent evaluation has
run or is authorized by this checkpoint.

`scripts/f94_r2_strength_calibration.py --r3-depth-calibration` is a separate
R3 entry point, rather than a reinterpretation of R2 `--stage0`. It loads only
the independent R3 PREP and fails closed on its schema, status, result-free
flag, fingerprint, source R2 PREP byte hash, source R2 fingerprint, and exact
candidate/corpus/opening/boundary identities. It rebuilds each tape and checks
its corpus ID, opening index 0, seed, action count, final-position identity,
ruleset, evaluator, and checkpoint before Arena.

Every R3 Arena configuration is read from the frozen R3 PREP: 4096-vs-256
nodes per move, `max_depth=64`, 8 MiB TT, one pair per tape, and one worker.
The R3 censor helper receives that frozen depth explicitly; it does not rely on
the R2 depth-12 global. Boundary V4-3 short-circuits before native search or
Arena construction.

The future R3 result schema is separate and non-authoritative. It retains
R3-only role-swapped evidence, searched-node/NPS/depth/fallback telemetry,
per-tape direction, descriptive CI, and exact actual invocation/game counts.
It reports complete only at exactly six invocations and twelve games, and
always sets `not_layer_d_authority=true` and `r2_observations_pooled=false`.

Focused tests cover tampered R3 PREP and R2 binding rejection before Arena;
the 64-depth configuration and censor boundary; the zero-compute boundary
short circuit; exact mocked six-invocation/twelve-game accounting; the
non-authoritative result schema; and exclusion of R2 observations from R3
statistics.

Any actual R3 run still requires a newly generated exact resource envelope and
compute plan, then explicit Chat and registered-Supervisor approval bound to
the current sandbox SHA, canonical digests, and exact command argv.
