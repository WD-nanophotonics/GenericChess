# DEV_AUX2613 — TDLeaf UNKNOWN receipt contract

Status: two deterministic tests pass; science remains OPEN.

The exact task2492 TDLeafEpisode implementation was exercised with synthetic,
fully specified receipts only. With two complete receipts followed by
finish(None), the first known inter-receipt TD residual updates the free
material coefficient, while the unobserved final residual contributes no
target. A fixed pawn coefficient remains unchanged. An incomplete receipt
adds no observation; with an unknown actual game result it creates no terminal
residual or weight update.

A first test attempt failed because the test incorrectly expected an incomplete
receipt to reset the episode and then supplied a known terminal result. The
existing implementation intentionally ignores incomplete receipts; the known
terminal result then updates the preceding complete observation. That test
assumption was wrong, not the learner. Attempt-1 script and diagnosis are kept
unchanged, and the corrected contract was registered before the passing rerun.

This is not a strength result, an evaluation of convergence, or a faithful
Beal–Smith reproduction. No games, W/L labels, fitted weights, or endpoint
comparisons were used. Exact implementation hashes and command are in
started.json and result.json.
