# Root budgets, Native guard comparisons and preserved finite adversity

2026-10-17. Science remains OPEN. Production base: `cd7be4d4d017ca19994546b4c30451ac9012c382`.
This delivery fixes observed rule inconsistencies; it does not adopt a faster
root policy, evaluator, cache, model or feature backend. Full tables and version
tiers are in [data](data/root_budget_native_guards_20261017.json); the source and
sanitized evidence capsule is in [archive](../archive/root_budget_native_guards_20261017/README.md).

## Delivered correctness changes

Dot supplied a concrete source prediction after reading fixed public source.
The local PRIMARY executed it: an admitted capture guard with a subject offset
outside the board and `count == 0` covers square16 in Core, but Native omitted it.
A separate locally identified admitted `exists == 0` guard over an occupied
source produced the opposite error: Core excludes16, Native invents its attack.
The ordinary `count == 1` source control agrees. These are existing Native
semantics defects, not consequences of removing NP/pass for a feature query.

`state_guards_hold` now makes an unresolved subject an empty candidate range,
then performs the declared comparison on either count or boolean existence.
It no longer short-circuits an unresolved subject or ignores the exists operator
and value. The kernel advertises `semantic_state_guard_comparisons`; older
kernels explicitly decline subject-bound guards and nonstandard exists
comparisons, while safe ordinary counts/exists remain available. Core fallback
and the explicit Native refusal are different paths; no automatic Native
full-search fallback is added.

Cross-mechanism checks found two additional concrete boundaries. A drop has no
source, but the Native packed source sentinel255 is a real square on16x16.
An actual admitted rule has509 Core actions versus255 Native actions, losing254
semantic bindings. A marked-drop variant demonstrates that these can carry a
different auxiliary-state effect. The compiler now explicitly declines wide
source-dependent drop state guards; it does not rewrite the action codec,
truncate the board/history or remove that rule from Core's task domain.

A valid drop guard using `offset_from_source(0,0)` also raised Core TypeError
while converting the absent source into coordinates. An offset from an unbound
base now resolves None, consistent with the existing empty-selection semantics.
Eight new8/16-board cases cover subject/global forms and source/offset refs.
Four actual AlphaBeta calls begin with a real king capture and opponent reply,
then choose the marked semantic drop at completedD1:8-board Native legality and
16-board complete Core fallback, all history/hand/aux/PV retained. No fabricated
hand/root history or new learned policy is involved.

Similar declaration code was examined rather than changed speculatively: an
out-of-board fixed declaration ref is Core-admitted but Native compile-refused;
action-bound declaration offsets are rejected by Core compilation. Those are not
admitted Native counterexamples and do not expand this repair.

## Qualification and failures

- Final normal four-layer run: **3177 passed**, after final Core/compiler changes.
- Final focused checks: **235 passed**, including192 comparison cases, full child
  controls, old-kernel refusal and8 cross-mechanism drop cases.
- Isolated final source: **294 passed**,80 loaded project modules bound to that
  checkout. The separately rebuilt C kernel was reused only after every C/header
  byte matched final source; final Python/compiler/test files were copied anew.
  The earlier286 checks remain their earlier source tier.
- Exact final-source Core replay:37 preserved records,1396 committed full-history
  edges and2333 legal PV edges;26 actual terminals,10 administrative UNKNOWN
  records and one interrupted27-ply prefix. No new search or games in this reader.

The first full run had2969 passes and200 setup errors, all WinError5 enumerating
the existing OS pytest temp directory. The exact200 previously unexecuted cases
then passed using pytest's supported project-owned basetemp. A fresh complete
3177 run passed after final source changes. No ACL or machine security setting
was changed; Smart App Control was not asserted as this error's cause.

Own implementation/recording errors remain visible: the contract recorder first
retained a live runtime view and could not pickle mappingproxy; a test fixture
used invalid spatial/effect names; a new admission helper used the schema field
instead of IR `guards`; and snapshot tests initially compared list versus tuple.
Original failed source/logs and corrected qualifications are distinct. None is
counted as a successful semantic control or blamed on missing user permission.

## Root scan contract and exact node forecast

The two lawful neutral-declaration controls return q0D1 score0 with scan bothON
andOFF, while raw static child evaluation suggests root+100. The child really
executes NO_CONTEST and the parent is unchanged. A scan is not a completeD1.
An accepted stateful override raises on the repeated complete child at callback4;
generic reuse would hide that observable failure. Raw versus bounded static
scores also differ. No arbitrary evaluator cache is introduced.

Twelve actual cold q0 controls on complete generated roots N20/32/79 establish
an inclusive-boundary forecast: scanON needs a node cap2N+2, OFF needsN+2.
One less aborts at the final boundary. This is a scoped forecast, not a time
completion guarantee or formula for qsearch, warm TT, root declarations or early
winning terminals. Root admission and legal generation also consume wall time.
All old frozen budgets stay unchanged.

A different private terminal-only scan preserves all five complete outputs and
two actual immediate-win witnesses. Whole-caller ratios for its three costly
roots are .640/.968/.686. The middle root misses the frozen10percent per-root
criterion, so DEFER it. No terminal-only game campaign or default change follows.

## Existing root flag: all prospective32 games retained

