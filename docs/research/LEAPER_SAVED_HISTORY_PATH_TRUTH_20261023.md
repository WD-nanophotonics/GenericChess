# Saved-history bounds and literal path truth

DEV_AUX / sidemission,2026-10-23. Fixed own input91659af86b138a85e2a8843e594dc6dfe36f2194;
shared committed sandbox c7e7b84101ee286a4d3bc98a19a33463afd2809d,read from FETCH_HEAD.
Rules/Core/search/history/Session/runtime have no new shared delta. PRIMARY retains
rule/layout sampling,forward games,E0 features/predictions,inverse and defaults.
AUX supplies truth,certificates,coverage/cost and matched offline scoring.

## Result and denominator

The same369complete records and34037ongoing full histories now have31889exact
WDL labels,81more than the preceding packet. No rule,record,history or mu support
was added or replaced. Existing failed/partial100k,1m,900s and50kstudies remain
closed and unchanged. No Player query,policy game,training or product change.

| Property | Previous TRUE | Previous FALSE | Previous UNKNOWN | Current TRUE | Current FALSE | Current UNKNOWN |
|---|---:|---:|---:|---:|---:|---:|
| WDL fork |1918|29899|2220|1932|29901|2204|
| Cooperative decisive path |4627|24778|4632|5443|24780|3814|
| All continuations draw |24778|4627|4632|24780|5443|3814|

Cooperation gains818known labels:816positive and2negative. Its complement is
all-continuation DRAW,not minimax DRAW. Current WDL intervals are27965[0,0],
2074[1,1],1850[-1,-1],1945[-1,1],189[0,1] and14[-1,0]. The2148nonexact
intervals are not scalar training labels or draws.

Original initial cooperation remains9TRUE/1FALSE;initial fork remains9UNKNOWN/
1FALSE. One initial WDL tightens to[0,1]. At K3:8:16,the actual Bmove
(0,1)->(2,3)captures the opposing A and reaches a saved exact-DRAW full history.
That guarantees a nonloss from this initial history;other first actions remain
unresolved,so neither a forced initial win nor a known initial fork follows.

The distinct-record fork-event tally changes148TRUE/36FALSE/185UNKNOWN to
150TRUE/36FALSE/183UNKNOWN. Guarantee-loss event changes81TRUE/36FALSE/
252UNKNOWN to83TRUE/36FALSE/250UNKNOWN. There are243critical record-actions
at232different full histories.540controller references are not540independent
games. Earlier UNKNOWN histories still prevent exact first-event times.

Both newly certified guarantee-loss events are one-ply win misses by RNG,
not new evidence of a deeper or material-learning mechanism. At record
4d58bcbe…ply12,actor0moves K(1,1)->(0,2)instead of the actual mating
A(2,2)->(2,3);the recorded game later draws by repetition. At a4a55639…ply7,
actor1moves A(1,2)->(0,1)instead of the actual mating A(1,2)->(1,1);the
recorded game later draws at the actual max128rule clock. Each record has two
controller references with RNG at the acting seat;those references are not
independent games. The immediate winning options were already known,the new
result is that each chosen ongoing child has value[-1,0],so skipping mate
really lowers the win guarantee. Neither child's exact WDL is claimed. A
correct immediate-win FLOOR is designed to address this tactical opportunity;
there is no counterfactual policy rollout or evidence that learned prices are
needed. Full IDs,queries,actual terminal replays and Core children are retained
in new-critical-cases.json and independently checked by the reader.

## Exact saved-child connections

One complete Core successor set was generated for each of2271existing histories
with unresolved WDL or fork.14407edges included2500children whose exact full
history IDs were already in the frozen inventory. No child outside this set was
expanded. The actual ply strictly increases on every edge.

In descending ply,translate a child's mover-relative interval[L,U] to[-U,-L]
when the mover switches;retain it if the same mover acts. A root's minimax
interval is[max action lower,max action upper]. Intersect with existing certified
bounds. Different action-value intervals prove a fork only when their possible
values cannot all coincide. Missing ongoing children remain[-1,1]. Cooperative
truth propagates as an existential OR;negative truth needs every legal child.

This gives267narrower WDL intervals,including81new exact values;14new forkTRUE,
2new forkFALSE and346new cooperation labels.2197rows change mainly because
previously missing action bounds become explicit;2197is not the new-label count.
The producer takes48.780component seconds/60.655end-to-end seconds including
input loading and output materialization. The independent public
legal_actions/apply_action checker verifies all2271roots/14407edges in18.226s.
Imported baseline truth keeps its earlier qualifications;it is not all re-solved.

