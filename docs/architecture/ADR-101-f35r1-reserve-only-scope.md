# ADR-101: F35 R1 Reserve-Only Scope Cleanup

Status: accepted and retained in F35 R1

## Decision

F35 R1 keeps only the Q34C first-iteration quiescence reserve authorized by
F34. Relative to the F34 production search implementation, the final
production difference is limited to the context-local
`first_main_iteration_complete` state, `_ordinary_qdepth_limit()`, the
run-root initialization/flip, and the ordinary qdepth cutoff. The original
F34 `_quiescence_runtime()` legal-generation order is restored exactly; the
lazy non-check generation optimization is not retained. Explicit qdepth-zero
callers retain their historical static-evaluation behavior, while the
production qdepth-4 run-root reserve still enters qsearch and gives ordinary
non-check nodes effective depth zero until the first successful iteration.

In-check qsearch remains before the ordinary cutoff and searches every legal
evasion without stand-pat. Configured qdepth 4 and hard qdepth 8 remain
unchanged. No evaluator, Native backend, rules, session, runtime, CLI, or
AlphaSho behavior was changed.

## Evidence

F35 R1 source-scope proof passed:
`FIRST_ITERATION_RESERVE_ONLY_PRODUCTION_SCOPE=true` and
`LAZY_NONCHECK_LEGAL_GENERATION_RETAINED=false`. The 20/20 F34 Q34C fixed-node
reproduction, reserve witnesses, direct/internal qdepth isolation, explicit
qdepth-zero compatibility, in-check parity, cancellation, and full tactical
safety corpus all passed.

The unambiguous three-repeat matrix records, at 0.50 seconds, 30 shadow
fallback events versus 24 candidate events, three roots with improved fallback
summary, three depth-improved roots, and no depth regressions. At 2.00 seconds
there were zero fallback events in both variants; the median across comparable
per-root first-completed-iteration medians improved from 0.781s to 0.609s
(22.02%), satisfying the unchanged F34 accessibility gate. Raw per-repetition
rows and per-root medians are retained in the R1 fixtures.

The earlier stacked F35 commit remains byte-identical provisional evidence and
is referenced by the R1 manifest; it is not the retained production scope.
The next bounded boundary is
`F36_POST_QUIESCENCE_RESERVE_SEARCH_CAPACITY_REBASELINE`.

