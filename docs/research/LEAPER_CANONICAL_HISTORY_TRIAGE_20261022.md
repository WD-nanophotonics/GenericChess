# Canonical Leaper histories: deadzones and useful decisions

DEV_AUX consumes PRIMARY's frozen canonical rules and trajectories. PRIMARY
retains rule generation, forward screening, inverse-design interfaces and
product defaults. This is post-hoc truth and learner diagnosis; no forward
campaign, new game, training start selection or default change is performed.

## Source and counting units

Source and current shared infrastructure are sandbox
`e8f4abf94bde7b6de1ab1a9acc3abfd24533c002`,
`docs/research/data/leaper_forward_design_20261022/observations.json.gz`.
Its compressed SHA256 is
`65cbda6e861249f04914511f5bcdd1e83233879c276236df7caac1f7d5c0b761`.
Rules, search, terminal/history and session code match that mainline; the separate learner uses the existing
public pure-material adapter from sidemission `9dee9f9276395f30d4cac724b99db9294e71cd79`.
No uncommitted PRIMARY work or role state is imported.

The closing fetch finds sandbox `44d346484b8927309bf3437b99d4816a36fd3cf0`.
Its Core/rules/search/session package has no delta. The maintained design,
portrait and forecast scripts and two test files are reused byte-for-byte:
actual frozen world counts, missing-role utility bounds and forecast helpers.
No PRIMARY forecast/generator campaign is rerun. Experimental observations
remain bound to their executed e8f4 source, not relabelled as new measurements.

The packet has 540 record references: 480 pilot/repeat executions, 40 material
controls and 20 capacity controls. The first 480 contain 331 distinct complete
GameRecords, as PRIMARY already reports. Across the entire packet there are
369 distinct complete records, 35,648 visits on those records, 34,037 distinct
complete GameStates and 17,520 distinct Positions. These are different counting
units, not independent sample sizes. Replaying all 369 distinct records through
GameSession reproduced their full final records, states and terminals.

All these rules have 4x4 boards, K+A+B per side initially, plain D4 Leaps,
capture removal, no drops/promotion, repetition-four draw and rule clock 128.
Actual `max_ply` is a rule draw here. Observer time/state caps remain UNKNOWN.

## Complete low-material observer

All ten <=3-actor closures complete in 373.484 seconds: 112,124 graph vertices
summed across distinct rule fingerprints. All 21,438 naturally observed distinct
low-material histories receive labels. The observer finds 111 histories with
actions of different WDL and 16 with an inferior recorded action. Only mask
pairs [1,3] and [3,8] contribute these forks: respectively 30/81 forks and 6/10
inferior histories. The other eight rules' observed low-material histories are
structural deadzones, not merely difficult search positions.

The structural test is stronger than minimax DRAW: no decisive terminal is
reachable even if both players cooperate. Its set is forward closed. For
non-dead histories, the already scoped history argument replaces incoming
edges to previously thrice-visited nonterminal Positions with draw sinks.
Complete reachability attractors give decisive ranks; a label is decisive only
when its rank fits the remaining rule clock. A winning strategy strictly
decreases rank and cannot revisit a future vertex or raise an older count <=2
to four. Terminal precedence remains Core's. This is specific to these
history-independent plain-Leap transitions, not a general Position quotient.

At this low-material stage alone, 243/288 max-ply record references have entered
a proven structural deadzone. On distinct complete records this is 156/195.
Conversely 12 max-ply references (eight distinct complete records) contained a
mover-relative forced WIN and an inferior decision before ending drawn.
These groups need not be disjoint: a missed win can subsequently enter a
deadzone. Unclassified higher-material prefixes are unresolved, not winnable
by default. First *proven* entry can be later than true entry.

The paid search receipts contain 6,407,363 nodes across 10,104 AB calls. Using
low-material labels alone, 3,228,790 nodes/4,786 calls occur after proven entry.
This measures paid work in these frozen trajectories. It is not measured saved
runtime: the observer has its own cost and is not deployed in the player.

## Four-actor truth and public decisions