## Negative alternatives actually examined

All952known cooperative parents in the retained layer already have a known
cooperative child. No residual saved-only disjunctive clause forces another
unknown child label. A separate two-way Bellman interval consistency check
replays all35648recorded actions and examines34037root max-factors. It adds
zero WDL/fork bounds:55.655s record replay plus29.409s constraint calculation.
Known-parent upper bounds and unique potentially optimal actions are handled;
this is not merely a backward-only repeat of the first calculation.

The committed Core search_state_identity is measured directly:34035groups for
34037histories,two nontrivial pairs,zero new labels. A capture-pruned candidate
has33979groups and offers only3cooperation/1partial-WDL transfer candidates.
It is not adopted as a history quotient or a label source. No public identity,
repetition handling or production transposition table changes.

## Literal paths across different histories

Position equality is used to propose a path,never to transfer truth. For every
cooperation-UNKNOWN target,find the shortest original decisive-record suffix
starting at the identical complete Position and fitting its remaining rule
clock. This freezes165proposals. Actual target-history Core replay proves160;
5suffixes encounter repetition and remainUNKNOWN. Preparation costs16.105s;
target proof phase6.054s,6724executed suffix actions. The independent positive
reader checks6637edges/160roots in7.562s. Prefix replay/compilation are included
in phase timers but not the suffix-action counters;initial truth loading is extra.

A separately recorded method control deletes Position loops from exactly these
same165saved source suffixes,then replays targets. It proposes3937actions versus
6989raw suffix actions,executes3825,and proves161with4UNKNOWN. It also replays
6989source suffix edges to construct the shortening. The phase costs6.001s;
the initial independent reader checks3759positive edges in7.280s. Later reader
validation additionally checks that removed segments are Position loops and
that retained edges form a complete simple source path. This is fewer target
proof actions,not evidence of wall-time,player or learner acceleration. Preparation,
prefixes,source reconstruction,loading and engineering cannot be omitted in a
fair cost comparison. Original raw failures remain preserved.

One concrete rescued history is43c5e2455a85c44c516ac7cdcabf6528844e1fae35da4b77e1cfd7153b0f4e5c.
The source suffix starts atply72 and has30actions;the identical target Position
is atply86 with42remaining. At the fifth shared action,the source repetition
count is2 and the target count4:source staysongoing,target draws atply91.
Deleting recorded loops yields14legal actions and actual mate at targetply100.
A failed suffix therefore does not establish absence of another decisive path.

The other four raw failures share a single terminal full history atply68;
shortening still draws atply64. These are correlated prefixes,not four independent
counterexamples or new games. They remainUNKNOWN after the final method too.

## Recombining existing recorded transitions

The next changed premise uses only the finite union of original recorded
Position/action transitions:17681positions,23124distinct edges,75observed mate
goal Positions. No alternate successor is generated. A reverse breadth-first
pass proposes one shortest observed path for each remaining target. Its edge
book is incomplete;absence of an observed path proves nothing about the game.

Of4125remaining unknown cooperation targets,3447have no observed path and204
only paths exceeding the remaining clock.474proposals are frozen before replay,
with180s/2000proposal caps and no alternative-path retry.311reach actual mate;
163hit a barrier or otherwise fail and remainUNKNOWN. Preparation16.615s,
proof9.195s/9649actual path edges,independent positive verification7.739s/
8519edges. These311new positives account for the final5443positive labels.
They are proof paths from the original histories,not policy rollouts or training
starts. This is reuse of observed transitions,not completion of an old capped
reachable graph. All previous failed attempts stay closed.

## What the new advice changes

New Claude comment1792759763.337249 is read and qualified-adopted:keep initial
mu separate from endogenous late-history mu,freeze real E0 and two explicit
baselines,and report finite-case limits. The suggestion to sample30–50new3x3
rules is deferred to PRIMARY's sampling ownership. No AUX generator or parallel
calibration campaign is created. The cited20.444s H6verification covers one
homogeneous four-actor rule,288layouts,max_ply6/repeat2. It does not forecast
cost or truth for six-actor max128/repeat4 rules. Under a fixed five-orbit
homogeneous code there are at most31nonempty masks before any further semantic
identification;more cases require another declared factor. Layout count is not
rule-family replication. Neither30–50rules nor a middle observed base rate by
itself establishes population calibration. Do not select/refill a headline by
looking at oracle class outcomes.

