# Complete Native q0: terminal priority and execution attribution

Science remains OPEN. The delivered correction is code
8800b7fe71a195ba534892e638cc2febc954111d. Complete Native q0 is a useful
scoped research reference; these results do not authorize a default/backend/UI
switch or treating q0 as the existing default q4 method.

## Actual defect and correction

The persistent C negamax checked a winning declaration before checking whether
its node had already ended. A real 4x4 root has black Ka4, white Kb2/Rd1,
white to move, and an always-eligible black WIN declaration that does not require
being out of check. Core q0 D2 chooses Rd4 and actual GameSession submission
ends in white checkmate. Both old Native TT0 and TT1 instead report loss
(-100,000,000+1) and choose an ongoing child: they incorrectly let black declare
a win after the mating move had ended the game.

The change moves the existing WIN block after the existing terminal branch and
before TT probing. It adds no terminal call and changes no packet, evaluator,
stop, ordinary search default or UI. Nine new regressions include mate and a
nonmating max-ply boundary, both root-window modes, TT0/1, real cold/warm calls,
and an ongoing-root WIN positive control. The corrected tests give old8fail/
1pass; the new kernel passes all9 and45 related tests. One first max-ply fixture
was wrong because the rook could still mate: Core correctly gives mate priority.
That failed assumption and corrected no-rook control are retained separately.

All2,535 unique active tests execute successfully:2,411 pass in the initial
full run;124 fail in setup because the pre-existing default pytest temporary
parent denies access. Exact-case recovery into a new project-private temporary
root passes all124. This is combined coverage, not one uninterrupted clean run.
No assertion failure, OS permission/security change or evidence of Smart App
Control is attributed to that directory error. Required code publisher45 passes;
full remote SHA was independently checked. Rebuild the optional kernel from
source to obtain the C correction; no binary or virtual environment is shipped.

## Frozen ordinary inputs and method boundaries

The original flat-material assay is pinned to6c9c4fd8 and its old binary. Five
already exposed generated rules use seeds2401--2405, sizes4/8/12/16/18, roots0/8
with every played move/history witness retained; eight played semantic fixtures
cover live transformation, capture-to-base hand, drops, expiring state, compound
moves and off-target effects. A checked NO_CONTEST root is the nineteenth input.
The seeded-hand neutral fixture is rebuilt from its actual factory and attack,
not falsely treated as a fresh ordinary game record.

|Arm|Conditions|
|---|---|
|Thin Core runtime|One existing minimal Python alpha-beta, Native legality/check/availability when supported, repr action order, no TT/q|
|Public Core|Actual AlphaBetaPlayer, Native providers when supported, no TT, full PV, root tactical off, q0/hard0|
|Complete Native TT0/TT1|Actual SemanticSearchEngine, cold0/1MiB TT, order cache off, exact root windows, q0/hard0|

All arms use100 for nonanchors and0 for anchors on board/current and hand/base
axes. Resource caps are1/4s in opposite orders, maximum depth12. Constructor,
caller, kernel and actual work fields remain distinct. These are different
algorithms/comparators/schedules, not an equal-node or pure execution-speed ratio.
Native terminal units100M and Core1B are normalized by sign/distance, never by
comparing unequal raw numbers. Native size18 declines explicitly; the thin
adapter declines general declaration competition. Full/Core arms retain it.
Those finite adapter limits do not redefine the complete generic project target.

The142 actual fixedD2 queries plus10 explicit declines all close at D2 with
matching normalized scores. An independent unpruned Core D2 oracle closes13/19
whole roots and verifies102 actual choices/declarations as argmax members.
Six12/16/18-wide roots hit their20s cap:40 query choices remain UNKNOWN, with
no extension. Scalar agreement does not silently close those missing maxsets.

The284 actual resource queries plus20 declines close all304 cells. On68 paired
supported NativeTT0/public-Core comparisons, Native is51deeper/17same/0shallower;
40 retain the same action/declaration. NativeTT1 is13deeper/55same versus TT0.
These are completion observations, not wins or stronger play. Full state/history
restore and returned action/PV validation hold. The old binary remains fixed
throughout; a short diagnostic/test/build overlap and ordinary concurrent load
are interpretation limits, not an exclusive-machine timing claim.

## Identical algorithm and complete state execution

A separate bridge drives that very same bare Python alpha-beta over Core with
Native providers versus complete Native capsules through existing public scalar
APIs. Sixteen supported nondeclaration roots use identical repr ordering,
terminal winners,1B mate units and material. Complete initial histories/events
are imported and checked;755 root/one-ply states pass exact imported snapshot,
legal-set, material and terminal comparisons. Core can omit a declared default
auxiliary slot that Native materializes; only that existing semantic default
equivalence is normalized in the shape comparison. Full imported Native history/
auxiliary snapshots still compare literally. The initial raw-tuple mismatch is
not presented as a rule defect or removal of auxiliary semantics.

All128 queries complete:32 traced pairs have exactly identical full action/leaf
stream hashes, work, scores and actions;32 uninstrumented pairs retain the same
work/results. Native/Core search-wall ratios range0.145--0.549, median0.302.
Construction precedes these bridge timings. Native public scalar validation,
profile parsing, checked state copies and history work remain charged inside
the search. This demonstrates a finite state-execution contribution, not the
persistent C loop's speed factor, a deployment result or universal throughput.
A failed preaudit omitted RuntimeSearchState history; it executes zero queries.
The96 successful calls before the later aux representation check are preserved;
only the32 remaining calls resume after correcting that check.

## Independent finite goal and actual rule prices

