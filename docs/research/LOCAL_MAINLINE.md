# DEV_AUX current research

## Current user direction

The formal2026-10-21 [Leaper direction](LEAPER_DIRECTION.md) supersedes the
Chess-first TDLeaf strength-panel priority. Study small deterministic Leaper
worlds, exact WDL/action quality, composition-conditioned useful material
parameters and the mechanisms of learning. Do not assume an intrinsic price,
monotonicity, additivity or unique identifiable ratios. Experiential learners
must not receive reference answers except explicit supervised controls.

Use the committed mainline rules, Core/GameSession and public search. The
executed package baseline6ea35571272708f7e220fa3868f2ca1a4d0cf7ca is unchanged
in latest sandbox3ddbf9988e680d473ebe5d90b2a66ec430993df5. Its maintained
semantic_probe_cost capture-only option is synced exactly; this research still
uses q0. All238shared package files match current mainline. AUX-only package
files remain learning/incremental.py and learning/mainline_search.py. No other
role state, unpublished work, defaults or tasks are adopted.

## Actual first results

Detailed definitions, costs, counterexamples, limits and reproduction are in
[LEAPER_FOUNDATION_20261021.md](LEAPER_FOUNDATION_20261021.md), with one curated
numerical file. Large raw histories remain ignored; historical assets stay inGit.

* Vanilla Core forbids Anchor capture and enforces royal safety. The initial
  benchmark explicitly uses mate/stalemate,3x3,oneAnchor+oneordinary each,
  eight-neighbour leaps,no drops/promotion/pass/aux/claims,remove captures,
  repeat2/rule-ply6draw. It is not a capture-Anchor prototype or old-game adjudication.
* ALL288fresh both-Anchors-safe layouts:80first-player wins,8second-player
  wins,200draws;91712complete-history contexts,1768Positions(include turn),
  11328contexts with different childWDL. ExistingRuntime reference agrees on
  every root action;one full416context transpose check preserves transitions,
  terminal and repetition histories.
* On the SAME288roots,publicD1/D2/D3/D4/D6make50/13/1/0/0WDLdecisionerrors,
  costing1456/4405/9316/15642/33754nodes. Finite rule only,no generaldepth claim.
* OrthogonalA/diagonalB,oneordinary each:all79184/81736AB/BAH6contexts draw.
  EightH10starts also allD. Exhaustive static3/4/5board censuses contain no
  mate,including captured-ordinary configurations. The radius-two locality
  argument explains why board enlargement alone cannot fix this scoped world.
* One actual legal shared first move mates inAA,but replacing the defenderA
  with four-targetB allows a capture and exactDraw. Removing its blocker from
  a separate legal fresh start also draws. Quantity and geometry interventions
  are explicit,with rebound rules and complete histories;no universalprice follows.
* ReplacingBgeometry by King-like leaps restores genuinechoices. On64selected
  exact-choice contexts,positive price intervals have identical actions within
  tested pairs. D2price.25to1.25fixes5WDLchoices;one SAME-price D1toD2choice
  worsens. No heldout/population or unconditional depth monotonicity claim.
* 32experientialD1episodes moveB.25to.322337,but all74candidate queries still
  select the initial-weight action.32D6episodes have78terminalPVs,zero material
  gradients/updates despite4nonzeroTDerrors.64histories/304reference labels/
  64TDcalculations checked5.55e-17;oracle labels were observer-only.
* SAME6actor occupancy:both-sideABcoexistence has1151contexts,14mates,26genuine
  choices;BBcontrol is degenerate.416publicqueries across4positivepricepoints
  find one actionchange with noWDLchange,not a price winner.
* SAME8actor occupancy:ABAversusABC(Ctwohorizontal leaps,extraA replaced on
  BOTH sides) is legal and solved:1195/685contexts,35/4mates,50/6genuinechoices,
  rootbothDraw,0.118/0.062s. This next composition case has begun,not only planned;
  no changedA:Bprice-region conclusion yet.

## Next executable work

Main:do A:B useful policy/value regions change between matchedABAandABC?
Use the saved exact rules/root action tables and maintained constructor;fixC
coefficient and compare public q0 choices against exact childWDL at bounded
common legal histories. Distinguish changed action,changed WDL and tied choices.
Start with the costed finite case,not a large grid or an unbounded solver.

Backup1:does the six-actorABmechanism persist at a second declared legal layout?
Use a small symmetry-qualified counterexample or matched fresh start;do not
count symmetric roots as independent rules or fit a ratio to the observed winner.

Backup2:reuse task2620 frozen histories without new searches,checking what its
seed/order schedule permits attributing to weights. Its old caps/UNKNOWN remain.

## Old evidence retained; stale queue retired

The old opponent-control producer was safely stopped on direct user redirection:
exit0,STOPPED_USER,999.223289s/2079852nodes.132histories/5802queries/116updates
checked8.88e-16. One condition16slots=3W11L2UNKNOWN,bound[-5/8,-3/8];other32
planned slots missing. Do not restart/refill it or launch the old prepared D3,
lambda/selfplay or natural-rule backups. Configs/models/failed and partial data
are preserved. Existing TDLeaf is a later mechanism tool,not the restored priority.

Task2625reuse recovers ALL4historical training/evaluation journals byte-for-byte
from4d0fd6d4279e361927368ee656c9727d266ffb74.86positive/33reversepairs verified;
37/17first split at the fixed foe. All190foe-first splits have identical prior
history/weights/complete rootvalue/request. Frozen code adds endpoint+1toordering
seed,so this is not a pure weight intervention.24selected full-history replays
pass;completePVactionpaths/allalternativevalues were not saved. No rerun,oracle
optimality or independent holdout is claimed. Task2620histories remain at
e6368f3c67ad386d5f10dac81355175cc05a4abf;their location,not a new full audit,was checked.
Earlier Chess/Generic/natural-rule results remain in INCREMENTAL_TDLEAF.md andGit.
Task2636audit/registration machinery stays retired.

## Recovery, timing and delivery

Role DEV_AUX/sidemission only;PRIMARY andDEEPSEEK independent. Preserve active
session UUID/origin/confirmed work,all scoped stops and all old caps. Current
existing app heartbeat was read back ACTIVE/90minutes/samechat;PRIMARY's latest
published record reports a separate user cadence change. This turn did not
modify it. Preserve that existing schedule under the latest user instruction;
earlier hourly receipts remain historical,not an automatic schedule repair.

Normal research accumulates60effective minutes,proceeding toward90;admin,offline
and idle are excluded. At>=120expected minutes first get explicit Chat mailbox
scope/budget assessment. Every recovery reuses latest committed infrastructure.
Read/review Chat/Claude asynchronously;no Dot waits or other-role task adoption.
The old uncertain Slack send is not resent. Before any new authorized report,
push reviewed own work and verify full origin/sidemission SHA. UNKNOWN neverDraw.
