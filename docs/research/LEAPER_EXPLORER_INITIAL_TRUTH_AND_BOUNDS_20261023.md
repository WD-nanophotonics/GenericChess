# Leaper explorer: initial truth, local bounds and matched-mu evaluation

DEV_AUX continues the user-endorsed explorer direction, on the same ten exposed
canonical rules and369complete records. No new rule, play layout, Player query,
training or default change is introduced. PRIMARY retains those responsibilities
and the E0features/predictions. Data and a portable reader are in
`data/leaper_explorer_followup_20261023`.

The ten ORIGINAL initial histories now have complete cooperative-decisiveness
truth:9TRUE/1FALSE. Initial WDL-fork truth remains9UNKNOWN/1FALSE. These are
different properties. No actual matched PRIMARY E0/baseline forecast was present
at this ordinary probe, so false positives/negatives remain **unmeasured**.

| Fixed34037-history support | Previous packet | With new evidence |
|---|---:|---:|
| Exact WDL |31390|31808|
| WDL not exact |2647|2229|
| WDL-fork TRUE |1914|1918|
| WDL-fork UNKNOWN |2647|2220|
| Cooperative TRUE |4612|4627|
| Cooperative FALSE |24406|24778|
| Cooperative UNKNOWN |5019|4632|

Of the2229remaining nonexact WDL labels,29are[0,1]and2200remain[-1,1]. Neither
is a DRAW or a scalar training target. All original capped/partial results and
the original packet remain unchanged; these are separately verified layers.
The31390inherited scoped labels are not all independently re-solved by the
portable reader. The418new exact WDL labels have the separate invariant or
literal terminal proof described here.

## A no-mate invariant closes the missing initial case

The fixed code[2,4]has adjacent-step Kings, diagonal-step A and two-square
orthogonal B. Every ordinary piece initially lies on the SAME checkerboard
colour across BOTH seats. Ordinary Leaps preserve that colour; captures remove
pieces, and the rule has no drops,promotion,auxiliary effects or resurrection.

If a King is checked, it must be on that colour: ordinary pieces cannot attack
the other colour, and legal Kings are nonadjacent. For every possible pair of
nonadjacent King squares, the checked King has an orthogonal adjacent square
of the opposite colour outside the enemy King's attack. That square is empty
of ordinary pieces and cannot be attacked by any ordinary piece. Moving there
is therefore a legal escape. The78finite geometry pairs for the relevant colour
are supplied as an independently checked table, rather than assumed from a
diagram. There can be no checkmate. Stalemate,repetition and the finite128-ply
clock are draw-only, so every complete legal continuation from this initial
invariant is DRAW.

The continuation quantifier is over Core board actions and rule terminals.
Voluntary Session resignation,declarations and external caller adjudication
are not paths in this tree;caller truncation remains UNKNOWN.

The checker physically binds4134source histories and36complete records,
19616legal actions and183checked-history escapes through current Core. It adds
372exact DRAW/fork-FALSE histories and2013exact action bindings. The successful
initial checker receipt is8.384s; proof construction,implementation,tests and
analysis are additional costs within this research segment.

Adversarial tests check312dense constructed Core states over both colours,
omitted/unsafe geometry and unsupported semantics. Other constructed positions
under the same movement laws DO mate, including one where a friendly piece of
the other colour blocks an escape. A constructed six-actor ongoing position
also has a one-ply mate. These are **not** records reachable from the original
initial history, new PRIMARY play layouts or E0benchmark cases. The theorem
requires a global ordinary-piece colour,not a separate colour per owner; it
does not claim that every arbitrary placement of these movement types draws.

## Cheap local truth before deeper proofs

One complete pass over the2275remaining unresolved histories checks14454Core
successor edges in49.325s. A terminal child has a literal WDL label; an ongoing
child remains[-1,1]. Taking the maximum child bounds gives46new exact WINs and
29nonloss bounds. Exactly one legal action establishes fork-FALSE without
solving its WDL:51such histories close this property. Disjoint exact terminal
choices establish4new fork-TRUE histories. Fourteen previously missing
cooperative positives also follow. No second ply is searched.

An independent legal_actions/apply_action reader checks the126changed roots,
741edges and86exact terminal action labels. Those741edges are the changed-row
verification workload,not the producer's complete14454-edge pass.

Two less efficient bounded attempts are retained as failures/cost evidence:

- An existential initial-history path search stops at100000expanded nodes,
  549422generated edges,completed depth7,in37.795s:UNKNOWN. The later invariant
  is a new proof premise,not an extension of that search.
- A24-root near-clock all-continuation batch stops at1000000node visits in
  77.687s:1COMPLETE,1partial UNKNOWN,22unstarted. The complete root's98755nodes
  independently verify in19.230s. It has minimax DRAW but terminal outcome set
  {player0LOSS,DRAW}; a literal8-ply mate lands exactly at the128-ply boundary.
  A positive needs that8-edge witness; the whole-tree attempt was unnecessary
  for that existential question. No missing batch slot is filled afterward.

