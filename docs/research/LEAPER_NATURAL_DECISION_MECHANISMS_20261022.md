# Natural Leaper decisions: price, depth, history and progress

DEV_AUX consumes PRIMARY's committed rules and trajectories under the
[user-endorsed division of work](LEAPER_INVERSE_DESIGN_DIRECTION.md).
This study adds scientific truth and learner diagnostics. PRIMARY retains rule
generation, canonicalization, cheap game screening and product defaults.

## Sources and the question that changed

Infrastructure is sandbox `55abf3de22f20ac03eb07b5260284466173a3264`;
the frozen input is PRIMARY `291f2c3b169992d451743f4babf314ca3a26776f`,
`docs/research/data/small_rule_family_20261022/observations.json.gz`,
SHA256 `1a48f7eaf038cc7745d6dd82ebc784d7a666286a59c7d159c4c1ba3c5338d087`.
The same 64 AB games/eight 4x4 configurations are exposed, related worlds,
not a new canonical-rule batch or independent test set. Repetition=4,
rule clock=128 and caller cutoff=96 remain different quantities.

The preceding report solved two D1 price-sensitive four-actor histories and
found both neutral. That does **not** describe all natural four-actor decisions.
We now use every natural four-actor visit, selected without WDL filtering.
Complete closures reuse the old <=3-actor graphs and applicable complete
four-actor graphs. Actual-history labels use the previously stated restricted
count-three/remaining-clock rank argument; no general Position-only history
cache is asserted.

## Natural four-actor truth

All 26 world/inventory components close in 390.477 seconds. They account for
609 visits, 596 distinct complete histories and 502 distinct Positions. There
are 105 visits with actions of different WDL and 19 inferior recorded choices.
The component-summed graph size is 1,139,558, including 313,787 reused entries;
825,771 new Core expansions are charged. These sums are work measures with
shared subgraphs, not independent states or samples.

| Recorded policy | Visits | WDL-fork visits | Inferior choices |
|---|---:|---:|---:|
| RNG |232|21|7|
| FLOOR |123|13|6|
| Static D1 |150|25|5|
| Static D2 |104|46|1|

These are conditional observations from different endogenous trajectories,
not randomized policy comparisons. The earlier statement that all nine
<=3-actor errors were RNG errors remains scoped to that smaller region.

## Actual learner search: useful price effects are rare, but real

The existing public pure-material q0 learner adapter ran all 596 histories at
B/A=1/2, 1, 2 and D2/D4/D6. All 5,364 calls complete their requested depths and
PV validation: 2,566,662 nodes, 755.477 seconds, no missing calls. Ordering uses
equal capture prices and fresh per-query TT; advanced PVS/aspiration switches
remain off. This is the learner's existing caller, not PRIMARY's full Static
evaluator. Each call has the same 8,192-node/1.5-second allowance, with 10% of
the time reserved for literal PV replay.
The learner sets ordinary and hard quiescence depths to zero. PRIMARY's new
forward driver retains its declared forced-check limit of eight. These are
caller configurations over the same shared search implementation.

With two ordinary actors, positive pure-material leaf order has two open
B/A chambers, separated by 1, plus the boundary. The three representatives
cover those ideal complete-search order cells. They do not enumerate all
numerical behavior under arbitrary finite budgets or Static positional terms.

| B/A | D2 inferior choices | D4 inferior choices | D6 inferior choices |
|---|---:|---:|---:|
|1/2|4|1|1|
|1|3|0|0|
|2|3|0|0|

One history, world13/slot104/ply13,
`fe0e8dd3c4793e2fb48f9cfe0bb541032e1ba428c4d88c0798540cef038c3479`,
changes from LOSS at B/A=1/2 to DRAW at 1 or 2 at all three depths. The finite
paired quality difference is 1/596; it is not a population confidence interval,
new game win-rate improvement, held-out transfer result or trained-model gain.
The four original D1 profiles were invariant at this history. D1 price
sensitivity therefore cannot be a necessary gate for later material utility.

Literal Core D2/D4 controls expose the tie mechanism: B/A=1/2 has only losing
argmax actions; B/A=1 ties DRAW and LOSS actions; B/A=2 has only DRAW argmax
actions. Equal prices succeed through the current canonical tie choice at this
history. The boundary is not a tie-independent safe price. A separate actual
154-node all-defense certificate binds the B/A=1/2 intervention's losing child.
The safe capture has a closed 2,298-Position/9,510-edge subgame with no decisive
terminal, so repetition/clock can only add draws. This independently establishes
the actual chosen LOSS-versus-DRAW contrast without shipping a large graph.

D4 repairs three D2 inferior choices for each price. D6 changes no chosen WDL
relative to D4 here. For B/A=1, D2/D4/D6 use 13,930/114,387/725,988 nodes and
3.032/25.604/222.202 seconds. Even when B=1 and 2 have equal WDL quality, nodes
change at 3/21/34 histories and actions at 3/8/10 histories respectively.
Work changes, action changes and useful changes are separate observations.

Preserving a WIN label also does not guarantee that the deployed policy
eventually wins. Among 109 preserved WIN choices, D4 fails to decrease the
proven distance rank at 53 histories; D6 at 45. D6 improves this progress
diagnostic despite identical WDL quality and substantially more work. This
does not establish actual game lengths or a universally better depth.

## Gradients and representation do not settle policy quality

The closed one-ordinary-B probe has identical actions, PVs, features and nodes
in all 33 complete D2/34 D4 positive-price triples. Nonzero gradients occur at
28 D2/13 D4 roots per positive price. No node-cost effect was measured there;
nonrandomized wall times are not evidence of a scale-induced speed difference.
Terminal scores are not divided by B in the scale comparison.