Eight newly seeded8/10/12-board families preserve atom/temp/compound/screen/drop,
original promotion, auxiliary state and relevant histories. Candidate attack
features are fixed at dynamic2/anchor0/promotion0; the same materialD2/.25s foe is
used for both existing root-flag arms. Candidates areD3/4096nodes/1s;64 plies
administratively censor, rather than declare draws. Generation and all games
share the original1800-second protocol; all32 finish in768.954seconds.

Both arms give **10W/1L/0D/5UNKNOWN**. Eleven resolved pairs all have gain0;
all16-pair mean gain bounds are[-.625,+.625].1274 physical edges/calls are retained.
DefaultON uses319 candidate calls/298.841search seconds/492437 evaluations;
OFF uses323/312.064/473023. Different trajectories prevent a total-game speedup
claim. The tenON depth0 returns are actual immediate wins, not failed searches.
No true fallback occurs at this one-second candidate budget. More completedD2
or fewer evaluations does not justify changing the default; do not pool this
cohort with the older half-second feature comparison.

Old-cohort attribution separately finds attack56NP16 and22nonNP true fallbacks,
versus material16NP16 and0nonNP; NP7 has none. This narrows a bottleneck rather
than asserting every Core no-progress rule fails.

## Feature-only projection: scoped equality, negative adoption decision

The private projection preserves original Core GameSession/search/history and
queries only S0/S1 Native attacked_squares. It explicitly binds the original
RuleSet/compiled/Position fingerprint, removes only NP/pass/consecutive policies
from a separate feature capsule and never uses its Native legality, terminal,
3+9 or search.12 states match;20 actual Core callers have equal decision/work/
full child/PV pairs and four signed-error/cancel/fake-clock controls pass.
All7087 saved feature observations match direct Core maps, with5773 distinct
Positions per-call and1544 scalar square checks. This is finite coverage with
shared IR, not an all-domain proof. A real constructor binding omission was
corrected between v1 and v2; source tiers are preserved.

The available nine cold whole-caller ratios have geometric mean .992; the tenth
has a zero baseline interval at Windows clock resolution. Do not impute its
ratio. The original all-ten cost criterion is not evaluable, and available nine
also miss it. Two wide roots .629/.650 coexist with setup/marshalling adversity
on cheap states. DEFER general adoption; no new backend API is delivered.

A separately frozen16-slot warm-wide consumer then tests actual amortization
with a stronger fixed materialD3/8192nodes/2s foe and equal candidate limits.
The new semantic counterexample changed priority; PRIMARY terminated only its
verified own producer, leaving **4 actual terminals +1 interrupted27-ply prefix
+11 unstarted slots**. This is an intervention, not a user stop, time-cap event,
or administrative draw. Original files are unchanged. No completed/partial slot
is retried. In the first completed family a Core WIN becomes a Native-feature
LOSS; the other role loses in both. That adverse pair is retained, not excused
by faster features. The interruption decision preceded reading those outcomes.

A new zero-search diagnostic uses the existing public Native evaluator on this
state-guard-free family:99 full record states and204 PV states give606 owner-map
comparisons with equal features/values. First common-parent divergences occur
at ply10(D2 versusD3, W toL) and ply11(D1 versusD2, L toL). This new-kernel checked
path tier does not verify the old unrecorded internal search leaves or prove
optimal action values. It reinforces the distinction between exact cheaper
inputs and useful finite decisions, without another arena or WDL gate.

## Collaboration and continuing direction

Daily request GC-SLACK-20261017-100020-fbaab04c has one confirmed root
1792198926.102459 and one complete Dot reply1792199141.915699. Exact payload
readback/reconcile passed. Dot read fixed public report/source/parser, not the
private helper/7087 rows, and did not execute them. Its source prediction was
locally reproduced, extended and repaired; no routine acknowledgement or
publication approval gate was imposed. AUX83's previously read fixed report
remains read-only context; no new AUX execution, code adoption, checkout/state
writes or worker is claimed. No controlled efficiency percentage is inferred.

Automatic review initially mislabeled the new Slack request as a duplicate and
its denied-tool output as a fabricated receipt. Preserved actual return, local
bookkeeping distinction, new-root read and existing authorization supported one
deliberate reassessment, which produced a real receipt. Another review confused
120seconds with120minutes; explicit2-minute/7200-second evidence resolved it.
No successful delivery was invented, security setting changed or enforcement
bypassed, and no renewed user authorization was required.

Search capability/cost remains first; cheap material, existing attack opt-in and
root defaultON remain. No price fitting, human holdout, model training, competing
solver, automatic merge or UI work follows. All failures, missing slots and
UNKNOWN are available in the checked capsule; next work must have a new concrete
premise rather than repeat these negative cost/arena panels.


Late recovery also reads the complete AUX85 parent1792199773.630129 and one Dot
reply1792199941.907679, no remaining pages. The disappearing oldTRAIN3s gain,
122-node negative sensitivity and heldRWIN/heldPUNKNOWN are OWNER reports, not
PRIMARY execution or a proven R-versus-P ranking. Dot proposes a prespecified
R-versus-N capture/deployment diagnostic; it remains advice in AUX's lane.
PRIMARY does not duplicate the grid, learner, solver or inspect AUX84/85 files.
The previously read AUX83 fixed report remains a separate earlier report tier.
