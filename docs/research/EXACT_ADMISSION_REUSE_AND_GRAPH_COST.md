# Exact compilation reuse and rule-price graph work —2026-10-15

Science remains OPEN. These are admission-cost changes, not better prices or
stronger search. The public baseline is
`75493026588accefd63917427a365f0c818a1cef`; PUBLIC remains necessary for Dot/Chat.
PRIMARY owns this backend/compiler work; the separate DEV_AUX solver, verifier,
cursor and learning checkout was neither edited nor duplicated.

## Decision and changed premise

The preceding search-only gains did not describe first-call cost. A cold-Python
pilot attributed most sampled12/16 first-call time to rule admission. A failed
source-partition rewrite had mixed regressions and remains rejected. This segment
traced actual constructor callers before changing code, then tested two exact
cost reductions. No global cache, skipped validation, price fit or API redesign.

On paid4331, the actual compiler/research caller built60556incoming rows four
separate times: temporary Native-capability probe, final compiled ruleset,
executable adapter and the frozen research metadata adapter. The latter two used
the exact same IR/support objects. The probe shared patterns/geometry/support,
but its Native-capability flag differed. Instrumented construction times were
.0939/.1101/.1294/.0844s; these are one traced observation, not unbiased shares.

The implementation:

- Native capability lowering receives the same IR/support and their pass/no-
  progress properties without constructing temporary Core attack indices.
  The payload builder only reads those authorities; its checks/fail-closed
  exception path remain. Full semantic-start validation remains mandatory.
- The executable adapter exposes the SAME compiled product and derived fields.
  Its factory accepts no replacement IR/support. Ordinary construction and
  `dataclasses.replace` still rebuild derived indices. No cross-rule lookup,
  fingerprint-based sharing or unbounded cache is introduced.
- Rule-price graph analysis uses exact bitset distance layers within the
  EXISTING exact-analysis bound1024vertices. Larger graphs keep their original
 64sampled sources/list BFS and SCC convention. Extra bit payload is bounded by
 128KiB; Python integer/list overhead is additional. No price formula, density,
  weights, rounding, clipping, evaluator version or cached value changes.

The old frozen research adapter still reconstructs its own indices and is charged
in caller timing. It was not silently migrated to make the reported gain larger.
Native C, q/defaults, all result fields, import paths and Core rule semantics are
unchanged in this delivery.

## Exactness and qualification

The adapter transfers all compiled fields, including every derived map/None
fallback, with the original IR/support/borrowed pattern-row identities. Replacing
IR with empty patterns demonstrably rebuilds, rather than retaining stale data.
Both endpoint-index and full-reference escapes retain their semantics. The path
cap65536 and endpoint cap262144 are unchanged. Auxiliary state, triggers, drops,
promotion and complete played history remain part of execution.

For the graph algorithm, frontier at distance d contains exactly the newly
reached vertices at d; OR of their outgoing masks followed by exclusion of seen
vertices produces the next shortest-distance layer. Counting each layer preserves
reachable pairs, integer distance sum and maximum distance. Completion stopping
is safe only after every other vertex has been discovered. Graph construction
already deduplicates adjacency lists, so their bit masks preserve destinations.
Directed edges, self loops and disconnected components are retained; Tarjan SCC
traversal and sampling above the exact bound are untouched.

Seven directed/disconnected random-graph sizes and five movement/rectangular
controls compare with the retained queue reference, including exact1024 and
sampled1056vertices. Tests also cover compiled field ownership, replacement,
physical play/history and initial-validation propagation.

Final normal product regression:2687passed in271.12s. A separate source-only
export rebuilt frozenV1/V2 and passed81focused tests plus35full roots,4497legal
actions and returned-PV complete state/history replay. It uses the existing
Windows/Python3.12/Zig libraries; it is not a clean-machine installer or timing
replication. Source-only replay and actual normal installed product tests are
separate evidence. Archive public-copy replay is recorded below when completed.

## Compiler-only pilot and actual consumer transfer

A declared16process pilot times48product compiles and48unchanged adapter builds
on four exposed paid rules. Every IR, Native payload/report, full initial state,
legal action set and six derived-map hash agrees. Six matched product-compile
ratios per rule have medians.775/.519/.544/.455 for4/8/12/16. This compiler-only
denominator differs from the full caller below.

The transfer uses20other already-paid full rules, five per board size,80fresh
Python processes and320queries. There is no new generation, training, human
holdout access or success-based replacement. FixedD3/1024nodes/q4/hard8, TT0,
ordering cache off; four queries reuse each engine. All160paired query non-time
fields agree, with no clock-censored pair. Every returned PV is checked against
Core board/hands/aux/actor plus every identity/event history entry; parents stay
unchanged.

Family-geometric cost ratios, averaging the two reversed orders per family:

