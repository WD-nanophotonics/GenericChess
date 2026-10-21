# DEV_AUX current research

## Route and infrastructure

Use the same fixed-scale classical TDLeaf/search-bootstrap learner, Chess first
and then complete Generic rules. Random/uniform initialization; no human material
priors. Actual rule W/L/D evaluates strength; search targets train. UNKNOWN and
missing remain unresolved. Full rules/history stay authoritative even though the
material approximation is intentionally limited.

User2026-10-21 requires committed sandbox infrastructure as the current baseline.
All238 shared package source files now match latest published sandbox
`6ea35571272708f7e220fa3868f2ca1a4d0cf7ca`. Its completed-root-win option and
public probe interface/tests are reused exactly; the option stays defaultfalse.
The common research_record uses strict GameRecord serialization. AUX-only
package files are `learning/incremental.py` and the thin
`learning/mainline_search.py` receipt adapter. Future Generic episodes default
to public mainline AlphaBetaPlayer with literal q0 PV features; the randomized
search remains an explicit historical/Chess reference. Actual moves and records
use GameSession. No parallel Core, no uncommitted
PRIMARY imports, no other-role state writes. Each hourly recovery checks and
reuses newer committed infrastructure and relevant results.

Native rebuilt; historical public-path full suite3969passed/1skipped in330.39s;
current6ea35571 search/learner/history affected regressions pass167tests.
Defaultlambda.95 remains. Default engine,
UI and deployed weights are not independently selected by DEV_AUX. See
[INCREMENTAL_TDLEAF.md](INCREMENTAL_TDLEAF.md) for exact callers/results/limits.

## Saved evidence and interpretation

| Study | Finite result | Limit |
|---|---|---|
| task2594, Chess | TD(.95)-initial mean+.390625 over256pairs | Four seeds use different root blocks; not independent replication. |
| task2620, frozen Chess |1536slots,1267actual/269UNKNOWN/0missing; TDLeaf-initial bound[29/384,111/128] | Other contrasts do not identify a method winner. |
| task2625, four small Generic rules |1024slots,980actual/44UNKNOWN; bound[61/512,149/512] | One rule slice spanszero; not full-domain strength. |
| Closed semantic/no-progress pilots |95/128 and46/128eval slots; bounds[-83/64,69/64],[-3/2,25/16] | Missing/UNKNOWN and old caps remain; no refill. |
| Natural rule1, D2vsD1 |32slots,27mates/5UNKNOWN; depth-policy gain[3/8,1] | Eight families; more realized work atD2. |
| Rule1 TDLeaf.95, uniform D1foe |70train/65updates;64eval/0missing;29W1L2U vs28W4L; gain[1/16,3/16] | One exposed rule/16families; narrow opponent condition. |
| Rule1 frozen trained-initial direct iterativeD2 |16slots,4W9L3U; trained payoff[-1/2,-1/8] | This condition disfavors trained; not an isolated opponent intervention on the old run. |
| Rule1 maxD3calibration |8slots,all node-capUNKNOWN | Foe actually completes34D3/38D2/3D1queries; no strength anchor. |
| Rule2 TDLeaf.95, uniform iterativeD2foe |80train/77updates at2Mnodes;64eval/0missing;8W19L5U vs23W6L3U; gain[-9/8,-5/8] | No improvement or weight adoption; baseline already wins23/32. |
| Rule2 TDLeaf1, fresh seed27190, same foe |75train/74updates at2Mnodes;64eval/0missing;20W10L2U vs9W16L7U; gain[1/4,13/16] | Own-initial gain only; different seed/initialization prevents a lambda-method winner. |

These are UNKNOWN-completion bounds, not confidence intervals or population
claims. No learned vector is a product default. A changed action, coefficient,
PV rank, terminal rate or node count does not establish value. The original
660.55s/UUID/task2620 recovery and later completed segments remain historical;
this session does not inherit their time. Detailed old reports remain in Git.

## Current work and next decision

The lambda1 run is closed:139full histories/4425queries and75updates independently
checked to2.22e-16;931.657s elapsed. Its11censored training episodes have no final
reward. Defaultlambda.95 and all closed studies remain unchanged.

One previously prepared fresh depth/work control has completed on rule2,
seed27191:two opening families,both candidate colors,maxD2/maxD3 candidates,
uniform1weights and a fixed uniform iterativeD2foe. Both modes have the SAME
16384query/240000game/90s,H128 allowance; overall1.92Mnodes/900s,eight slots.
It changes the resource premise and uses fresh histories; it does not resume
old60000node D3games. All8slots finish: D2=2W2L,maxD3=2W2node-capUNKNOWN,
finite gain[0,1]. D3pays675191nodes/129.716s versus55864nodes/20.724s atD2;
39D3/20D2candidate queries and290919partialD3nodes are retained. No strict
gain,per-node speedup,equal-compute or population claim; no topup.

The coupled comparison is now closed atsourcee4c8c193,seed27192:129train episodes,
4Mtrain nodes,96eval slots/79mates/17UNKNOWN/0missing. Lambda.95=10W14L8U,
lambda1=24W5L3U,ONE initial=11W15L6U. Own-initial bounds[-7/16,7/16]and[7/16,1];
lambda1-.95=[3/8,17/16],shared initial cancelled exactly. A strict finite-condition
advantage,not a population or initialization-robust method winner.225histories/
7657queries/129updates checked within2.22e-16;6492852nodes/1715.759s,exit0.

