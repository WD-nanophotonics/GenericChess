# Price, rule context, q policy and ordering — 2026-10-22

The earlier finite Unit advantage does not extend to the new2048-node/q0
envelope: Unit minus Static is[-1/6,1/12]. Fullq1 is strictly worse than pureq0
with Static prices on this cohort,[-5/12,-1/6]. Neither result selects a generic
price or search default. New capture-onlyq1 work fails its cheap cost screen;
a check-onlyq0 candidate is ready for a separate whole-game utility test.

## Inputs, policies and interpretation

The12configurations were frozen and prepared before this segment's fitness:
seeds202610221100–202610221111,4/6/8boards, classic-like/free-random setup and
bilateral/no movement symmetry. All12generated; none was replaced. Opening-win
preference is OFF. Two initial positions, worlds5and6, have immediate Core wins
and remain in every denominator. Twelve distinct full rule/input records do not
prove12behaviorally inequivalent games or an independent population sample.

This is the generated legacy-movement subset, not a redefinition of the complete
generic target. All declared/future types, promotion, drops, auxiliary fields and
relevant history are retained. No human labels, held-out Xiangqi data, learner,
AUX checkout, extra worker or product default was used/changed.

Static is the existing complete rule-derived profile. Unit uses1000CURRENT-board
and900BASE-hand prices for nonanchors, preserving proved-inert hand zeros;
anchors and promotion gains are zero. Existing dynamic weights2/5/3 stay on.
Price contrasts use common Static material ordering. G alone replaces those
ordering methods with Unit while holding the Unit leaf fixed. TT/history ordering
remains endogenous. Every actor starts a fresh Player/TT per game; its own TT
persists within that game. Disk caches are OFF.

Whole-game calls use maxdepth64 and2048total main+q visits, no query deadline,
q-hard8. Pure configured q0 with check-only OFF skips q entry; it is not the
ordinary-q0 reserve inside a positive-q first iteration. q1 requests ordinary1,
with the existing first-iteration reserve and mandatory-check handling. Actual
completed depth/source/control reason is retained, including depth0immediate wins.
Caller cap96does not replace the real512-ply rule. Whole-run caps are cooperative
checks between bounded work units; the final atomic call can cross the cap.

Utility is+1win,0actual draw,−1loss. Unfinished/no-contest/ineligible/missing slots
have[-1,1], never an imputed draw. Effects average the24role frames. One observed,
eligible Static self game supplies opposite role utilities; its physical costs
are not doubled. Distinct continuing policies have independent UNKNOWN tails,
even for identical96-ply records. No Elo, SPRT, population CI or scalar-q/WDL
correctness follows from these finite bounds.

## Executed work and retained limits

| Batch | Actual / planned physical games | Player / FLOOR returns | Producer seconds |
|---|---:|---:|---:|
| Pureq0 price, fixed Staticq0 |36/36|1212/0|636.453|
| q1 price cells, fixed Staticq0 |48/48|1741/0|1054.805|
| Pureq0 price, fixed FLOOR |48/48|382/363|197.380|
| Unit leaf, Unit ordering |24/24|787/0|411.701|
| Capture-remove price, fixed Staticq0 |28/36|1661/0|1800.362|

That is184actual games/192planned,5783Player+363FLOOR returns. All6146physical
history plies and17262literal PV edges pass the public-copy Core reader. The
additional48cold Player returns are separate;24pilot baseline views are exact
reuses, not new queries. Their141literal PV edges and the six finite D2 references
are qualified separately. This is shared Core qualification, not an independent
engine or a full-game solver.

The remove run reached its original1800-second cap. Eight slots were unattempted;
one attempted game stopped at65plies;14retained physical games are ongoing,
including that capped game. No cap, seed or slot was refilled. Other four batches
completed all planned games. No game had a fallback or Native operational failure;
there were no game setup/runtime exceptions. Preparation diagnostics are separate:
a mistaken physical-position assertion included the fingerprint that must change
under a changed RuleSet. Its12failed preparations were privately retained before
checking all remaining physical fields, distinct fingerprints, identical initial
actions and board/promotion prices. No product expectation was changed.

Producer wall, paid query time and residual setup/recording/other time are distinct
in summary.json. Concurrency limits wall interpretation. Total node budgets do
not fix semantic pushes, classification work or future cost. No claim of full
continued-game cost dominance is made.

## Finite effects

A=Staticq0/Staticorder; B=Unitq0/Staticorder; C=Staticq1/Staticorder;
D=Unitq1/Staticorder. Their fixed foe is A. E/F are Static/Unitq0 against the
existing FLOOR policy: first immediate terminal win, otherwise seeded random legal
choice. G is Unitq0/Unitorder against A. All source/mask/cost records are included.

| Contrast | Finite effect |
|---|---:|
| B−A: Unit leaf atq0 |[-1/6,1/12]|
| D−C: Unit leaf atq1 |[-1/12,5/12]|
| C−A: q1−q0 with Static leaf |[-5/12,−1/6]|
| D−B: q1−q0 with Unit leaf |[-1/3,1/6]|
| (D−C)−(B−A): price×q |[-1/6,7/12]|
| D−A: Unitq1 whole policy |[-1/4,0]|
| F−E: price against FLOOR |1/24|
| (F−E)−(B−A): opponent×price |[-1/24,5/24]|
| G−B: Unit material ordering at Unit leaf |[-1/6,1/3]|
| G−A: whole Unitq0 policy |[-1/12,1/6]|
| Remove-mode Unit−Static |[-23/24,19/24]|
| Remove-price effect minus pocket-price effect |[-25/24,23/24]|