One local certificate adds a concrete guarantee-loss occurrence beyond the
previous240. At ply21of record
`09989ed2e4b5a2ac4d65a6dfb5b5c309f02c3a48e3d7957ed04e3b69fedb36f2`,
root`02acc3c10f9373b269f5f5e67111e0ab2ab40f0801d3fe5c1d034bd7b764ba83`
has immediate mate choices A:c2-b2and A:c2-b1. The actual RNG action A:c2-d2
instead causes immediate stalemate DRAW,with107ruleplies still available.
This proves a real WIN-to-DRAW guarantee loss and an absorbing draw terminal,
not just a price/PV difference. The same full record has two controller
references,not two independent games. It is not an E0false-negative example:
no E0prediction exists.

An initial public-API keyword error in the path entry and a SessionResult
attribute error in the colour checker are preserved,with their repairs.
Different node conventions,post-hoc proof insight,caches,load and engineering
cost prevent treating these receipts as a controlled speed comparison or a
learner/player acceleration result. Execution/source qualifications are explicit
in the packet; current published verifiers recheck the claims.
The quoted timers measure the indicated search/check/pass components;some
input loading,materialization and serialization are outside those timers.
Complete outer-command wall clocks were not independently recorded. They are
not end-to-end experiment-cost guarantees.

## Events, sampling laws and forecast targets

Of369distinct saved episodes,148certainly encounter a WDL fork,36certainly do
not,and185remain UNKNOWN. Their540controller references give207/54/279;
references are not independent games. For guarantee-loss events the analogous
distinct-record counts are81TRUE/36FALSE/252UNKNOWN. No positive episode has an
exact first-event time yet: unresolved earlier histories can precede the first
known event. Late-label volume cannot stand in for early decision coverage.

The proposed initial-history truth view preserves exactly the original ten
history hashes and rules,with new point-mu IDs. Its cooperation proportion is
9/10. Uniform over the34037saved ongoing histories,the same property is only
bounded by4627/34037to9259/34037. This is an actual target shift,not E0error.
The global laws also assign different weights to rules;this is not an isolated
causal effect of game stage.
The packet supplies exact shared-label contrasts between all saved sampling
laws. UNKNOWN labels are shared across laws,so bounding their difference
directly can be tighter than subtracting independent marginal intervals.
The exposed6/4family partition has5positive/1negative initial cooperative
labels in calibration and4positive/0negative in leaveout. That leaveout cannot
estimate specificity or provide a false-positive case. Do not refill or select
held-out rules by their oracle outcome to manufacture the missing class.

Scoring now supports both exact history-property forecasts and rule-level
prevalence forecasts. If r is the true finite prevalence and p the forecast,
mean binary Brier loss equals(p-r)^2+r(1-r). Rate squared error and binary
Brier have different raw losses and skill denominators; their paired absolute
model-versus-baseline improvement agrees because the common term cancels.
Rate-loss bounds respect integer feasible label counts,not a fictitious
continuous truth inside an interval. Paired comparisons retain common UNKNOWN
labels,missing forecasts,known-support skill and equal-rule weighting. They
do not create a predictor or prove that a supplied freeze was blind.

All results are finite exposed controls. Descriptive counts/ratios/loss bounds
are valid with that denominator; population calibration, IID confidence and
new-rule generalization do not follow. A small initial-root action disagreement
rate alone is not a mathematical bound on complete-policy utility: identical
first actions can diverge later. Even a small per-decision disagreement can
occur at the one consequential decision in every game. No TD work is reopened.

## Communication, source and next decision

The probe saves44threads/45exact raw returns. Seven formal revision decisions
include qualified adoption of Claude1792752568:use finite cases and a real
frozen baseline;retain descriptive denominators rather than impose a blanket
ban on ratios. Legacy-tagged Chat reply1792756416to PRIMARY is also saved and
reviewed:adopt its finite-case/whole-policy qualifications;defer its192-slot
price/depth campaign as PRIMARY-owned. It does not reactivate Dot. Reading,
adoption,actual execution and the other partner's reading remain separate.

Shared committed sandbox source is
`c7e7b84101ee286a4d3bc98a19a33463afd2809d`,fetched into this checkout's
FETCH_HEAD. Rules/Core/search/history/Session/runtime exactly match that source;
the only generic_chess branch differences are the existing AUX learning files.
New PRIMARY-specific calibration scripts/data are not a second AUX campaign.
Original canonical records remain pinned to e8f4abf94;all role,stop and cap
boundaries remain. Only sidemission is published;the60-minute patrol is unchanged.

The next concrete question for Chat/PRIMARY is whether first E0should use the
now fully labelled original initial-cooperation view,with a separate late-history
fork diagnostic,or keep the earlier all-history target. I recommend the former
for an opening headline,with explicit exposed-control status and a frozen real
baseline/information set/uncertainty/cost. Initial-fork proof expenditure should
follow an actual decision-changing E0error,not another broad graph. PRIMARY
chooses the target and genuinely new holdout;AUX evaluates exact matches.
