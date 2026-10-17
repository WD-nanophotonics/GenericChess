# Learning cost, signal coverage and Generic feature transfer - 2026-10-17

Science remains OPEN. PRIMARY checks the existing positive AUX86 learner and
its prospective Core consumer boundary. No new learner, training, game campaign,
solver, product/default change or API is delivered. DEV_AUX retains its separate
checkout and ongoing87 training-regime study.

## Decision and actual cost

Keep the scoped positive learning result. Describe its computation accurately
and retain the full experiment history. A reported78.04-second final TRAIN is
not the total cost of obtaining or evaluating that result.

|Existing producer|Role|Reported seconds|
|---|---|---:|
|2492|Original smoke TRAIN before its retained repair|85.010|
|2495|Corrected online TRAIN|249.070|
|2497|Episode-frozen TRAIN used by the positive result|78.039|
|2493|Original smoke evaluation|123.076|
|2496|First two-family episode evaluation|31.810|
|2500|Eight-family episode evaluation|123.454|

The final TRAIN plus its two evaluations costs233.304seconds. All six recorded
learning-route producers total690.459seconds:3193770TRAIN nodes and2169303EVAL
nodes. These are immutable reported wall measurements, not independent timing
reruns, CPU-time totals or a complete account of engineering/manual effort.
Nested arm/whole timings are not added twice. Original smoke and corrected
online methods are not extra replications of the final positive method.

Game/curve accounting retains302aborted TRAIN nodes (150/17/135 across the three
TRAIN producers). The original smoke evaluation actually executed16duplicate
initial-baseline slots, costing328396nodes; hypothetical later baseline reuse
cannot retroactively remove that cost. Producers2496/2500 paid their respective
seed/family/role baselines once. No equal-cost superiority against price grids,
whole project lifetime cost or universal efficiency follows.

Exact ledger: [data](data/learning_cost_20261017.json). Earlier expensive Core
diagnostics are supporting verification, not prerequisites for executing the
small learner. Further Core engineering needs a concrete consumer dependency.

## Existing signal covers four directions, unevenly

Read the actual5299recorded PV value/gradient receipts and37frozen episode
impulses reproduced in the preceding segment. The four free coordinates are
N/B/R/Q; the pawn remains fixed. For each seed the integer feature Gram has
exact rank4. Numerical returned-gradient and episode-impulse matrices also have
rank4 under the stated relative tolerance1e-12.

|Initialization|Nonterminal rows|Distinct four-feature vectors|Raw feature condition|Gradient condition|
|---|---:|---:|---:|---:|
|1977|3053|77|5.328|3.976|
|8173|2178|112|1.949|1.540|

This rejects a completely unobserved linear direction in these recorded feature
rows. It does not identify unique optimal prices, global return, effective
independent sample size or adequate exploration. For example, the Q feature is
nonzero in282/3053rows for1977 versus1524/2178for8173. Distribution and cancellation
matter; full algebraic span does not make the trajectories equivalent.

The two episode-impulse condition numbers are8.160/2.099. Those vectors combine
credit and cancellation, not causal per-piece effects. No additional exploration
batch, network or parameter selection is justified solely by a nonexistent exact
nullspace. First assess the already-running87 contrast when published.
[Full observations](data/learning_signal_span_20261017.json).

## Original recipe and calibration are separate choices