At compound_shift, complete Native exposes a root loss within6 while public
Core1/4s retains the material estimate-200. A literal Core attacker/existential,
defender/universal solver proves white can force the terminal win within6 from
this black-to-move root, using5,198 transitions. A separate consumer checks the
whole certificate and all defensive action coverage in86 further transitions/
87 nodes. It uses actual complete Core terminals/declarations/history, not a
score or principal line as a label. It establishes earlier finite information;
all root choices being lost is not evidence of a better selected outcome or
shortest possible mate. No complete WDL admission requirement follows.

The next separately frozen assay replaces the arbitrary vector by the actual
existing rule-derived static board/hand tables on the10 generated roots.
Dynamic mobility, anchor escape and promotion bonuses are explicitly zeroed;
this is not the complete default dynamic evaluator. Separate board/current and
hand/base tables, including the existing hand discount, are passed without
rounding or fitting. All694 supported root/one-ply scalar evaluations match
Native exactly. Twelve Native cells at18 decline explicitly.

The108 actual calls close:16 supported fixedD2 score pairs match, while32
resource pairs give12deeper/20same and26 identical actions. Cold profile builds
cost0.0012--0.2514s across4--18 boards; the existing memory cache hits take about
12--15microseconds. Keep that existing reuse; no new cache is motivated. The
smaller completion advantage with real prices motivates examining the existing
ordering interface, keeping leaf values fixed, rather than extrapolating the
flat-vector result to default play or adding another transport variant.

## Ordering and selected-choice diagnostics

The existing ordering_checkpoint interface supplies either a flat100/0 vector
or the frozen rule-derived vector for sorting only; every arm retains the same
rule-derived leaf/hand evaluation. These are zero-training material checkpoints,
although the existing result field calls the enabled API learned_move_ordering.
No new model, Native ordering path or default flag is added. Order cache is off;
full checked search transitions and discarded material-view ordering trials are
counted separately.

All96 calls close on the four exposed12/16 roots: eight fixedD3 three-arm groups
have literally identical complete score/action/declaration/PV/decision-line/
depth tuples. At1/4/16s the flat ordering is12deeper/12same, rule ordering
10deeper/14same versus plain across24 paired cells each. Ordering can pay for
millions of extra trials by reducing searched work, but leaf prices need not
be the best ordering prices. At2404-ply8/16s flat ordering reachesD4 twice while
rule ordering and plain remainD3. Keep the cheap baseline in transfer and do
not select a winner from one favorable depth or demand an exact ordering model.

A separate pure-Core fixedD3 diagnostic evaluates every distinct changed root
choice in the original flat/profile resource pairs:20 bare alpha-beta branch
queries,13,691 recursive nodes, all complete in5.748s. The56 differing flat
paired instances are equal at that objective. Of six profile instances, Native
is lower in four and higher in two. Repeated arms/orders are not independent
samples. This is a predefined finite static-material diagnostic for methods
that actually deliver different horizons, not WDL, a game win, or proof that a
lowerD3 value makes a deeper search worse. Changed actions alone are not gains.

The prospective transfer freezes seeds2501--2507 with sizes4/8/12/16/8/12/18,
roots0/8 and the full random played walk before any query. No prices are fitted.
One4-board game ends at ply1, so its ply8 root is unavailable and is not replaced.
Two18-board roots explicitly decline36 planned cells. All198 actual queries on
11 supported roots close;22 fixedD2 three-arm complete tuples literally match.
At1/4s flat ordering is20deeper/24same, rule ordering16deeper/28same versus plain
across44 paired cells each, with no shallower case in these cells. Inputs are
new to this transfer but its design follows exposed development results; this
is not universal or restored unexposed validation. Keep both explicit research
controls, including their real costs, rather than switching the default method.

The next feasibility check begins before building a new kernel. It compares a
very cheap current-target/promotion/drop delta approximation with actual complete
Core transitions on all32 available original/transfer frontiers, including the
unsupported18 inputs. All3,098 actions complete in21.957s. Exact delta equality
holds for2,820; hand-capture yield, transformations and off-target effects remain
real differences. Every cheap top-tie set contains an exact maximum, but only30
have every tied action at that maximum: offtarget_token_live and2505-ply8 retain
bad ties. Large top sets can make mere overlap trivial; this is not a playing
or deployment result. The hand-yield example gives cheap1,000 versus actual
1,900, not an engine/evaluation error. This deliberately approximate ordering
never removes actions or changes the complete search state or rules.

Next test a private cheap ordering implementation behaviorally only if its saved
trial work can pay at the caller. Initial source inspection has begun: the
existing action bit fields suffice for local target/promotion/drop features,
but candidate buffers can include illegal candidates and full traversal checks
must remain authoritative. Retain correct first-legal-child/PV/TT behavior,
all later effects/history and exact fixed-depth result checks. Do not require
exact ranking as a scientific admission gate or build a new public framework.
No such C prototype or default change is included in this delivery.

## Evidence and limitations

Agent-generated inputs, declarations, exact rows, source versions, failures and
proof/consumer are delivered in the purpose evidence archive and data index.
Raw Slack/account/receipts, host logs/XML, binaries and private/user inputs stay
Git-ignored. The initial producer declarations are immutable; zero-query setup
repairs and the actual later producer hashes are recorded separately. No prior
frozen budget, exposed-validation status or source measurement is relabelled.
Earlier H5 censorship remains UNKNOWN; this distinct finite H6 certificate does
not retroactively prove it. Collaboration is in ../operations/COLLABORATION_LOG.md.
