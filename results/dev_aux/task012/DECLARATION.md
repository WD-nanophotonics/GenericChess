# Task012: search-level executed Native versus accepted work

Baseline b4108a68a7ee06327be39cb3a222939644085a52, installed supported binary
SHA2f97cfb8816bc963163207095bf40ac990169284cd0cfb2e7b545f0a6bf07bf1.
New question: can a real interrupted AlphaBeta caller join actual C entry/return,
provider attempts and formal-push disposition to completed/aborted phases?
Task005 tested only direct frontier calls; Task002's selected Python method
ledger did not observe actual C executions. No old batch is rerun.

Frozen root: existing Chess-middle CASES[0], existing weighted evaluator, Native
legality requested, no disk cache, D2/32768nodes/10sec/q4/hard8. Set a cancellation
token exactly after the first C generation return either at root phase0 or at
iteration2 q phase; do not add budget polls. Four calls per trigger, opposite
plain/instrumented orders. Transparent C/provider/push/phase observers in both
arms; original physical timers only in instrumented arm. Eight calls total,
expected under20sec, outer120sec guard between calls. No timing attribution.

Record both reached/unreached triggers, Centry/return, provider accepted deltas
and failures, phase/current push ID, successful/failed pushes and copied actual
occurrence multiset plus root semantics. Expect all Ccalls attributed exactly
once to provider attempts; accepted sum equals final stats; failed attempt work
cannot disappear from diagnostic records. Exact nontime decisions/counters and
entry traces must match arms. Root cancellation may invoke uncancelled fallback:
report it as additional executed work, not recursive search completion.
Stop/failure records stay immutable; mismatched probes restrict attribution.
Finite diagnostic only; no production counters/defaults, Native kernel rebuild,
timing gain, WDL or universal generated-domain acceptance.
