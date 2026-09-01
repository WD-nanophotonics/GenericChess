# ADR-100: First-Iteration Quiescence Reserve

Status: accepted and retained in F35

## Decision

During the first completed iterative-deepening iteration, ordinary non-check
quiescence performs stand-pat evaluation but does not enter optional noisy
continuations. After a successful main iteration, ordinary quiescence resumes
the configured production qdepth of 4; the hard qdepth remains 8. In-check
quiescence is unchanged and always searches all legal evasions.

The implementation is limited to
`generic_chess/ai/alphabeta/search.py`. A context-local
`first_main_iteration_complete` state distinguishes a run-root reserve from
direct/internal qsearch contexts. The negamax leaf still enters qsearch while
the reserve is active for the production qdepth-4 path, so terminals,
declarations, in-check handling, stand-pat, alpha handling, cancellation, and
node accounting keep their existing order and semantics. Explicit callers
that set qdepth to zero retain the historical static-evaluation contract. The
effective ordinary qdepth is selected by a private helper only after those
gates; no public toggle or game switch was added.

## Evidence

F35 retained the candidate with 20/20 exact F34 Q34C fixed-node reproductions.
The ordinary first-iteration qdepth-zero witness, post-iteration qdepth-four
witness, aborted-iteration isolation, in-check evasion parity, cancellation
isolation, push/pop balance, and tactical safety gates all passed. The
three-repeat wall matrix passed the accessibility gate: at 0.50 seconds it
removed two fallbacks and improved depth on two roots with no regressions; at
2.00 seconds the median first-completed-iteration gain was 29.72% with no new
fallbacks. The descriptive AlphaSho comparison was external-only and was not
rerun or used for selection.

No qdepth configuration, evaluator, native backend, ruleset, session, runtime,
or CLI behavior was changed. The next bounded boundary is
`F36_POST_QUIESCENCE_RESERVE_SEARCH_CAPACITY_REBASELINE`.
