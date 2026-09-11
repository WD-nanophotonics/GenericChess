# GenericChess F84 C1 Teacher Extended Cost Calibration

F84 is a bounded, resource-only calibration stage over exactly three already
frozen F83 roots. It does not replace roots, label the 36 train / 12 dev
acquisition roots, fit C2, run Arena, or change production semantics.

The stage uses the exact F62/F59 teacher contract: C1 as parent and observer,
root budgets 2k/40k/80k plus observer 2k, all-legal child budget 1k, selected
child budgets 10k/20k, depth 12, 8 MiB TT, and root-window pruning disabled.
Each selected resource root is attempted once with a 720-second wall cap, at
most two roots concurrently, and a 1500-second whole-stage hard wall.

The explicit bounded resource envelope declares 16 logical CPUs, two active
root lanes, expected wall/CPU bounds of 24.5 minutes / 4.8 hours, hard bounds
of 25 minutes / 5 hours, one stage, zero games, zero Arena pairs, zero plies,
and a 1,271,000 maximum declared node budget. Any cap preserves unknown fields
as `null`; it never writes zero teacher calls or Q labels.

The flow schema requires positive integer ceiling fields, so its minimum
representations are 1 for games, Arena pairs, and plies, and 5 for hard CPU
hours. The durable execution contract records the effective F84 workload as
zero for all three non-search quantities.

Durable output: `artifacts/f84_c1_teacher_extended_calibration/calibration.json`.
Resource roots remain permanently outside future C2 training corpora.

## Result

The single bounded stage completed all three roots with no retry:

- `reachable_random-r-00`: 330.968 wall seconds, 25 legal actions, 6 selected actions, 12 teacher calls.
- `c1_on_policy-r-00`: 399.489 wall seconds, 32 legal actions, 7 selected actions, 14 teacher calls.
- `c1_pv_corridor-r-00`: 265.032 wall seconds, 32 legal actions, 7 selected actions, 14 teacher calls.

The stage took 596.502 wall seconds, with 40 teacher calls and 141 total
search calls. All three results were `COMPLETE`; classification is
`C1_TEACHER_COST_EXTENDED_CALIBRATED`. Calibration artifact SHA-256:
`9fd8eb417a71fb1c5e7af5225c84fb73facb0549eeaae229a6923e7be8a4677b`.
