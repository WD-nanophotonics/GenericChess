# H50B2C compact semantic search state and root parallelism

## Result

The public immutable semantic position API is unchanged.  Search-edge state
copies now copy the complete live board, hands, auxiliary state, and scalar
metadata, but only the append-only history prefix below `history_len`; the
reserved unused history tail is not copied.  This is a safe intermediate
compact-state optimization and preserves exact repetition and terminal rules.

The old full-state search remains the behavioral oracle during development.
The semantic search regression suite passed after the change, including node
budgets, cancellation, terminal scoring, repetition, root preservation, and
fixed-depth PV checks.

## Measured result

On representative 18-ply positions at depth three, the live-history copy path
preserved score/action/PV parity with the accepted iterative reference.  The
single-thread improvement from the earlier 4-ply control was approximately
9.9% for Western and 8.0% for declaration-free Shogi.  Checked transition
latency in the same run was 8.78 us and 13.31 us respectively.

This is below the 25% threshold for a more invasive mutable delta rewrite.
The full `GCSemanticUndo` remains 53,920 bytes for compatibility APIs, but the
search path does not allocate one full undo frame per edge.  A future compact
delta can target changed squares, hands, aux values, and history length if
profiling shows that remaining board/aux copies are material.

## One-position root split

`generic_chess.native.semantic.root_parallel_search` is an experimental
single-position root split.  It enumerates root actions deterministically,
gives each worker an isolated child position, runs the accepted GIL-free
iterative search, and merges by score then packed-action order.  There is no
shared TT or mutable shared state.

At an 18-ply Western position, depth three latency was 130.3 ms, 71.7 ms,
38.9 ms, 23.6 ms, and 19.7 ms for 1, 2, 4, 8, and 16 workers.  CPU
utilization was approximately 1.0, 2.2, 3.2, 7.3, and 12.7 cores.  At the
corresponding Shogi position it was 168.6 ms, 90.4 ms, 48.7 ms, 27.2 ms, and
24.0 ms, using approximately 1.0, 2.1, 4.2, 6.9, and 9.8 cores.  Every root
split result matched the accepted iterative score, packed action, and full PV;
RSS rose with worker count but remained single-digit MB at 16 workers.

## Decision

Retain the live-history copy optimization and the experimental root-split API.
Do not force a larger mutable-delta rewrite after the sub-25% single-thread
gain.  The next likely high-value search optimization is a semantic TT, with
root split and state-copy profiling retained as comparison baselines.  The
Heavy workflow now runs at normal process priority while preserving one Heavy
job, one Worker, and one repository writer.
