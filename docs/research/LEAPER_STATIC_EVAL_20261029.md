# Pure-Leaper exact static-evaluation aggregation

Status: research-only, all product defaults unchanged. Measured savings are
positive on these development histories, but the ORIGINAL fixed acceptance gates
remain INCONCLUSIVE because of unresolved tiny-cell CPU timing. No gate was
relaxed and no expired slot was replaced.

## Results that determine the decision

| Frozen assessment | Work and result | Decision |
|---|---|---|
| Full cProfile Q-count/inventory attribution |9/18 planned Root-entry calls; active30000-node baseline~7.6s, profiler cancelled at30s with different work; zero-Q immediate wins also occurred |NO_GO/UNKNOWN;9 remaining NOT_RUN |
| Exact per-call static memo shadow |17414 calls,4692 repeated-position hits,26.9438%; every hit also recomputed raw; same work,~3.65% overhead |FAIL frozen50% reuse gate;48 cost calls NOT_RUN;8192 capacity not retuned |
| Integer-mask static aggregation shadow |17414/17414 raw values equal, same work,~4.14% overhead |Conditional cost stage admitted |
| Root-entry cost, ALL12 histories, OFF/ON/ON/OFF |All12 groups preserve actions/scores/PVs/full untimed stats; wall ratio0.9193949831, CPU0.9192009875;6 family CPU aggregates lower |Original gate INCONCLUSIVE:4 groups have zero SUM of their two OFF CPU samples;8 individual OFF samples zero |
| Cold Player lifecycle, same ALL12/ABBA |48 actual Player objects/calls; all decisions/work/Core undo/PV/Native checks match; wall ratio0.9321362285, CPU0.9326912308;6 family CPU aggregates lower |Original gate INCONCLUSIVE:one group has zero SUM of its two OFF CPU samples;3 individual OFF samples zero |

The lifecycle experiment is a separately frozen measurement of constructor,
rule-derived evaluation profile, Native provider, mask setup and choose_action.
It does not replace or repair the earlier51 Root-entry records. Existing compiled
RuleSets/sessions and an already loaded process/binary are outside that boundary.
The existing Native binary is pinned in the archived plan. There were no new
builds, games, training, workers, solver or product-source changes.

All cost searches use D8 as a ceiling,30000 nodes, Q4/hard8, real first-iteration
Q0, fresh per-call TT, existing Native legality/availability/check, a20s caller
cap and fixed batches. Many returns retain an earlier complete iteration after
node_limit; this is matching bounded work, not completed-D8 truth. The earlier
Q attribution alone had a30s cap. These are actual search calls:zero Player
objects in the direct Root-entry harness did NOT mean zero computation.

## Exact transformation and admission

`PureLeaperMaskEvaluator` reuses EXISTING compiled empty_mobility destinations.
Those tables, offsets, Native execution, Core undo and incremental hashes are
baseline capabilities, not new inventions. The research change is the static
consumer: integer OR/bit_count instead of repeated Square-set unions, one board
pass for ownership/material/occupancy/first anchors, and omission of a promotion
bonus proven zero in this admitted subset. All prices and weights remain the
current default rule-derived profile. No action, pruning, Q policy or TT bound
is cached or changed.

Admission requires the existing strict plain-Leaper IR footprint check PLUS
all metadata movement atoms being LeapAtom, no promotion-bonus zones, square
boards of at most256 cells and at most65536 mask-table entries. The footprint
check alone is NOT a proof of legal moves, valuation completeness or a new Core
kernel. Core still supplies legality, terminal/history/clock and runtime rollback.
Unsupported scope is not silently redefined as the complete generated domain.
This remains a research wrapper, not an enabled product path.

For the reference evaluator, Leap attacks are the union of precompiled target
sets, including pinned pieces and friendly-occupied targets. Integer OR is the
same finite union; bit_count gives its cardinality. Escape uses the SAME existing
short-step table, removes occupied/opponent-attacked squares, and retains the
first anchor in board order. Missing anchors and multiple anchors preserve the
reference behavior. Hands, side perspective and raw score/clamping boundaries
are unchanged. Broader arbitrary-semantic valuation correctness is not claimed.

## Verification and remaining uncertainty

Seven primary evaluator tests compare1440 deterministic occupancy/hand/side/
weight cases over six families, plus source Core children and negative ray/
fingerprint controls. Another232 cases cover3x3/7x7 asymmetric owner frames,
duplicate targets, off-board long leaps and mixed short/long anchor steps.
These synthetic static positions are NOT legal-game samples or strength labels.
The additional fixture first failed because old setup options became illegal
after movement was changed; it was replaced with a fresh validated setup while
keeping the equality assertion. No production output was fitted as an expectation.

The memo was independently tested against forced hash collisions, mutable-view
lifetime, bounded eviction, raw-vs-history distinction and deliberately impure
shadow behavior. Its negative gate remains closed; it is not the mask evaluator.

An8.1% Root-entry and6.8% cold-lifecycle aggregate reduction is useful bounded
cost evidence. It is not a passed fixed gate, statistical population guarantee,
new-family strength/Elo result or reason to enable defaults. Extreme short calls
need a prospectively suitable precision protocol; they are not retrospectively
replaced. Microsoft documents process cycles as CPU cycles across process threads
and warns against converting thread cycle counts to elapsed time:
[process API](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-queryprocesscycletime),
[thread caveat](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-querythreadcycletime).
No cycle-counter experiment or retrospective conversion was run.

[Manifest](data/leaper_static_eval_20261029/manifest.json) binds150 literal members,
including all frozen plans, failed attribution, raw/enriched returns and exact
source hashes. All51 mask Root-entry and48 lifecycle slots are consumed and closed.
The same mask optimization run retained its17:01:18UTC origin/65min cap; completed
historical projects were not accumulated into an approval balance.

## Current priority

The newly received [independent605cacb8 review](../reviews/chatgpt_patrol/2026-10-29_020006_JST_e9d4f253.md)
was privately preserved, fully read and safely fast-forwarded as one doc-only
change. Adopt its priority: fresh-motion-family fixed-service decision quality,
not more exposed extension/LMR/PVS tuning, one-hop label mining or timing-cell
refill. The mask result stays a bounded backup. A precision probe is deferred,
not a publication/work gate. [Next protocol](LEAPER_THREAT_ORDER_PROTOCOL_20261029.md).

2026-10-29 wording correction after public AUX670bae91 pointed out the unit:
retained raw fields were recomputed without new queries. The fixed resolution
gate checks the two-OFF SUM per group,not every individual sample. Root starts
after three census records;cold starts at its own slot0. Ratios/gates/defaults
are unchanged;this is not a timing rerun or independent hardware reproduction.
