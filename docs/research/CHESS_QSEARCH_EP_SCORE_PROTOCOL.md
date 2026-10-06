# Actual qsearch effect on a different frozen EP fixture

New semantic integration control, no usefulness reference or old-tree retry.
Start an explicitly synthetic native Chess game at
7k/3p4/8/4P3/8/8/8/K7 b - - 0 1. Its initial history is exactly this root,
not a claim that it came from native initial play. Public d7d5 supplies the
real next-turn token; preserve this two-record history. Pinned author uses
the same synthetic initial root and full stacks for all child comparisons.
All children ongoing/nonchecking required; no unexpected family substitution.

Fixed geometric_half normalized five-mode coefficients and scale100000 from
previous qualification, never tuned. Call actual quiescence once with the
unchanged classifier and once with a research-only runtime adapter. qdepth1,
harddepth2,no TT/order,full window,no root iteration reserve. Independent
complete-child one-step stand-pat/capture reference supplies expected score.
Adapter creates immutable-position/terminal views while runtime is pushed,
returns capture/check/promotion/terminal list then restores state. All probe
pushes count, including quiet classification. This is deliberately a costly
correctness adapter, not efficient generic production capture extraction.

128 combined public transitions/runtime pushes,5000 all returned/membership
entries,128 source pushes/5000 source entries,15sec whole producer. Instrument
legal_actions and push/pop, assert full root restoration, preserve source
hashes and failures. No root search, puzzle solution, deeper reference retry,
exposed-label fitting or production source edits. Output cannot be rerun.