Shared-action cancellation tightens contrasts in the closed 52-history panel
without querying or filling missing labels. All 26 invariant controls have
zero profile contrasts even if their absolute WDL remains unresolved. Among
26 sensitive histories, Static-Unit is exactly zero at 21; its mean bound
across all 26 histories is [-5/26, 4/13]. No pair has a sign-certified
advantage. These are ideal uniform-support contrasts, not literal deployed ties.

Within the new four-actor census, nine of 25 rule/material feature groups have
different exact WDL labels. Even an unrestricted material-only critic,
allowed a separate function for each rule, has
empirical squared-error lower bound 1400233/46809840 on the 596 histories and
22 unavoidable classification errors. Two same-Position groups in world18
have different actual-history WDL (slot151, plies30/34 versus38 and31/35
versus39). These facts limit a material-only **critic**; the strong D4 action
results above show why they do not by themselves justify adding a neural model.

## Feasibility limits and next decision

A separate opening check uses eight previously unassessed six-actor initial
roots, outside the old 52-history panel. Its original 1,000,000-node allowance
ends in 70.436 seconds: only worlds0/1 are attempted, H6 completes, H8 is
partial, both WDL bounds remain [-1,1], and six worlds are unattempted.
This batch is closed. Encountering some mate terminals proves neither an
opening forced win nor a draw. The old 2M-node and assessor batches remain
closed with their original missing rows and charged failures.

The natural five-actor batch closes at its original 1,800-second allowance
(1,800.178 observed seconds, including atomic operation overshoot), with
450 seconds/component and 600,000 states/component. Thirteen of 24 components
complete: 145/260 visits, 136/244 distinct histories, 61 WDL-fork visits and
19 inferior recorded choices. Component13 remains incomplete at 143,191
states/17,200 pending; ten components are unattempted. No labels are produced
from the incomplete component, and no continuation/refill is queued.

The completed subset is cost/order conditioned, not representative of the
unresolved worlds. With the previous <=3-actor results, exact post-hoc labels
now cover 3,538 of 3,968 natural visits. This high visit coverage is dominated
by later subgames and does not solve the six-actor openings. Original actual
caller-UNKNOWN games remain UNKNOWN; optimal-continuation labels do not replace
recorded outcomes or censoring.

For three remaining ordinary actors, conservative surviving-material leaf
vectors give positive critical B/A ratios 1/2, 1 and 2. These are search
parameter cells, not intrinsic values or assumed strategic additivity. A new
bounded public q0 screen uses all 136 completed histories, seven chamber/
boundary representatives and D2/D4: 1,904/1,904 full-depth calls, 251,847 nodes,
49.908 seconds, no missing calls. The original truth cap is not extended.

| B/A | D2 inferior choices | D4 inferior choices |
|---|---:|---:|
|1/4, 1/2, 3/4|10 each|7 each|
|1|7|4|
|3/2, 2, 4|2 each|2 each|

B/A=3/2 versus 1 improves five D2/two D4 histories and worsens none in this
subset: conditional paired means 5/136 and 1/68. Across the original 244
histories, 108 are unmeasured, giving conservative mean bounds [-211/244,
221/244] and [-107/122,109/122]. Both cross zero. No price, model or default is
promoted, and no learning or held-out improvement is claimed.

## Validation and delivery

All 19 four-actor observed mistakes have actual-prefix all-defense winning
certificates for their decisive side: 9,014 Core nodes. The intervention proof
adds 154 nodes. This is not independent reconstruction of every DRAW label.
The [compact capsule](data/leaper_natural_decisions_20261022/manifest.json)
contains all 7,268 public-call receipts in compact form, branch labels and
arithmetic, all 20 winning strategies, the safe-draw witness and executed
research sources. Large caches and transient drivers stay ignored.

Its [verifier](data/leaper_natural_decisions_20261022/verify.py) reuses the
existing public proof verifier and shared Core: 9,168 proof nodes, two corrupted
proof controls, 1,165 literal price-control nodes, six independent public
search calls, and the 2,298-state/9,510-edge safe-draw closure. It recomputes all
compact receipt arithmetic. Full graph/history-WDL censuses remain locally
verified results, not a claim that the small default verifier reruns every graph.
The two focused search/Leaper regression files pass all 57 tests.

An initial packet check correctly rejects a binding mistake: the historical
FLOOR error and the B/A=1/2 counterfactual choose different losing moves. Its
failure receipt is retained. The new 154-node proof covers that distinct
intervention; the old 19 proofs and experiment budgets are not rewritten.

No new physical games, training, generator, production default, worker or
schedule change occurs. Next consume PRIMARY's committed canonical batch when
available. Independent backups diagnose PV-gradient exposure and rank progress
from the existing complete receipts; nonzero gradients, critic residuals or
locally improved prices alone do not establish learning or whole-game strength.

At delivery, PRIMARY publishes `e8f4abf94bde7b6de1ab1a9acc3abfd24533c002`.
Its maintained `scripts/leaper_design.py`, `scripts/leaper_portrait.py` and
`tests/development/test_leaper_design.py` are copied byte-for-byte into this
checkout; the rule/search/history package itself has no new delta. All 32 new
interface tests pass. The 8.7MB input capsule is retained only in ignored local
artifacts, not duplicated into this delivery. Ten first-record-per-fingerprint
full-record checks and ten actual learner H1 calls/103 nodes pass on the new
committed inputs. The learner correctly uses four channels with no unused C,
without a second generator or a hardcoded six-channel adapter. This is consumer
compatibility, not a new strength or speed result; the experiment sources above
remain 291f2c3/55ab. The next Main consumes e8f4's frozen canonical trajectories.
