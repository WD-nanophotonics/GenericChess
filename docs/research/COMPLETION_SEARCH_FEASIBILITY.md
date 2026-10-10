# Completion-aware search feasibility

This is a bounded research alternative to the installed alpha-beta search.
The product/default remains unchanged. Sources, frozen rules, all outcomes and
costs are retained separately from this decision record. Generic coverage still
requires promotion, drops, auxiliary state and relevant adjudication history;
the prototype excludes declarations/restarts and does not establish that target.

## Why test this route

Existing semantic attack/defense relations separate five exposed top children,
but a simple hanging-piece alarm misses ordinary mating drops in the complete
old cohort. Increasing ordinary q to1 at the same512node condition changes none
of15 selected actions or immediate-loss counts, and six D2 controls become D1.
Removing only root TT best-move priority increases some partial coverage but
does not consistently improve choices or completion. These observations motivate
testing how search retains resolved evidence, rather than fitting exposed labels.
FINITE_SEARCH_COMPRESSION.md owns those price/input/root-order diagnostics.

## Primary sources and transfer limits

[On some improvements to Unbounded Minimax](https://arxiv.org/html/2505.04525v1)
separates exact terminal information and completion from heuristic estimates,
and studies transposition/full-backpropagation changes. Its22game empirical
comparison uses learned evaluators and10second searches. It supplies an algorithm
premise, not evidence of a fixed-budget gain on this generated rule domain.

[Completeness of Unbounded Best-First Minimax and Descent Minimax](https://arxiv.org/html/2603.24572v1)
uses separate heuristic, resolution and completion values, with finite game-graph
assumptions. Finite completeness does not imply useful short-budget choices.
A board-only cycle quotient would discard this project's history-dependent
adjudication. Keeping full state avoids that identification; it neither proves
finite termination for every supported rule nor provides a cheap transposition
implementation. The experiment below uses no transposition table.

For the four actual pilot rules, max_ply is512 and declarations/automatic
adjudications are empty. Incrementing ply through public transitions gives a
finite unrolled history tree even if board positions repeat; genuine repetition
or MAX_PLY remains a rule terminal. This is an inference from these configured
rules, not proof about arbitrary restart interfaces, a board-only TT quotient,
this prototype's unbounded algorithm parity or short-budget performance.

[Learning to Play Two-Player Perfect-Information Games without Knowledge](https://www.jmlr.org/papers/volume27/25-2259/25-2259.pdf)
describes partial-search/tree bootstrapping and a substantial per-game learning
protocol. Its48hour training/network and2second search conditions are not small
local training or a shared unfamiliar-rule model. Partial minimax targets are
search estimates, not new terminal truth. No training follows from this review.

## Prototype contract

Nodes retain public full GameState and use actual Core legal actions/transitions.
Heuristic values are owner0-oriented. Resolved outcomes are separate: a real
current-player winning child suffices; other resolved results require all legal
children to be expanded and resolved. A partial frontier cannot certify an
all-child loss/draw. Unknown is never converted to an external-horizon draw.
Six finite backup controls cover partial loss, existential wins for either side,
all-child loss, and choosing an established draw over loss for either mover.
They check the prototype's bookkeeping, not a theorem about arbitrary rules.

This is a completion-inspired feasibility implementation, not paper algorithm
parity. It uses canonical ties, no TT, no training and no game-specific patches.
Declarations/restart interfaces are excluded. The current winner-or-draw terminal
projection would need explicit handling of NO_CONTEST before wider domain use.
Public transitions preserve full history but perform different work from the
installed incremental alpha-beta runtime. Equal count labels do not equal cost.
The two algorithms also differ in frontier selection, tie/order rules, TT use
and incremental execution. This is a route comparison, not an isolated causal
ablation of the completion field. Their common leaf fixes price attribution.

## Initial finite assay

All five exposed old parents and12 frozen2160-2163 opening0/4/8 states, Unit/v3,
give34 calls in82.326seconds. Each old-parent call materializes512 successors
and costs roughly3â€“6seconds. Both leaf arms select four of five old parents
without an immediate mating reply; one remains. The twelve newer roots include
real early resolved wins. None of this establishes gain at the old512alpha-beta
node cost, nor an independently validated evaluator or default.

Next compare actual behavior under a common wall-clock target with fresh frozen
2164-2167 rules, holding the leaf identical on both sides and swapping algorithms
between owners. Actual wall overruns, workload definitions, duplicate trajectories
and external censoring remain visible. An explicitly declared same-condition
repeat examines wall-clock scheduling sensitivity; it is exposed reproducibility,
not another independent holdout or a result-selected budget extension.
The initial timed batch overlaps the tail of a finite root-support audit and
a17.456second common-parent diagnostic. Keep that scheduling qualification;
the repeat runs after all such local experiments have ended. This removes the
observed Agent interference, not all OS background activity. Actual per-call
wall measurements include alpha-beta PV validation; whole-game wall also covers
shared legal-action checks/submission and retained records. Report search work
and caller costs separately, without treating one second as a strict latency
guarantee or identical CPU allocation.

The first16games complete519plies in549.887seconds: alpha-beta9wins, frontier3,
two real repetition draws, two still ongoing64. Four2166two-ply mates repeat
an observed short trajectory under different labels/owners; they are not four
independent demonstrations. Both2164Unit cells are ongoing; both2167Unit cells
are repetition draws. Other terminal outcomes are retained, without turning
ongoing into draw or pooling all leaf conditions into a strength estimate.

Alpha-beta261calls total269315visited nodes; frontier258calls total47470
materialized successors. Their summed measured caller times are265.715 and
252.513seconds, median1.0181 and1.0035, maximum1.0455 and1.0132seconds. These
actual costs are compatible with a shared target, not identical work/strict
latency. No exposed rescue or changed trajectory establishes an economical
default. The declared repeat completes477plies in504.297seconds with alpha-beta
9wins, frontier4, one true repetition draw, two ongoing64. Three of16cells
change action trajectories:2165v3 frontier/AB atply6,2167Unit AB/frontier atply1,
2167v3 frontier/AB atply32. Only the2167Unit event changes, from repetition draw
to black mate. Thirteen distinct action trajectories exist in each batch;
the repeat is not13new independent examples. CPU interference in the first
batch is qualified, but this cannot attribute every change to that interference:
the one-second stopping point also depends on ordinary OS/timing variability.
The fixed logical-work assays and actual cost curves answer different questions.
All996 selected children are audited:561 unique complete states,435 cache hits,
63787 public reply transitions and557.545seconds. There are25 positive path
rows; duplicates and forced exposures prevent treating that as an avoidable
error rate. The four2166 two-ply outcomes follow one root with only one legal
action and a real opposing mating reply (21 public transitions), so they do not
distinguish these algorithms.

## Cost issue worth one bounded follow-up

The prototype's public apply_action path validates an action again, whereas the
repository already owns legal_successor_handles and materialize_legal_successor.
These issue parent-identity-bound verified handles and produce full Core states,
including history, repetition and terminal status. Reusing them is an existing
interface option, not permission to skip validation or use board-only states.
A fixed512-successor research variant retains all24 choices, root-child values,
resolution and non-time work signatures on12 original2164-2167 roots, Unit/v3.
All503 root handle children equal public apply_action complete GameStates.
Summed search time on these unpaired local calls decreases33.299 to1.678seconds;
this identifies an implementation-cost opportunity, not playing improvement.

An independent inverse-bool encoding assay retains48 paired action/value/work
signatures (96 calls),503 complete one-step state pairs and3658 history-record
pairs. It covers global expire-next-turn bool slots, equality guards and set_bool,
not arbitrary effects/history equivalence. Full-state execution is still needed.

The instrumented cost controls count actual semantic-engine transitions while
preserving each uninstrumented decision/work signature. On2164 opening4 Unit,
438 alpha-beta nodes require13220 internal transitions;512 original-frontier
successors require115046;512 handle successors require2034. On2165 the analogous
counts are90 nodes/516 transitions,512/19486 and512/1588. Instrumented wall costs
are separate from ordinary timings. These counters explain why equal node labels
were misleading; they do not establish that one search policy is better.

The concrete next comparison is a declared fresh2168-2171 sixteen-game assay,
same one-second target, common leaf on both sides, swapped owners and64-ply
external censoring. Only the supported handle path changes the frontier's cost
premise. Keep all original adverse results; no result-dependent rule selection,
budget extension, product adoption or exposed fitting. This remains a comparison
of search routes, with different ordering/TT behavior, rather than a causal
completion-only ablation.

The handle-time batch completes all16cells/881plies in984.742seconds:
frontier5wins, one true repetition draw, ten ongoing64, no technical abort.
All16 action trajectories differ. On2168 Unit the frontier wins only as owner0;
v3 gives an owner1 frontier win and a repetition draw in the reverse assignment.
On2169 Unit the frontier wins both assignments; v3 gives one owner0 frontier win
and one ongoing game. Both2170 and2171 have four ongoing cells. No selected-reply
or whole-root loss attribution is claimed for this batch. These are positive but concentrated
local signals, not an Elo estimate or a paired gain relative to2164-2167.

Alpha-beta439calls use360273nodes with449.083 summed caller seconds;
frontier442calls use2277556 materialized successors with441.053seconds.
Median/max wall costs are1.0222/1.0581 and1.0086/1.0800seconds;4/8calls exceed
1.05seconds. Whole-batch costs also include legal submissions and result saving.
Root resolution is reported separately from heuristic scores:436frontier calls
remain unresolved, six have a resolved root. More work or a resolved root alone
does not prove a better useful decision. No default is adopted.

A finite interface transfer check on existing7x5/9x10 cannon rectangles at
lexical ply0/2/4 retains232 complete handle/public child pairs and all six
original/handle fixed64 choice/value/work signatures. It costs0.868seconds.
This supports the existing API reuse on those shapes, not Native compilation,
arbitrary generated mechanics or long-term value. The next useful question is
whether completion outcomes at a specific common parent change a decision beyond
cheap immediate-terminal information, with prices/time/order qualifications fixed;
conditional drop-service input remains an executable alternative. No automatic
training, longer games, all-reply audit or new framework follows.

Recovery: data/completion_search_20261010.json and handle_time_20261010.json route
the complete sources/rules/adverse outcomes to completion-search-20261010-index.json
and handle-time-20261010-index.json in ../archive/search_compression_20261009.
Initial packaging incorrectly used absolute member paths; corrected packages use
workspace-relative paths, retain failed producers and repair records, and replay
full histories from the final archive. Recovery replay is not independent science.

## Terminal-preserving completion ablation

The next controlled research variant keeps the same full-state handles, canonical
ties, Unit/v3 leaf on both sides and actual-terminal scores. ON propagates valid
completion, skips resolved subtrees and stops at an existential win. OFF keeps
ordinary partial heuristic minimax and uses structural exhaustion only to prevent
re-expanding finished terminal trees. It deliberately does not expose internal
resolved outcomes. This is a combined propagation/skip/early-stop ablation, not
isolated causality of the priority field. Six finite bookkeeping controls pass;
eight actual512-successor calls include exact ON parity with saved2165 signatures
and the newer2169 parent. No product/default or learned table changes.

All32 predeclared2172-2175 games complete in1311.959seconds/830plies. Both time
conditions use the same four rules, Unit/v3 leaves and swapped ON/OFF owners;
the second condition is an exposed resource curve, not independent validation.

|Target per call|ON wins|OFF wins|True rule draws|Ongoing64|Plies|
|---|---:|---:|---:|---:|---:|
|1second|4|7|0|5|455|
|2seconds|7|4|2|3|375|

Eight matched cells change terminal event class with time. Twelve/eleven distinct
action trajectories exist at1/2seconds; all four2175 cells share an immediate
one-ply mate in each condition. These dependent counts do not establish stable
completion utility. The28 common-parent opening/earliest-time-divergence probes
use5201 transitions. All selected children have zero opposing next-reply win
witnesses; only2175 has an immediate root win. This narrow absence is not WDL
or an explanation of subsequent outcomes. The sole ON/OFF opening difference,
2172v3 at2seconds, disappears at each common512/4096/16384-successor budget:
all six calls retain identical choices/values and unresolved roots. A timed
choice difference alone therefore does not identify semantic causality.

ON resolves6/13 roots at1/2seconds. OFF retains91/358 root-child occurrences of
an extreme backed score with no resolved outcome; occurrences are dependent,
not independent errors. Actual terminal scores can reach a partial frontier
without proving its internal result. OFF completes no structurally exhausted
root in these games. ON/OFF summed caller seconds are224.007/229.935 and
355.509/377.960, on different trajectories rather than paired speed controls.
Maximum caller costs are1.066/1.051 and2.130/2.124seconds. The earlier apparent
2.19second one-second overrun was whole-game legal-submission/save overhead;
it was corrected and supplies no cancellation-interface defect. At2175 ON
stops at the shared winning move in about4milliseconds while OFF spends its
time budget. Cheap shallow terminal handling might provide the same saving.

That concrete uncertainty selects a fresh2176-2179 sixteen-game route comparison:
installed cold Core maxD2/q0 versus completion ON, common2second upper target,
Unit/v3 and swapped owners. Actual completed depths and unlike executor/ordering
costs must be reported; maxD2 does not guarantee completingD2. No Elo, default,
outcome-selected extension, longer single-job permission or all-WDL gate follows.

All16 shallow-route cells finish in1075.431seconds/681plies: Core5wins,
completion3wins, three true repetition draws and five ongoing64. Fifteen distinct
action trajectories remain. All three completion wins are owner0 on2178/2179;
five Core wins use v3, while2177 stays ongoing in all four cells. These dependent,
leaf/owner-sensitive outcomes do not support adopting a more expensive search.
Core completesD2 at269 of341calls andD1 at72; its common upper target is not a
fixed completed-depth promise. Core/frontier caller totals are340.949/670.164sec;
internal search totals334.344/665.189sec. Core's caller includes PV validation,
whereas the frontier returns only a root action. Different ordering/executor
conditions remain part of this route comparison. Maximum calls2.040/2.108sec
and median.973/2.016sec are local measurements, not universal latency guarantees.
Core materializes163646 successors and visits164326nodes; frontier materializes
3652849 successors. Generation/evaluation calls are35042/129389 and51805/3651089.
These work counters do not count every internal semantic transition.

The ablation's19 resolved calls are not all immediate terminal selection:
eleven selected children are terminal, eight remain ongoing despite a resolved
root. The latter include three current-side winning and five losing resolutions.
This is evidence of a deeper mechanism, not an independent WDL certificate or
economical advantage. All eight, including losses, are retained for a common-
parent installed-D2 control using their original1/2second upper target. Whole
selected-child next-reply diagnostics remain scoped observations, not a new
admission or all-defense proof requirement. No automatic fit, search/default
adoption or further longer-game experiment follows from this comparison.

The complete shallow-route reply diagnostic covers681 selected children,
574 unique full-history states and107 cache hits, with66618 public reply
transitions in635.592sec. Eight distinct selected-child states expose an opposing
immediate win: frontier5/Core3. All three Core cases had completed onlyD1.
These are path witnesses, not an avoidable-error rate; unchosen alternatives
were not fully tested and resolved losses may already be forced.

All eight nonterminal completion roots receive the installed coldD2 control.
Five losing resolutions have corresponding Core mate-range loss scores; three
winning resolutions have no Core mate score despite completingD2. Seven of
eight actions agree. On the three winning roots, maxD3 requests still complete
onlyD2 at2.016-2.033sec, retaining scores-200,0,-2052. Cached frontier/new Core
timings are unpaired and scores use different terminal scales; neither is an
independent WDL certificate. The concrete winning-resolution gap survives this
cheap baseline and is worth keeping, rather than banning the whole route.

A declared128/512/2048-successor cost scale retains all three winning roots and
all nine calls. The2173Unit ply29 win resolves at184 successors in.051-.059sec;
the2174v3 ply3 win resolves at1152 successors in.271sec. The2173Unit ply27 root
stays unresolved through2048 successors (.806sec). This exposed diagnostic
motivates one prospective question: can a fixed small completion prepass add
useful signal while leaving enough of the SAME total deadline for installed
Core? It does not select a policy from exposed labels or authorize extra budget,
default adoption, longer games or renewed qualification of old data.

The alternative drop-service probe materializes only semantic drops at five
saved2151ply3 top children, retaining full state and auxiliary prerequisites.
Checking-drop counts for typesA/X are1/0 at both safe index20 and unsafe33/38;
the unsafe47/48 counts are3/0 and4/3. Full drop counts differ slightly, but the
checking-count subvector aliases the safe and two unsafe children. Availability
or check incidence is not mating utility. Feature extraction costs.017-.024sec
and290-518 internal semantic transitions per child; generation costs are
reported separately. No count penalty, model expansion or fit follows.

Decision: defer the unmodified expensive frontier as a default. Retain the
three finite winning gaps as a narrower combined-budget search hypothesis.
Conditional drop service remains an alternative requiring more useful response
information than check counts. These observations change the next experiment,
not the two research mainlines. Products, search defaults and prices stay fixed.

Recovery: data/completion_ablation_20261010.json and the purpose-specific
completion-ablation-20261010-index.json route all declarations, sources, work
caps, adverse observations and full states. The first package producer fails
when it reads a dataclass action as action_to_dict. Keep its archive/source;
a separate verify_existing.py matches the recorded action against public legal
actions without modifying experimental bytes. The repair source is isolated in
completion-ablation-20261010-repair.zip. Verification replays1511 saved game
states, sixteen winning reply-action occurrences across eight positive states, eleven Core control children, five
drop-service children and374 drop options. Recovery is not independent science.
