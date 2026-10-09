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
