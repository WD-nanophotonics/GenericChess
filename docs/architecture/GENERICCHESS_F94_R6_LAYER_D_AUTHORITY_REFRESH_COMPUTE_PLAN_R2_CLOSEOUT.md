# F94 R6 Corrected Layer-D Compute Plan (Result-Free)

This is a corrected plan-only checkpoint. No Heavy, Arena, native run, or
compute approval has been performed.

## Exact remotely published code/PREP binding

- Final R6 code/PREP checkpoint used by the plan: `8a8f61cad7af6b42ac822cb56539bf4e2126efb9`
- Frozen PREP byte SHA256: `f160c1052531b5763b17bf4ec085ae2b63d7828b4de5baef0c493980b2a54efb`
- Protocol source SHA: `1c21371c4ef9cc6b7c3e3a0833efcf0c833afdeb`
- Exact plan artifact: `f94-r6-layer-d-authority-refresh-20260913-v2.json`
- Exact envelope artifact: `f94-r6-layer-d-authority-refresh-20260913-envelope-v2.json`
- Plan SHA256: `ae25afcfb655d08eb60d440504520140ada3822e675afb593b7befc6af64d418`
- Envelope digest: `d7a358b62d2376ccbc2ec713d372aca87463699dc717805a586a72e038796450`

The two exact JSON artifacts are attached to the Courier review message so
Chat can independently hash and inspect their bytes.

## Fixed sample and selected lanes

The command remains the frozen R6 executor over exactly two controls, tapes
9801/9802/9803, three matchups, 18 invocations, 108 pairs, 216 games, and 216
action traces. The 216 games are decision-relevant because every control must
pass all three independent 18-pair bootstrap matchups; skipping a matchup or
early stopping would create selection bias and cannot establish
`CALIBRATION_READY`.

The corrected envelope declares 20 logical CPUs, four intended/safe concurrent
Arena lanes, 35 expected / 120 hard wall minutes, 12 expected / 24 hard
CPU-hours, 8 GiB expected / 16 GiB hard peak RAM, 800,000,000 maximum nodes,
and 163,296 maximum plies. The four-lane choice is supported by the bounded
synthetic six-pair `workers=4` out-of-order completion smoke
`tests/test_learning_arena_integrity.py::test_resumable_arena_concurrent_completion_order_is_deterministic`,
which passed deterministically. No nested native engine threads are enabled.

The plan preserves pair-granular checkpoints and fail-closed telemetry,
identity, censor, and accounting rules. It forbids intermediate-result
selection, one-control/108-game alternatives, and any lane increase without a
new protocol and approval. Chat scientific approval and registered Supervisor
approval must bind the exact plan SHA, envelope digest, argv, PREP SHA, and
code SHA before any Heavy invocation.

## Verification

Focused R6/workflow tests passed, including the attachment-forwarding guard;
the bounded concurrency smoke passed; and `compute-plan-status` returned
`compute_size=large` with no approval present.