|Board|Python compile + unchanged adapter|API-ready first query|API-ready four-query prefix|
|---|---:|---:|---:|
|4|.836|.943|.972|
|8|.757|.893|.945|
|12|.668|.814|.882|
|16|.603|.753|.828|

Conditional five-family bootstrap intervals and all phase/paired rows are in
`data/admission_reuse_20261015.json` and the archive. Fresh Python processes do
not mean a cold OS/filesystem cache. Python imports/deserialization are separate;
provider-module loading is excluded and was NOT separately timed. API-ready
pipeline includes compile, unchanged adapter, initial session, price, Native
compile, engine and searched prefix. It is not whole application startup or a
causal estimator for every unchanged phase. Concurrent load is a timing limit,
not a reason to rerun selectively or request another project to stop.

## Why another compiler refactor was deferred

Two further complete paid rules4324/4334 were profiled with unprofiled controls
and reversed orders. Total profiler overhead was2.67/2.34. Two geometry catalogs
are indeed built, but their profiled cumulative costs were only.00768/.02764s.
Cumulative fields overlap and cannot be added into wall-time shares. Another
catalog refactor was not adopted: actual unprofiled price cost.0385/.1698s and
all-source BFS were more material than another broad compiler cleanup.

## Price-analysis cost, including adverse controls

Three graph variants were declared: original queue, early discovery-complete
queue stopping and bitset layers. Across seven shapes/eight motifs/reversed
orders/two repeats,672graph calls were timed. Only final-repeat metrics were saved,
so the exact comparison count is224candidate/reference comparisons, NOT448.
All saved metrics agree. Sparse forward-only32bitset analysis is1.57x the original;
early queue stopping also regresses on sparse controls. These adverse cases are
retained. The broad graph prototype above1024was measured but is not the chosen
production route because its extra bitset storage scales quadratically.

The bounded candidate then runs80processes/160full-profile timings on the same
20paid transfer rules. Both repeated profiles and all separately recorded complete
movement-capability fields agree exactly, including raw/normalized/rounded/
clipped board/hand values and promotion gains. Family ratios:

|Board|Full profile cost|Conditional family95percent interval|
|---|---:|---:|
|4|.957|[.927,.989]|
|8|.856|[.826,.882]|
|12|.734|[.713,.755]|
|16|.630|[.604,.656]|

Two small-board pairs regress, worst1.0448x; all are retained. This supports the
small globally bounded implementation on this development distribution, not
universal speed dominance. No board-specific patch or price-quality inference.
These remain geometry-based cheap static profiles; faster construction does not
make them complete semantic/state-interaction valuations.

## A real finite first-call budget is a different experiment

A separate320process four-cell experiment uses baseline(A), compiler-only(B),
graph-only(C) and both(D), with two reversed orders and.5/1s API-ready deadlines.
All admission phases count before remaining search time is assigned. Atomic
Python compilation itself is not interruptible: expiry after a phase is explicit
`ADMISSION_EXPIRED`, never success/draw or a fabricated search result. The
underlying product SearchLimits/default semantics are not modified.

At16/.5s, searches execute A0/B8/C0/D8 of10calls each. At16/1s the counts are
A9/B10/C10/D10. D obtains eight extra invocations at.5s and one at1s relative to A.
For all69pairs where A and D both search, retained depth and action stay the same;
extra allocated seconds do NOT establish stronger search. At smaller boards all
invocations execute, also with unchanged retained depths/actions. Result qdepth
can be0despite requestedq4; actual policy and stopping histograms are retained.

Atomic phase overrun reaches.1415s in D/.5s versus.1377s in A/.5s: these changes do
not guarantee a hard deadline. Above zero means overshoot, not a timer failure
silently discarded. Baseline16/1s also has one Native-compile expiry. The full
four-cell allocation interaction `(D-C)-(B-A)` and every phase/expiry remain in
the data. Raw caller ratios are not treated as matched-search cost when some
cells never perform search. Provider-module loading remains excluded/unmeasured.

## The next control: requested q versus actual retained policy

The frozen20family study closes in1466.128s with70of80planned common roots and
560of640queries; all80missing slots are actual terminal-tail roots, not replaced.
There are280matched policy pairs;172choose the same action. The q4request retains
shallower depth in274pairs, the same in6, deeper in0. These are capacity results,
not proof that disabled q is better.44enabled-q calls stop at the hard check cap.
All560returned PVs retain full state/history agreement and unchanged parents.

An interpretation error was caught from the ACTUAL result fields: passing
ordinaryq0/hard8 disables q entirely at the existing Python entry, returning
(ordinary0,hard0). The enabledq4request can reserve D1with(ordinary0,hard8), then
attempt(4,8). This experiment therefore compares DISABLED q with ENABLED q;
it does not isolate ordinary depth while holding check extensions fixed. Original
plans, limits and rows are preserved; no new product bug/default change or silent
repair rerun is claimed. Per-board/budget returned-policy/stopping histograms
remain in the data rather than treating requestedq4 as completedq4.