The short [TDLeaf paper](https://arxiv.org/pdf/cs/9901001), Eq9, and the longer
[KnightCap paper](https://arxiv.org/pdf/cs/9901002), Figure3/Eq11, present the frozen
episode/PV update. They are distinct documents. The longer experiment calibrates
one pawn to0.25 through tanh, fixes the pawn coefficient and conditionally filters
positive TD errors from unexpected opponent blunders. That online-opponent setup
is different from this symmetric four-weight self-play pilot. The headline
experiment used material priors; its unity-initialized control learned more slowly.
Its discussion of Beal-Smith material learning is not independent access to the
full1997 paper. Neither recipe nor speed should be copied without its premises.

For pawn1 the paper calibration is beta=atanh(.25)=.2554128119; this pilot uses.1.
A receipt-only local derivative comparison at the SAME frozen weights/leaves
gives paper/current gradient multipliers ranging.2084..2.5541 for1977 and
.0794..2.5541 for8173. Thus a single global alpha multiplier does not equate these
local gradients. Under the paper beta,476/470nonterminal leaves have prediction
magnitude>.95, versus0/0at current beta. This is a saturation diagnostic, not a
better training result or a reason to retune87.

The executable rederivation matches all original lower-order-statistic summaries
and returned gradients within4.17e-17. An initial reproduction used interpolated
quantiles and failed exact summary comparison; that source is retained and the
definition is explicit. Terminal leaves still have zero new gradient.
[Calibration observations](data/learning_calibration_20261017.json).

A separate original [AAAI2002 poster](https://cdn.aaai.org/AAAI/2002/AAAI02-150.pdf)
reports both favorable learning from a material-only start and adverse results
from a stronger hand-tuned start. These are separate online runs, not matched
paired causal evidence. It reinforces checking the actual common deployment
effect, rather than treating parameter movement as improvement or assuming an
initialization-independent convergence guarantee. No current experiment is
changed from that observation.

## Actual complete promotion/capture/drop interface

The preceding report's Generic feature/action tier was source-only. This segment
upgrades ONE existing complete semantic witness to actual execution: promoted
capture R->TP, opponent promotion R->TP, then hand-R drop. Published AUX86
SessionEnv, material.channels and typed choices/execute helpers run against
current full Core state. All rule types, auxiliary values, no-progress semantics
and complete history remain; no simplified task was substituted.

For owner0 the resulting board/hand identity counts are:

|After edge|Board current identities|Hand base identities|
|---|---|---|
|Promoted capture|TP:+1|R:+1|
|Opponent promotion|R:+1|R:+1|
|R drop|R:+2|empty|

Every complete child state equals the retained witness. Both perspective vectors
are opposite, original caller state/record stay unchanged, and three pops restore
each previous full state, record, result and vector. This is three typed action
executions, zero searches/training/solver calls, on one existing family. It is
not all-domain equivalence, Generic strength or an AUX solver execution.

Two setup mistakes occurred before any action: reading piece_types on the compiled
object and sorting PieceType objects directly. The scripts and corrections are
retained. The public helper modules are included so execution does not depend on
an untransported AUX checkout. The known RESTART/NO_CONTEST-to-zero hazard remains
an owner-notified future Generic scoring issue, not silently repaired here.

## Concrete main-PV versus q-leaf boundary

A complete main PV is insufficient to reconstruct a q-based learning gradient.
The existing public Core API promises a main line, while its qsearch returns a
scalar. An actual complete-state example now makes this distinction concrete.

The4x4 rule starts with top-first layout '..rk / .... / ..X. / K...'. R moves
vertically; X leaps(0,3), making this particular X immobile. Both anchors, full
capture-to-hand semantics and all histories remain. Fixed material includes board
and hand counts, with R1/X2. Fresh TT/order-disabled public calls use D2, full
main PV, root scanoff,20000nodes/3seconds and qhard6.

|Both legacy and semantic compilers|Returned score|Main-PV material|
|---|---:|---:|
|q0, R1/X2|-3|-3|
|q1, R1/X2|-1|-3|
|q1, R1.1/X2|-0.9|-3.1|
|q1, R1/X2.1|-1.1|-3.1|

The q1 main line moves the white anchor a1-b1 and the black R c4-c2, capturing X.
A legal further anchor capture b1-c2 explains the scalar: its complete material
vector is(R:+1,X:-1), whereas the nominal main-PV vector is(-1,-1).
The recapture is nonterminal at ply3/history length4. It is an explanatory legal
witness, not a new public selected-qleaf identity receipt.

The measured R finite-difference slope is+1 for the returned score and-1 for the
nominal PV material. Merely recomputing the PV leaf gradient can reverse credit.
Actual returned leaf/terminal/stand-pat identity is needed if a future Core-based
learner uses qsearch. Current AUX search returns its own leaf; this finding
requires no new API, production change or repeated q campaign now.

All preparatory negative controls remain: four D1 calls use the first-iteration
ordinary-q0 reserve; four D2 full-rook unit calls choose equal-material quiet PVs;
four vertical-rook unit calls expose the mismatch in legacy but happen to choose
a matching quiet PV in semantic. Those matches never established a universal
contract. The final eight predeclared fractional controls remove the unit-value
quiet/capture tie in both compilers. Twenty original calls total, plus the
separately identified same-source qualification replay; no evaluation games or
learning are counted. A wrong constructor field failed before the first call
and was corrected without changing a budget.

## Qualification, ownership and continuation

The [capsule](../archive/learning_cost_generic_transfer_20261017/README.md)
has67members including a manifest, with exact hashes/CRC checked. One old
logical-result source path is sanitized only in the publication copy; private
originals remain. No raw Slack/account output, personal information, credentials,
PDFs, bytecode or Git metadata is published.

Independent restoration from247tracked files at Core base
c01802cc72948d2309d4c3c072dca98c4b44887e and66payloads reruns eight producers in
8.31seconds: cost accounting, calibration, span, three typed actions and20Core
queries pass. Non-time results, full states, actions/PVs and node/qnode counts
match. This is clean-source reproducibility of the same engine and historical
data, not new independent training or an independent rule authority.

AUX87 root1792210550.016409 was freshly read as parent plus all four replies,
with no remaining pagination; at that read there was no new peer publication.
Its source/results remain owner-reported to PRIMARY. No AUX checkout, computation
or unpublished source was touched. Next inspect its fixed publication and common
plain-D2 deployment results, preserving shared-prefix exposure90013-90020.
No routine Dot acknowledgement is required before independent work or delivery.


## Newly published87: actual independent follow-on

A later complete read recovered the new AUX reply1792214173.318149 and the88
request1792214684.150599. Fixed87 source is
[0d9cba18252b7669c4dcf68f228dfd680f296d8e](https://github.com/WD-nanophotonics/GenericChess/blob/0d9cba18252b7669c4dcf68f228dfd680f296d8e/results/dev_aux/SEGMENT_20261017_87.md).
Its173payload hashes/CRC and archive SHA5b1d8af5ddf32ab2d14ef2e81ffafb13a3ef8bf941be81ff68117289566678bf
match. PRIMARY executed the32published tests and closed owner auditors on a
separate exact extraction:317updates,931validation games and208013legal plies
pass. Those auditors were authored by AUX; running them is not independent
PRIMARY authorship or new training.

PRIMARY separately wrote a forward-convolution TD calculation and paired game
tally. All317updates match within4.44e-16;48025query receipts include48017completed
and8failed queries costing1299nodes. All304actual final residuals are zero;
earlier credit still produces316nonzero episode updates. No outcome is fabricated
for13censored episodes. This is receipt arithmetic, not all-tree verification.

Endpoint384/384games are actual terminals on16new91000-91015families, all4initials
and both roles. Both training regimes improve every initialization under common
plainD2 deployment versus the same uniform foe. Independent pooled mean W-L gains
are plain.5 and q2.3046875; direct q2-minus-plain=-.1953125. The same128physical
initial baselines are reused, not paid or counted as independent twice.
Eight TRAIN arms each use1Mnodes, with different trajectories/game opportunities;
this is a whole training-regime contrast, not pure target-quality causation.

The separate curves retain547/576games,29missing and4actual UNKNOWN. At1M, plain
gain bounds are[.375,.59375], q2[.1875,.40625]. Direct paired q2-minus-plain is
[-.3125,-.0625]. Subtracting the two marginal intervals instead gives the looser
[-.40625,.03125], because it discards exact shared-baseline cancellation. Bound
the two trained rewards directly, including missing/U, rather than treating one
shared uncertain baseline as two independent uncertainties. This is interval
arithmetic on this finite panel, not a population significance statement; the
reported clustered curve envelopes still cross zero.

A predeclared structural sample deduplicated to18actual completed queries across
all8arms, covering initial/nonzero-gradient/terminal/cut/forced-evasion paths.
PRIMARY reexecuted the fixed search at saved weights and complete histories:
action/value/PV feature/terminal marker/gradient/node count and all deterministic
stats match, with full roots restored. It is a structural convenience sample,
not all48025searches, random holdout or matched-wall failed-query diagnosis.
Original effective time was not journaled for one curve failure; no nominal replay
is used to relabel that U or diagnose an OS fault.

The source clarifies boundedq2 counts ALLextension edges, including forced
evasions; only nonchecking nodes may cut at qply>=2. It does not mean two optional
captures after every evasion. The frozen approximation/caps remain. No expansion
of q is supported by this finite result. AUX88's new TD-versus-mean-TreeStrap study
is already in its lane; PRIMARY read its request only, not88code or execution.

The known non-scoring hazard now has a published opt-in fix:
task2511.ScoringSessionEnv raises typed NonScoringTerminal for actual
RESTART/NO_CONTEST, preserving the result for an explicit caller policy.
PRIMARY's32executed tests include its7realGameSession controls. Frozen2492/86
SessionEnv still has the old behavior and old Chess pins stay unchanged. This
closes the concrete future-Generic scoring defect for the new adapter; it does
not establish full Generic learning, all-domain equivalence or repair the old
PRIMARY trajectory carrier automatically.

[Independent87 observations](data/learning_peer87_independent_20261017.json) and
[reproduction supplement](../archive/learning_cost_generic_transfer_20261017/README.md)
retain the tier distinctions. Keep cheap plain training as the current comparison,
inspect owner88's published common-deployment result next, and do not launch a
duplicate learner or revive Core optimization without a needed consumer.