The four-actor observer uses every natural four-actor history, grouped by committed
fingerprint and ordinary inventory, and reuses the complete low-material
graphs. Its frozen total limit is 1,200 seconds, 120 seconds/150,000 vertices per
component. All 56 components and all 9,573 distinct histories complete in
783.297 seconds. Component-summed vertices are 1,898,508: 625,112 imported
entries and 1,273,396 new Core expansions. These sums measure work and overlap,
not distinct states or independent samples. No old batch is continued/refilled.

There are 1,689 four-actor WDL-fork histories and 176 with an inferior recorded
action. Combined with <=3 actors: 31,011 labelled histories, 1,800 forks and
192 inferior histories. The 3,026 remaining distinct roots have five/six actors
and remain unresolved at this stage.

| Actual recorded controller | Labelled reference visits | WDL-fork visits | Inferior choices |
|---|---:|---:|---:|
|AB|7,478|1,331|24|
|RNG|30,881|574|216|
|FLOOR|6,882|132|57|
|Static adapter|908|170|3|
|M0|818|124|7|

These are different endogenous trajectories, with repeated references retained,
not a policy trial or independent win-rate estimate. At <=3 actors alone AB
has zero inferior recorded choices and almost exclusively deadzone visits;
that does not establish its adequacy at four actors.

The combined truth identifies proven deadzone entry in 263/288 max-ply
references, or 173/195 distinct max-ply records. Conversely 65 references/42
distinct records contained a mover-relative WIN and a subsequent inferior
decision. Missing a win and subsequently entering a deadzone can both occur.
With four-actor annotation included, 4,113,305 original AB nodes/6,274 calls
are after proven deadzone entry. This still measures cost, not acceleration.

Sixteen preselected SHA-ordered four-actor error histories receive independent
all-defense proof attempts: 13 complete (2,246 literal Core nodes), three hit
the 5,000-node cap (5,001 charged visits each) and remain unproved by this
certificate check. The graph labels and the limited independent proof coverage
are separate evidence. No proof is refilled.

## Public price/depth calls and ties

The 900-second query batch closes with 28,538/57,438 recorded calls and
3,093,404 nodes: 28,536 full requested-depth receipts, two cancelled calls,
28,900 unattempted slots. All six conditions complete on 4,756 histories;
4,817 source histories lack a complete contrast. Every whole-source
conservative quality interval crosses zero.

| B/A | D2 inferior choices | D4 inferior choices |
|---|---:|---:|
|1/2|54|34|
|1|55|36|
|2|56|37|

D4 improves 19--20 single-step WDL choices over D2, with no reverse change in
this subset, at about 8.6 times the nodes. This is not an equal-work strength
comparison or acceleration result. Price effects occur at only three histories,
all in [3,8]. Literal Core D2/D4 argmax controls complete in 4,473 nodes:

- `adb75...`, ply17: B<1 has only DRAW best actions; B=1 mixes DRAW/LOSS;
  B>1 has only LOSS. The current equal-price tie choice finds DRAW.
- `d4dcf...`, ply7: D4 at B=1/2 has only WIN best actions; B>=1 mixes WIN/DRAW
  and currently chooses DRAW. D2 at B=1/2 still has WIN/DRAW ties.
- `f7790...`, ply17: B=1/2 still mixes WIN/DRAW but currently finds WIN;
  B>1 has only DRAW. Lower B is not tie-independent here.

For `adb75...`, a separate 2,664-node actual-history all-defense certificate
binds the **actual B=2/D4 intervention**, not a historical RNG/FLOOR action.
The opponent can force WIN. The B=1/2 capture enters a closed 4,264-Position/
18,720-Core-edge subgame with no decisive terminal. Its selected LOSS versus
DRAW contrast therefore has independent literal evidence. Rebinding the bad
proof to the safe action is rejected. The older natural corpus has an
opposite-direction price effect under its own conditions; neither is an
intrinsic piece price.

## Five actors and existing zero-training priors

The independent 900-second feasibility batch reuses applicable complete
four-actor graphs and visits inventories round-robin across rules. It closes
in 901.772 seconds including durable partial saves: eight complete components,
five incomplete and 27 unattempted out of 40. It labels 379/1,834 histories,
including 114 WDL forks and 37 inferior histories. The 1,455 missing histories
remain UNKNOWN. Partial graphs stay ignored and closed, without continuation.