Exact coefficient bounds are independently checked by endpoint enumeration and
public analysis replay. Leave-one-configuration-out and descriptive opening-win
exclusions remain diagnostics; the primary12configuration estimand is unchanged.
The changed generator/search envelope does not isolate an opening-filter effect.

Nineteen of24B/Apaired trajectories diverge. Six resolved outcomes reverse in
worlds2,7,8, with opposite seat effects cancelling within each rule. Aggregate
non-identification therefore does not mean unchanged behavior or unlearnability.
Adding Unit self games solely to measure the role-balanced two-policy opponent
interaction would add no utility information: both self means are zero and the
reverse direct matchup is the same zero-sum observation. The third FLOOR foe
was used instead. This algebra says nothing about missing execution eligibility,
per-seat questions or unmeasured self-play costs.

G improves one resolved loss to a win, but its three UNKNOWN tails and B's three
tails remain independent. All13censored pocket source games still contain10–30
nonanchor board pieces; one has empty stock. The old two-King closure does not
apply. Conditional on the validated512rule clock and one bounded query per ply,
G−Bcomplete own-counted-node cost lies in[-2529270,2582538]. This is a conservative
node-only continuation bound, not wall/primitive/total-match cost or extra play.

## Mechanism without turning proxy scores into labels

All six resolved Staticq1/q0 outcome-change roots were retained, including the
one improvement. Twenty-four fresh cold controls use the exact full histories,
q0/q1 at2048, q1 at8192 and a complete D2q0 reference. Five original paired
returns have the same completed depth. Thus the negative aggregate cannot simply
be described as failure to reach the same nominal depth.

The independent Core D2 reference visits7962edges. Every original q0 choice is
D2-optimal there; every original q1 choice has a lower D2q0 value. Yet the world8,
role0q1 choice improves the actual outcome. The proxy gap is not a WDL error or
a training gate. All12selected actions have no immediate opposing mate and have
verified counterexamples to a forced win within three plies. That does not make
them losing or nonwinning in the full game. The original WIN3 early exit did not
by itself complete the immediate-loss test; the independent reader enumerates
that separately. Larger coldq1 budget recovers the originalq0action on only one
of six roots; no extra-budget whole-game outcome is claimed. Cold/warmTT effects
remain explicit.

Only capture custody changes in the12remove variants. Initial physical positions,
actions, current-board and promotion-price tables match; full RuleSet fingerprints
must differ. BASE-hand prices correctly reflect inert remove stock, so complete
price profiles are not asserted equal. Twenty-four of28available trajectory pairs
diverge. Four diverge before any real capture, including two initial turns,
while full current physical roots/actions and leaf scores match. Future reserve
resources and legal continuations differ. This is scoped planning context across
two RuleSets, not a same-RuleSet state alias or proof that board prices are
impossible. The broad censored capture interaction identifies no utility sign.

The latest saved Chat suggestion was also tested cheaply: exact full-rule/history
joining matches10of34old first divergences to existing two-turn scans; both chosen
actions remain UNKNOWN in all10. The other24have no exact saved scan. Stop that
join without repeating the501312-edge scan or creating a solver/learning gate.
AUX's separate scientific suggestions stay in its lane. No outgoing Chat occurred.

## Next actual question

Twelve new capture-onlyq1 initial-root calls exactly reuse12fullq1 baselines.
They preserve all returned actions/scores/completed depths but increase pushes
40163→43360. The declared local cost checkpoint fails; no24game follow-up is
launched. Removing noisy actions does not guarantee less work at a fixed-node cap.

Twelve new check-onlyq0 calls exactly reuse12pureq0 baselines. Pushes are
20447→19706, with two changed actions and three changed scores. All three
paired pilot aggregates still use20505counted visits. Check-only has1919q visits,
of which764are in check. Noise-classification counters are not all actual checks
or evasions. All24new pilot PVs and baseline-return identities pass qualification.
These are work/feasibility observations, not playing strength or value correctness.

The next24whole games are frozen and NOT RUN: Static leaf/order, candidate
check-onlyq0ON against pureq0OFF,2048nodes, all12existing input roles, caller96,
expected600seconds/cooperative cap1200. It reuses eligible A self baselines and
never reruns the pilot. No further capture-onlyq1 fitness, mode-cap refill,
product default, API, learner or AUX change is selected. Science remains OPEN.

Primary literature is used with its limits: [Ye and Marsland1992](https://webdocs.cs.ualberta.ca/~tony/RecentPapers/Experiments-FP-YeMars-1992.pdf)
separates selective-search mechanisms and acknowledges missing execution-time
measurement; its tactical-hit measure is not our whole-game utility. Beal1990's
[publisher abstract](https://www.sciencedirect.com/science/article/pii/0004370290900728)
describes null-move quiescence; full text was not obtained. Neither source licenses
importing approximate repetition rules, pruning constants or null-move assumptions
into arbitrary generated rules. No external positions/human labels were imported.

Full inputs, source, outcomes, exact missing slots, costs, public-copy qualification
and reproducible readers: [evidence capsule](data/price_rule_context_q_and_order_20261022/README.md).
The preceding288-game scope remains at
[69a3c84a](https://github.com/WD-nanophotonics/GenericChess/blob/69a3c84ab0be9875611e751e78d3225f0fa8973c/docs/research/PRICE_RESOURCE_AND_OPPONENT_CONTEXT_20261022.md);
it is not recounted as new work here.
