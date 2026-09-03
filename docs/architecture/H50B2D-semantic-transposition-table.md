# H50B2D semantic transposition table

## Decision

The Native semantic iterative search now accepts an experimental
`tt_megabytes` binding. A nonzero binding allocates an independent four-way
semantic table for that search call; the table is never shared with the legacy
`GCPosition` TT, other RuleSets, or other evaluator configurations.

Each key contains the current canonical semantic position digest, an
incrementally maintained four-word history/event context digest, and the
history length. The context is seeded once from the packed root history and
updated in O(1) on each semantic transition with the appended position digest,
actor, and gave-check metadata. This prevents repetition and
continuous-check paths from sharing entries merely because their board state
matches.

Entries retain depth, score, bound, best action, PV prefix, generation, and
replacement metadata. Mate-like scores are normalized on store/probe using
the local search ply plus the explicit root offset. PV nodes use deterministic
full-window handling and, when needed, a TT-disabled PV replay so TT move
ordering cannot change the exact baseline PV.

Declaration-bearing RuleSets remain fail-closed at the semantic iterative
entrypoint.

## Verification

Focused semantic tests cover no-TT parity, TT result/PV parity, history-
sensitive repetition behavior, mate-distance behavior through root-parallel
search, and root immutability. The normal regression selection passed 102
tests after the B2D changes.

The final benchmark used depth 4 and two deterministic positions per case,
each built after 24 legal plies, for Western and declaration-free Shogi. All
0/64/256/512 MB comparisons preserved exact score, best action, and PV
(`parity_all=true`). The table entry is 608 bytes; actual table allocations
were 39,845,888 bytes (64 MB request), 159,383,552 bytes (256 MB request), and
318,767,104 bytes (512 MB request).

Representative node reductions versus the no-TT baseline:

| case / position | 64 MB | 256 MB | 512 MB |
|---|---:|---:|---:|
| Western / 0 | -3.5% | 12.5% | 18.1% |
| Western / 1 | 10.5% | 37.8% | 39.4% |
| Shogi / 0 | -15.8% | -1.8% | -0.2% |
| Shogi / 1 | 31.2% | 49.6% | 50.0% |

The same conservative history identity means benefits are position-dependent;
some positions pay TT/PV-replay overhead. The strongest measured wall-clock
improvements were Western position 1 at 512 MB (9.087 s to 5.731 s) and Shogi
position 1 at 512 MB (9.206 s to 4.895 s). TT hits were dominated by previous
iterative-depth reuse; current-iteration hits were zero in this conservative
history-key benchmark, so within-tree transposition sharing remains limited.

Raw benchmark evidence is intentionally outside Git:

- path: `C:\Users\wdai\AppData\Local\Temp\f50b2d-semantic-tt-v7.json`
- SHA-256: `91aa927d11e1999738592cec0eca93abbc414d95d6ef3d65a5f75a0637e91794`

The next optimization boundary is a short search-integration stage; the
history key should not be weakened without a correctness argument.