All 5,306 public queries on the 379 available histories complete D2/D4 across
seven positive price-cell representatives: 572,943 nodes/116.997 seconds.
At B=1, D4 improves seven choices and worsens two relative to D2. Deeper is
not uniformly better. This subset is conditioned on graph cost/completion.

| B/A | D2 inferior choices | D4 inferior choices |
|---|---:|---:|
|1/4, 1/2, 3/4|22 each|18 each|
|1|24|19|
|3/2, 2, 4|25 each|19 each|

The same driver then evaluates PRIMARY's frozen empty-board-mobility ratio
and Static board-price ratio, in the same pure-material learner caller with
equal capture ordering. Static positional dynamics are excluded. All 379
histories/both depths are included: 1,234 new calls/134,054 nodes and 282
exactly reused complete grid receipts, not 1,516 new calls. Both batches finish
below their separate 120-second caps.

Both priors make 22 D2 and 17 D4 inferior choices, improving two over uniform
at each depth without reverse changes. Despite different numerical prices,
their actions, PVs, features and nodes match in all 758 paired conditions.
They reach this observed positive-grid served-policy envelope, including the
best rulewise constant choice. This is an exposed diagnostic of preexisting
priors, not prediction, held-out validation, TD learning or a universal
representation bound. Whole-source bounds [-1454/917,208/131] cross zero.
No model or experiential opening is selected using oracle labels.

With five-actor annotation there are 31,390 labelled histories and 2,647
unresolved five/six-actor roots. Deadzone entry explains 263/288 max-ply
references (173/195 distinct records); 73 references/47 distinct drawn records
had a mover-relative WIN. These groups can overlap. Original AB work after
proven entry is 4,118,425 nodes/6,284 calls, an observed cost, not saved time.

## Why local gradients cannot screen useful prices

A separate zero-query analysis joins the previously published 1,904 five-actor
receipts to their exact branch labels. It retains the original cost-conditioned
136/244-history subset and all 108 missing histories; it is not a new test set.

At B=1, D2 has 44 zero-B-Jacobian histories, 81 nonzero and 11 terminal PVs;
D4 has 46 zero, 71 nonzero and 19 terminal PVs. Four of the five D2 benefits of
B=1 -> 1.5, and both D4 benefits, occur at a zero local B Jacobian. Thus six of
seven history-depth benefits would be missed by a nonzero-gradient filter.
The seven contrasts are not seven independent histories.

The Jacobian differentiates the selected literal leaf value, with fixed A=1.
A finite price change can switch the minimax branch even if the original leaf
contains no B contribution. Conversely a nonzero Jacobian need not imply any
WDL improvement. No TD residual, eligibility trace or actual update is inferred
from these query receipts. Other experiences can still update B, so this is
not a proof that TD cannot learn. Oracle diagnostics remain outside training.

## Verification, limits and next action

The initial observer failed before graph expansion because schema LeapAtom
objects have no `.kind` attribute. The corrected attempt uses their actual
type; the failed source/log remain local. A post-hoc script also initially
assumed terminal PVs carried feature vectors; it now preserves their distinct
terminal category. Neither error changes source games or fills a missing slot.

The compact verifier passes 369 complete record replays/35,648 actions and
binds 31,830 visited roots to full GameStates. It checks query arithmetic,
missing bounds and exact prior reuse; replays 29 original proofs/2,518 nodes
plus the separate price intervention; rejects four proof corruptions and a
wrong intervention binding; and checks the clock, full argmax, safe closure
and selected literal PVs. It does not re-solve the full graph census. All 99
initial focused tests and 67 closing interface/learner tests pass; they overlap.
Confirmed effective research is 4,987.525 seconds (83.125 minutes), excluding
the closing infrastructure import, administrative publication and transport.

An intermediate join incorrectly attributed any inferior action at a shared
history to every record visiting it. The final analysis uses each record's
actual action, and the verifier reconstructs its original hash and full path.
Before/after outputs remain local; source games and graph labels are unchanged.

Next inspect the 17 D4 failures shared by both priors and every tested positive
cell: distinguish strictly bad argmax sets from mixed-WDL ties before choosing
a learner/evaluator hypothesis. Use saved histories/graphs and bounded literal
Core controls. Do not reopen closed batches, oracle-select training starts,
or duplicate PRIMARY's generator/forward screen. No trained-model, population,
held-out or product-default winner is established.
