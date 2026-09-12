# F94 R6 Resumable and Concurrency-Verified Compute Plan (Result-Free)

This is a result-free protocol checkpoint. No Heavy, Arena, native authority
run, or compute approval has been performed.

## Exact remotely published code/PREP binding

- Final R6 code/PREP checkpoint used by the plan: `7808c4042d63d6c795c5e4d5a94898307a8ea34a`
- Frozen PREP byte SHA256: `78b935c3cb5391851bd8a8a574d25ac69714f030a49a01e6006c1d7d8133b8ba`
- Protocol source SHA: `5713b0b6041116d1e03400f0c8db0e3f4d02870a`
- Exact plan artifact: `f94-r6-layer-d-authority-refresh-20260913-v3.json`
- Exact envelope artifact: `f94-r6-layer-d-authority-refresh-20260913-envelope-v3.json`
- Plan SHA256: `786c76eff72948508562049c5f82977a68724bed2b877e6fc2653d51d72969bd`
- Envelope file SHA256: `c91d10b1b1e4b1686328e024e479142c3bcbdc4b90f8e15c8d71eba528737cb7`
- Canonical envelope digest used by `compute-plan-status`: `facd77e06f1c1bf2cb44a78aedb7792b8d346fd493223909767242c264c740a7`

The exact JSON artifacts are attached to the Courier review message so Chat
can independently hash and inspect their bytes.

## Fixed sample, resumability, and selected lanes

The command remains the frozen R6 executor over exactly two controls, tapes
9801/9802/9803, three matchups, 18 invocations, 108 pairs, 216 games, and 216
action traces. The PREP contains 6 frozen opening corpora / 36 frozen
openings. The 216 games are decision-relevant because every control must pass
all three independent 18-pair bootstrap matchups; skipping a matchup or early
stopping would create selection bias and cannot establish `CALIBRATION_READY`.

Each control/matchup/tape invocation uses `run_arena_resumable` with an
identity-bound ignored progress directory. Complete role-swapped pairs are
atomically checkpointed and only a complete six-pair invocation enters score,
censor, or bootstrap aggregation. Valid progress is reused only for the same
immutable protocol identity; corrupt or mismatched progress is an evidence
failure. Fallback, explicit censor, sparse depth, and horizon hits remain
observations in a complete fixed sample. Identity, telemetry,
evidence-integrity, and operational failures stop the fixed sample and leave
partial invocation statistics uncommitted.

The envelope declares 20 logical CPUs, four intended/safe concurrent Arena
lanes, 35 expected / 120 hard wall minutes, 12 expected / 24 hard CPU-hours,
8 GiB expected / 16 GiB hard peak RAM, 800,000,000 maximum nodes, and 163,296
maximum plies. Four lanes are supported by bounded native workers=1 versus
workers=4 observational equivalence at a tiny node/depth budget (excluding
elapsed/NPS telemetry) and a workers=4 interrupted/resume test proving that
completed pairs are not recomputed and the resumed summary equals an
uninterrupted summary. No nested native engine threads are enabled.

Chat scientific approval and registered Supervisor approval must bind the
exact plan SHA, envelope digest, argv, PREP SHA, and code SHA before any Heavy
invocation. This checkpoint requests review only; it does not authorize the
216-game run.

## Verification

The focused R6 and arena integrity tests passed (34 tests), including
resumable executor routing, fatal partial-aggregation protection, bounded
native concurrency equivalence, and workers=4 interrupted/resume behavior.
`compute-plan-status` returned `compute_size=large` with no approval present.
