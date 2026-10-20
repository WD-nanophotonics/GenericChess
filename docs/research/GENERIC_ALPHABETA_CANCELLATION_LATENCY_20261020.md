# Generated-rule AlphaBeta cancellation latency —2026-10-20

## Question

Does the actual public `AlphaBetaPlayer.choose_action` path return slowly after
the UI's cooperative `CancellationToken` is cancelled? This follows the prior
Undo/Redo UI probe, which used a cooperative fake player and explicitly did not
measure AlphaBeta latency.

## Bounded screen

Six new 6x6/8x8 generated rules used `classic_like`, `bilateral_random` and
`free_random` setups, hybrid generation enabled, and
`require_no_opening_win_in_one=True`. Each initial position was searched twice;
the token was cancelled after 50ms and 100ms. Search limits were depth32,
5,000,000 nodes, a 1.5s deadline, qdepth3/hard-qdepth6. A single local search
thread per sequential case called the public `AlphaBetaPlayer`; the test thread
measured from `token.cancel()` to return. Every returned decision reported
`cancelled`, retained a legal action, and left the session root object unchanged.
All 12 searches had started and completed at least depth1. The observed
cancel-to-return median was0.4615ms, maximum2.330ms. Raw rows, including seeds,
node counts and timings, are preserved in ignored
`.local_agent/primary-mainline-20261020/cancellation-latency-no-opening-win.json`.

An initial unfiltered eight-rule screen was unsuitable as the main estimate:
three fixtures returned `root_immediate_win` before cancellation. Its raw rows
remain in ignored `cancellation-latency-screen.json`; those six results are not
counted as cancellation observations.

## Interpretation

This small initial-position screen finds no measurable AlphaBeta cancellation
delay that warrants changing per-node polling, UI waits or backend contracts.
It is not a population estimate, busy-process stress test, midgame benchmark or
guarantee for every indivisible provider call. Although the standard
`AlphaBetaPlayer` configuration was used, the screen did not persist native
legality/fallback counters, so it makes no claim about which provider path each
rule exercised. Do not expand this into a stress campaign absent a concrete
slow-cancel trace from a real UI task. The earlier cooperative UI integration
regression remains complementary evidence, not a substitute for this screen.