No actual E0 or matched baseline was supplied at the ordinary probe. The new
pending contract requests a base-rate baseline and a board/actor-count-only
cheap baseline,with fit support,information set,source SHA,probabilities,
uncertainty/abstention and complete cost. A fitted base rate uses labels and is
not label-free information. The original exposed6/4initial split is still
5positive1negative versus4positive0negative;specificity on its leaveout cannot
be estimated. No measured FP/FN,blindness or unseen-rule gain is claimed.

For constant rule-level probabilities p(E0),q(baseline) and true prevalence r,
paired Brier improvement is(q-p)(q+p-2r). Given r in[l,u],its identification
width is2|p-q|(u-l). If p=q,further labels cannot change this paired comparison.
If p>q,E0is robustly better only when p+q<2l;when p<q,only when p+q>2u.
This is a decision frontier,not synthetic E0 evidence. Initial cooperation is
already fully known,so additional late-history proof does not improve that
headline. The first actual frozen forecasts should determine whether a further
specific certificate can change a decision. Do not continue generic truth
expansion merely to shrink a count.

There is also a concrete baseline-support issue:the original10initials all
have board_size4 and6actors. A deterministic board-size/actor-count-only
predictor has exactly one input class there. Under the same fit protocol it
has the same information partition as a constant base-rate predictor;different
outputs would reflect fitting/prior/randomization differences,not geometry
information. Declare this equivalence rather than duplicating computation. On
saved-history mu there are5actor-count classes,so this is a different baseline
question. All1192six-actor histories still have0known forkTRUE,158FALSE and
1034UNKNOWN;the1689known four-actor forks cannot be reported as initial-screen
success. These are support/count diagnostics,not newly fitted forecasts.

The new initial nonloss also identifies one minimal prospective fork query:
A(1,0)->(2,2)has value[-1,0],and its saved ply1child has[0,1]for the next mover.
A literal WIN certificate at that child would separate this action from the
known DRAW capture. The existing optional Session WIN entry is called once at
depth3/2048nodes/30s,on a different rule/history from the closed50kcontrol.
It returnsUNKNOWN at the depth budget,154nodes/0.662s,no certificate. There is
no depth extension or broader batch;initial fork remainsUNKNOWN. The shared
source field names the Core baseline;the existing proof helper's own SHA256 is
also retained. This is an AUX diagnostic call,not learner invocation or benefit.

A final existing-data closure feasibility check removes missing-action/mate
vertices and all their predecessors from the observed transition book,using
complete legal-action universes already bound at source roots. Only24terminal
candidate Positions remain and no ongoing source history lies in them. No
remaining unknown can be settled by that closed subset. The17.636s check stops
without successor expansion or an adopted negative label. It does not turn
the3447unconnected observed targets into no-mate conclusions.

## Delivery and reproducibility

Separate packet:data/leaper_explorer_saved_paths_20261023. Earlier packets remain
immutable. New data are bounded below4MiB and source/file hashes are explicit.
Run scripts.verify_leaper_saved_paths for parent proofs,all new legal-edge and
positive-path checks,recorded-edge provenance,bidirectional constraints,
repetition barriers and final views. Its final truth digest is
d129e9a87929502a19b4758a53ff4eec2084c6bb0e6e11700cc50998d374f333.
Failed path observations are not negative truth;incomplete observed edgebooks
are not closed-deadzone certificates. Final published sources include verifier/
test additions after execution;no independent prelaunch own-code commit receipt
or controlled speed comparison is claimed. Raw Slack/account data and JUnit
host metadata remain ignored/private. Research timing and publication receipts
are separate from computation timings.

Validation:138related tests pass in39.006s,including39new tests for finite Core
trees,integer-completion max bounds,history/source corruption and literal
proofs. The initial full portable reader passes in257.460s,including both
parents,recorded-edge provenance,all new positive proofs and views. Final
metadata/minimal-diagnostic checks receive a separate updated-reader receipt;
unchanged parents and negative constraint diagnostics need not be rerun for
that additive check. Early test fixtures incorrectly mixed legacy and semantic
compiler identities,and one used a3x3toy at a4x4admission boundary;both fixtures
were corrected while keeping the real rule admission strict. Failed test
receipts stay private. No failed run is relabeled as a successful experiment.

Six additional actual-case corruption guards also pass. The final additive
reader passes in68.276s,including the two immediate-win/source-outcome cases.
Session d19acb3d-cef7-4958-bc85-ac27053ca24b ends normally at safe_checkpoint
with3846.034857confirmed effective seconds(64.101min),six evidence-bearing
intervals and a successful session finish. Publication/transport are excluded.
Next ordinary probe seeks actual E0/target/baselines;independent backups are
retrospective tactical scope of known forks and failed-path barrier analysis.