The preselected public-mainline pilot is closed:source0ac74767,lambda1,27193,
2Mtrain nodes/57episodes/54updates,35actual/22U;two already-terminal starts kept.
Eval2Mnode cap ends46of64slots,23actual/23UNKNOWN/18missing; trained6W4L13U,
initial5W8L10U,9missing each. Bound[-9/8,23/16],no utility claim or topup.
103histories/2481queries/57updates verified2.22e-16;687.302s,exit0. Actual public
search execution is established; different policies/histories prevent a speed
or strength comparison against the reference studies.98focused tests pass;
full default-path regressions pass3969/1skip before the next producer.

The fixed direct control27194 is also closed:64of64slots,16W5L43UNKNOWN,
payoffbound[-1/2,27/32],0missing,460.422s/2919897nodes.42game-node caps and one
unfinished first layer remain;no strict gain or weight adoption.64histories/
1157queries checked;1065D2/91D1fallbacks/one incomplete query. No new training.

The bounded TT/full-PV check is complete:24calls0.980s,four saved roots.
WarmD2reuse pays2nodes,but warmD1retains deeper scores and3of4exported PVleaves
do not match. Keep fresh per-query players,no persistent cache/model epoch risk.
The next16coldD3queries18.597s show existing zero-price capture/killer/history
ordering completes4of4versus3of4,three commonD3values unchanged. TTalone gives
no cold node reduction here. Source00e39117 reuses existing TT/order perquery;
82targeted learner/runtime tests pass. No duplicate search or universal speedclaim.

The predeclared three-seed panel is closed atsource
00e391172f63c7f6259a9e91d1d4f2060be5a3e8/bffe:lambda.95,public orderedD2,
uniformD2training foe,then frozen own-initial direct games. Original4200s/27M
caps;actual4200.124380s/8983167nodes,exit0,GLOBAL_TIME_CAP.321train episodes/
307changed updates;308of384direct slots,201W90L1D16UNKNOWN/76missing.

| Seed | Direct W/L/D/U | Missing of128 | Payoff completion bound |
|---|---|---:|---|
|27195|39/46/0/4|39|[-25/64,9/32]|
|27196|93/16/0/7|12|[29/64,3/4]|
|27197|69/28/1/5|25|[11/128,71/128]|

Pooled planned-slot payoff[19/384,203/384] is positive for these three finite
conditions. Seed1/2intervals are disjoint;this is combined initialization,
training-root and resource-conditioned variation,not populationconfidence,
lambda superiority or product-weight selection.629full histories/26353queries/
321TD calculations independently checked,error1.33e-15. Original producer's
summary stops before its final seed entry;all103last-seed rows are retained and
independently reconstructed,not rerun or inserted into that original summary.

The selected fresh-rule backup also executed after6ea sync,sourceb83eaab1:
generator2026102103(firstattempt),episode27199,85plies/85queries/20149nodes/
8.431s,actualplayer0win,18drops/4promotions.43observations produce a nonzero
update with independent arithmetic error0;full history replays. One trajectory
shows common-path feasibility,not strength or full-domain coverage.

Next question:does selfplay training beat fixed-foe training under one coupled
fresh initialization/root schedule? This control is designed,not run:
freshseed27200,two300s/800000node arms,then16families/bothcolors direct arm play
under300s/1.92Mnodes;whole900s/3.52Mnodes. Same learner/publicD2q0,no new search,
no old missing-slot refill,no assumption of50percent or population power.
Use existing opponent=model alias with episode-frozen weights for selfplay.
HigherD3anchor remains a separate bounded alternative,not a prerequisite.
Q1 remains unconnected because no q continuation is exported for TDLeaf features.
Expected>=120min needs Chat mailbox scope/budget assessment.

Closing bffe1e4b findings were read:Native service throughput required aligned
physical PV/work; extra D2 completion did not establish W-L benefit. Same RNG
seed across action representations did not preserve physical histories. Reuse
these limits,not PRIMARY's probe task. No q tail or Native speed claim is added.

## Mainline findings to reuse

Read PRIMARY's fixed6a4f886 andd2da9705 research records, rather than recreate them:
D1invariance cannot filterD2learning, selected-PV rank is not utility, conditional
improvement need not improve an opening policy, and history can change goals
under aliased material trees. The newer custody/ordering result distinguishes
coefficient identity, represented leaf value, ordering, paid work and actual
outcome. Our ordering remains material-independent. Do not infer universal
intrinsic prices from the learned coefficient vector or patch negative prices.

Existing shared capture-only qsearch and richer encoders are future candidates;
first inspect their real caller/limits and PRIMARY's current results. Do not
implement another qsearch, add coverage gates or launch a feature/solver campaign
because the present material learner has mixed finite outcomes.

## Scope and durable recovery

Task2636's unregistered16rule audit/receipt framework is retired. Its frozen
inputs are history,not a continuation queue. No registration/crosswalk gates
or old closed payloads are restored. Cleanup and unique private recovery are
recorded in docs/operations/CLEANUP_20261021.md; prior detail remains in Git.

Chat/Claude advice is reviewed asynchronously. Latest direct user reuse policy
supersedes earlier deferral of Core imports. Defer MCTS/Elo/SPRT and broad
feature/solver changes; reject UNKNOWN adjudication/imputation. One uncertain
old Slack send remains unconfirmed and is not resent. Before every new authorized
message,push reviewed own work and verify the full remote SHA. Cadence remains
ACTIVE hourly in this chat. PRIMARY and DEEPSEEK remain independent.
