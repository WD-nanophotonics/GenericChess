# Task005: Native work can precede a zero accepted-frontier counter

18 predeclared direct-frontier controls pass on pinned b4108a68 source.
The supported installed extension SHA256 is
2f97cfb8816bc963163207095bf40ac990169284cd0cfb2e7b545f0a6bf07bf1.
No binary rebuild or product change. Actual extension entry/normal-return
spies observe semantic_transient_legal_actions; they do not infer execution
from requested backend or Runtime cache calls.

|Checkpoint cancellation|C generation returns|Accepted native_legality_calls|Provider metrics actions|
|---|---|---|---|
|1:Runtime entry|0|0|absent|
|2:provider entry|0|0|absent|
|3:after state pack|0|0|absent|
|4:after C generation|1|0|absent|
|5:after provider decoding|1|0|absent|
|6:after provider return|1|0|35|
|7:after Runtime pair validation|1|0|35|
|No cancellation|1|1|35|

Both strict modes reproduce each row. All cancellations preserve exact root
semantics/history, leave no partial frontier cache, retain the provider and
record zero fallback/operational failure. An ordinary query afterward returns
the same35legal actions as Core; recovery counts are separate from the abort.

Two declared post-C decode faults also observe C return1/accepted0. Non-strict
fault handling falls back to Core and disables the provider: final enabled=0
despite earlier actual Native execution. Strict handling propagates the fault
and leaves the provider active. These injected transport/decoder failures are
not evidence of a broken installed kernel. Root semantics remain unchanged.

## Attribution decision

native_legality_calls is a count of accepted provider frontiers after complete
provider return and pair validation. It is not an exception-inclusive count of
Native C invocations. A zero value on an interrupted/failed call cannot prove
that Native did no work; final enabled state also cannot describe the whole
call's route history. last_call_metrics publication is a further boundary:
metrics can exist despite zero accepted Runtime frontiers, or be absent after
a completed C generation that aborts before publication.

Retain existing product API and completed-run evidence. In research diagnostics
that compare interrupted work, label accepted frontiers explicitly and capture
C entries/returns, aborts and fallback separately where that distinction changes
the decision. Ordinary completed Task001 D2 controls with no fallback/abort are
not invalidated by this result. No speed or cost fraction is inferred from call
counts; opaque internal C trials are not unique game states.

Read-only AST comparison shows the two counter-relevant methods match the
current primary source exactly. This extends the source interpretation, not the
executed runtime source pin: these tests ran the independent b4108a68 checkout.
Core-neutral callback counters alone cannot authenticate an arbitrary callback
as Native; actual callable/provider/binary/fallback evidence remains necessary.

Declaration, native_abort_audit.py and native_abort_counts.json preserve fixed
checkpoints, recovery/failure routes, exact source/binary hashes and results.
The source note records the pre-run hypothesis separately. Dot review was
requested in a fresh root; no reply/adoption is assumed here. The direct-count
batch began after the renewed primary five-minute timing slot ended and its
process has exited. No wall measurement, extra worker or admission gate.

Dot reply was fully read and adopted: first check consumers. Static search of
product and scripts finds initialization, stat synchronization, PlayerDecision
forwarding/declarations and the thin bridge reporting tuple; no counter read
controls budget subtraction, backend choice or retry. Search budget uses its
own node/cancel/time fields. This scoped source audit supports stopping at
documentation and research diagnostics, with no product API change. Dot did
not independently run the18 controls. Raw reply stays ignored.
