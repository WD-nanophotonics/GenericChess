# Supported mixed q ordering and PVS delivery

The ordinary-only q ordering candidate now has an explicit supported constructor
option. The existing orderer runs at nonchecked q nodes; checked evasions remain
lexical. This adds no evaluator, pruning, runtime, Native ABI or UI policy.
Defaults and the old all-q option retain their prior behavior. The option is a
usable candidate with bounded positive and negative evidence, not a universal
improvement or protection against the checked hard boundary.

```python
from generic_chess.ai.alphabeta.tuning import SearchTuning

tuning = SearchTuning(
    use_ordered_qsearch=True,
    use_ordered_qsearch_in_check=False,
)
```

The appended field preserves existing positional fields. All six runtime and
stateless q ordering calls receive the already computed check status; no extra
check query is introduced. It is ignored when q ordering or general ordering is
disabled. `use_ordered_qsearch=True` alone preserves historical all-q ordering.
The player keeps immutable tuning, so no cross-policy mutable TT mechanism is
introduced. Existing q-depth TT guards, complete history and errors remain.

## Actual qualification

One public1455 D2/q4/hard8 call reproduces the prior private candidate's full
choice and work: score6449 and35518 qnodes, without a global orderer replacement.
Eight actual saved-before/new-source calls on1008/1052 reproduce default and old
all-q full choices, main/q/order work and q provenance exactly. Nine regressions
cover runtime/stateless quiet checking-drop mate, checked hard-boundary abort,
implicit semantic type change and public cancellation after completedD1 followed
by warm/cold D2 recovery. Final current-source active suite:2,328 passed, zero
failure/error/skip. Raw XML remains private; its hash and counts are archived.

Three initial new tests assumed runtime history lacked its imported initial
sentinel. The engine restored correctly; the tests were corrected to compare the
actual initial runtime snapshot. Original failed tests and the correction remain.
The first old-source launch proposal was rejected before execution by automatic
review on a claimed greater-than-one-hour estimate. The accepted eight-call
30-second guards bound that producer to240seconds; all eight completed. No
unchanged rejected launch or long-run consultation bypass occurred.

## Fresh frozen PVS by q-scope plane

Four generated hybrid8x8 rule seeds1511–1514 (full seeds2026101511–14), eight
sorted-uniform legal prefix plies, seed+15000, were fixed before queries.
AB/PVS × lexical/mixed,16/64seconds, two reverse orders, no node cap, q4/hard8.
Native semantic leaf evaluation, frozen rule-derived prices, Native legality and
readonly Native availability were shared; Core retained adjudication/history.

Seed1511 terminated before the required prefix and was retained unavailable with
no replacement. All64 cells are accounted for:48 actual calls plus16 unavailable.
Producer query wall1121.422seconds. No budgets or hard bounds were extended.

|Root|16s, all four modes/both orders|64s, all four modes/both orders|Exit distinction|
|---|---|---|---|
|1512|D2/15230|D2/15230|64s lexical AB/PVS hard8; mixed AB/PVS time limit|
|1513|Immediate win/999999999|Immediate win/999999999|Root terminal shortcut; not D0 search-depth gain|
|1514|D4/2106|D5/3081|Time limit|

All24 PVS contrasts and24 q-scope contrasts agree in the complete retained
score/action/main-PV/depth/choice/declaration/q-policy tuple. All48 retained PVs
were independently replayed through Core's complete legal history; four distinct
lines, exact reconstructed root/witnesses, zero Native-legality fallbacks and
balanced root/history restoration. Exits:28 time,4 checked-hard-limit,16 immediate
wins. The changed exit on1512 adds no completed depth or action. Thus this plane
provides no additional PVS or mixed deployment gain. It does not erase the prior
eight-root mixed gain or prove general failure; sampling, terminal roots and
ordinary concurrent load limit the conclusion.

## Fixed completed work versus unfinished attempts

Sixteen adaptive exposed-root controls fix1512 atD2 and1514 atD4, same q4/hard8,
fresh TT, four modes and reverse orders,30-second guards. All complete, all four
full tuples agree, and reversed-order non-time tree counts agree per mode.

|Root/scope|AB qnodes|PVS qnodes|PVS null windows/researches|
|---|---:|---:|---:|
|1512 lexical|20260|18239|236/1|
|1512 mixed|20319|17902|236/1|
|1514 lexical|13261|13209|1830/6|
|1514 mixed|12820|13039|1830/6|

PVS lowers q work about10–12% on1512, but slightly raises mixed q work on1514.
This is completed-work evidence without a resource-plane depth gain. Local times
and actual transition/frontier/import counters are preserved; these are not
isolated CPU speed factors or WDL results.

One actual1514 mixedD4 profile preserves the fixed full tuple and all physical
frontier work. It has68930 Core pushes versus12820 qnodes: classification and
complete child commit remain substantial. Nested push cumulative time10.224s,
terminal3.224s, component diff1.935s; these overlap and must not be added.
The small XOR/nonboard-map components each contribute only about1.5% of the
profile's17.559s total. No new token/hash cache or footprint shortcut is selected.
Profile overhead and ordinary concurrent computation are disclosed; host pstats
is private, sanitized function rows are archived.

## Actual consumer activation and its limitation

Eight same-budget16s controls omit the optional availability callback. Normal
Core availability then gives1455 D1/8279 in both lexical and mixed orders;1514
staysD4/2106 in both. Missing callback is a deliberate execution condition,
not an operational fallback failure. The prior1455 mixed D2 gain depends on the
measured caller/backend condition and must not be advertised for every consumer.

The repository already offers `use_native_semantic_availability=True` on
`AlphaBetaPlayer`; no duplicate helper or framework is needed. Four actual calls
using that flag, the mixed tuning above and no explicit callback reproduce the
research helper's1455 D2/6449/q35518 and1514 D4/2106/q12820 in both orders.
The existing public provider is bound, imports/queries equal actual pushes
(147332 or68930), zero declines and Native-legality fallback, root restored.
The option retains Core history/terminal ownership and unsupported fallback.
It is default-off; supplying a custom callback still takes precedence.

These comparisons keep the Native semantic evaluator and rule-derived weights.
They do not establish gains for a different evaluator, independent Native q4
search (unsupported), the user's frontend, or a clean source-only machine window.
The new q-scope flag alone is Python-source only; restart a consumer to load it.
Earlier Native internal-layout commits still require their documented full
rebuild. UI Test remains user-owned and unchanged.

## Decision and evidence

Deliver the small opt-in q-scope interface with explicit backend activation and
limits. Leave defaults/PVS/UI policies fixed, retain every unfavorable/unavailable
cell, and return to one substantial actual caller cost rather than enlarging
budgets or tiny hash micro-optimizations. Existing quiet-drop and shared-check
negative planes remain frozen; another root alone is no changed premise.

Evidence: [index](data/mixed_q_public_api_20261013.json),
[bounded science/source archive](../archive/mixed_q_public_api_20261013/evidence.zip).
The archive contains86 actual research search calls and source/test qualification;
Core PV replays and pytest invocations are separately identified, not inflated
into search-call counts. Prior evidence: [ordinary q ordering](ORDINARY_Q_ORDERING.md).