Unique selected-child diagnostics:57complete one-ply no-win scans,8actual terminal
children,48UNKNOWN and1opponent winning-reply witness. Reused actions/roots are not
independent new diagnostics. None of the original matched pairs establishes loss
avoidance against a complete alternative: UNKNOWN remains UNKNOWN. No-win after
one ply is not optimal WDL or long-term safety.

The actual witness is seed4323/ply12: at1s the q4request keeps D1/(0,8), chooses a
capture+promotion and permits a literal quiet checkmate reply. A separate actual
GameSession execution and Native checked replay agree on that checkmate, both
boards/hands/aux/actors and complete histories. This is NOT a terminal-authority
mismatch or a falsely completed D2. At4s enabledq retainsD2/(4,8) with another move;
disabledq keeps another checking promotion at both budgets.

A NEW exposed two-branch reply-frontier diagnostic qualifies those two alternative
choices: each has exactly one legal opponent reply, complete Core/Native legal
sets, child terminals and all histories agree, neither reply wins immediately.
This demonstrates a local avoidable immediate loss in the1sreserve choice, not
that either alternative wins under optimal play or that q should globally change.
Old1sUNKNOWN labels/caps are not overwritten by this separate followup.

Why did the old one-reply scan censor even one legal reply? Its inner checkpoint
called stopped(), reading THREE JSON stop files each time. The bounded one-case
control observes7240callbacks/21720file reads and UNKNOWN at1.0006s versus complete
10600deadline-only callbacks/6outer stop reads in.0120s. These are observer costs,
not an intrinsic Core search-hardness estimate. There is no product stop-policy
change, resampling or rerun of48UNKNOWNs. Future bounded diagnostics should retain
cooperative outer stop checks without file I/O on every primitive guard.

## Four selected move differences under one fixed continuation

After the original timed batch closed, a declared eight-game diagnostic forces
only the stored first choice, then uses the SAME fixed4096node/disabled-q policy
on BOTH actors. Four exposed parents from three families, including two dependent
4312roots; no new generation/training/solver, no claim of independent validation.
All8games close in59.304s with277physically checked Native/Core edges.64additional
plies remain an actual cap; a capped ongoing state is UNKNOWN, never draw.

|Common parent|Disabled-q first choice|Enabled-q first choice|
|---|---|---|
|4304/0|actual LOSS|actual LOSS|
|4312/0|actual LOSS|actual LOSS|
|4312/4|UNKNOWN at cap|actual WIN|
|4313/0|actual LOSS|UNKNOWN at cap|

This falsifies an easy inference from changed/deeper moves to useful outcomes:
the first two branches both lose under this continuation. The last two retain
censoring and conditional differences; they do not establish optimal WDL or a
global q winner. Raw results, move histories, before/after full-state hashes and
all retained search receipts are archived; a proving/search-disabled consumer
independently replays them below.

## Current implication and delivery

Retain the qualified exact admission changes. More usable first-call time often
failed to change the retained q policy; a fixed larger q does not guarantee a
better decision, while globally disabling it is also unsupported by these
conditional continuation results. The next specific question is completion-aware
allocation of reserve and enabled-q work, using the confirmed reserve-loss root
and contrasting conditional cases. Do not reopen the old unchanged q1/q4 curve,
increase a frozen hard cap or duplicate AUX's Session solver/bank/learning lane.

Some admission timing runs overlapped PRIMARY regression/source checks as well
as ordinary machine concurrency. Reversed orders and conditional family intervals
do not make exact hardware-load matching or a universal causal claim. The q-policy
batch and subsequent continuations ran sequentially, preserving their declared
resource scopes. None of the new measurements warrants an Elo/price-quality claim.

The public archive contains source variants, complete rules/records, plans,
missing slots, raw technical result rows and resolved operational failures.
Private exact Slack/account originals stay ignored; publication copies exclude
personal information/passwords/credentials. PUBLIC source links and the companion
COLLABORATION_LOG provide review without a Dot acknowledgment/approval gate.

Separate proving/search-disabled continuation consumer replays all277edges and
full final records/results in1.502s; source and exact receipts are archived. This
is a separate consumer using the same Core/compiler, not an all-domain proof.

Actual PUBLIC-copy replay on the sealed1243member ZIP passed81focused tests,
35roots4497actions/full histories. Its exact archive hash and full receipt are
`../archive/admission_reuse_20261015/publication-replay.json`. The next scheduling
source examination has begun; it is recorded in the data as a proposal, not an
implemented/tested policy. No producer is left running.
