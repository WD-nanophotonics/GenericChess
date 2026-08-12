# ADR-022: Semantic search runtime cost attribution and gated checkpoint optimization

Status: ACCEPTED for F4

## Context

F3 correctness is frozen at `47bad121fb07fef421583aa7198bf2887d985994` and its
history-aware TT model is not an optimization target.  F4 measures the
Semantic Standard Shogi search as a bounded deterministic workload using both
an opt-in audit recorder and `cProfile`.

The representative Profile A search is only a few hundred nodes but spends
seconds in semantic legality/check work.  The deep profile shows that
`SemanticEngine.is_square_attacked`, S3 legal trials, terminal legal-action
checks, and the checkpoint callback dominate cumulative/self time.  TT key and
probe/store work is negligible by comparison.  Profile B adds qsearch and
preserves the same broad conclusion.

## Decision

Authorize exactly one local optimization: for non-interactive fixed-node
searches, `_Context.checkpoint()` performs the already-required max-node check
directly instead of dispatching through `Budget.check()` and its non-interactive
polling branch on every semantic callback.  Interactive cancellation and
deadline searches retain the original `Budget.check(..., force=True)` path.

This does not change legal action generation, action order, transition,
terminal precedence, evaluation, search windows, TT semantics, history
eligibility, or qsearch policy.  Core remains unaware of AI audit metrics.

## Evidence gate

The candidate passed all seven gates: it is dominant across four semantic
prefixes, material in both profiles, explained by cProfile call counts and
self time, local to one search method, semantics-preserving by exact corpus
parity, testable with fixed repetitions, and useful by the required >=20%
target micro/whole-search evidence.

## Measurements and limits

The required evidence lives under `artifacts/f4_runtime_cost/`.  Recorder
timing is opt-in; default search still uses `NullAuditRecorder`.  Inclusive
timer fields are not added together as if they were exclusive.  cProfile
cumulative values are explicitly nested.  Profile B cProfile hit the 60 s
controller safety abort, while the repeated non-profiler Profile B corpus
completed for all cases.

The next optimization target is semantic attack/check and S3/S4 legality
work, but that is deferred because it requires a separate correctness and
performance phase rather than a second F4 optimization.
