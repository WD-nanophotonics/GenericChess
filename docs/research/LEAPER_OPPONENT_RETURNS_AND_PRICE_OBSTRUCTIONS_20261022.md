# Leaper opponent returns, longer learning and price obstructions

DEV_AUX / sidemission. Infrastructure source is committed sandbox
`f92d739dec3b7454c58fc2d7709e7233156633e6`. Its delta from the preceding
`559aa80d` baseline changes research/operations documents only, with no shared
package or test changes. Core, GameSession, terminal/history handling and the
public learner search remain the shared implementation. No other checkout,
default player, worker or schedule was changed.

Equal optimal-play WDL does not imply equal usefulness against a specified
opponent. A bounded complete-history observer separates two drawing actions'
eventual returns against an RNG opponent. Conversely, on three actual legal
starts, no nonnegative B/C prices can make a D4 material evaluator choose only
winning actions under uniform ties. **Removing that sign constraint changes
the answer: A=1,B=-1/4,C=0 removes every D4 error on the 13 selected starts and
all four rule controls, including 52 completed public-search checks.** This is
an oracle-selected search-parameter control, not learned or intrinsic prices.
Longer experience moves parameters toward
an exposed better region without reaching it in the executed runs. These are
different claims about conditional return, search parameters and exact value.

Compact inputs/results: `data/leaper_opponent_returns_20261022.json`. Large
records, graph caches, query/PV logs and one-off drivers stay in ignored
`artifacts/`. Local replay is reported below; unpublished raw records have not
thereby received external independent verification.

## A drawing action can be better against the frozen opponent

Use the retained ABA rules and complete prefix **B0 a1-b2**. Player 1 is the
candidate. Compare forced **B1 c1-b0** (low arm) with **B1 c1-b2** (high arm).
Both have exact optimal-play DRAW. The following continuation is fixed before
calculation: A=1, B=3/4, complete D2 minimax with uniform choice among its exact
argmax; the foe chooses uniformly among legal actions. This ideal tie policy is
distinct from the deployed public search's lexical tie policy.

The first foe move has five versus two replies. Its average material proxies
are `-2B/5` and `B-1`, crossing at 5/7; worst-reply material scores cross at
1/2. Neither proxy is an actual game return. The new observer instead propagates
exact rational path probabilities through complete Core GameStates, including
the played prefix and repetition history.

The joint 120-second/100,000-Core-visit allowance stops at the visit cap in
6.927 seconds, after 15,370 expanded contexts. It is closed, not extended.

| Forced arm | Actual terminal WIN mass | Actual terminal DRAW mass | Proved draw-only, unplayed mass | Pending mass | Eventual terminal-payoff bound |
|---|---:|---:|---:|---:|---|
| low | .019525 | .298033 | .641737 | .040705 | [-.021181, .060230] |
| high | .126709 | .069965 | .793978 | .009347 | [.117362, .136056] |

Thus **high minus low is [.057132, .157237]**, a strictly positive exact
probability bound, not a sampling confidence interval. Unexpanded payoff stays
[-1,+1]. Every arm's displayed exact rational masses sum to one.

The zero payoff used for the separate eventual-return bound has a specific
proof: the previously complete graph's 8,088-vertex set is forward closed and
has no reachable decisive terminal under *any* actions. Finite repeat-two play
there can only terminate in a rule draw. These branches were not actually
played to H64 terminals. Counting them as unresolved instead gives wide
terminal-observation bounds; that H64 comparison remains unresolved. The
closure's complete Core-edge verification is retained from the preceding
segment, rather than relabelled a new verification or a positive WIN proof.

The reference and saved-training RuleSets differ only in their inactive
max-ply metadata. Both clocks exceed the conservative `2*7^9` possible-position
bound for these K/A/B, no-hand, capture-removal worlds. Repeat-two therefore
fires before either clock could affect play. The whole prefix and every
transition are retained; a fresh-position WDL was not substituted for history.
This permits the physical-rule bridge, not a general history quotient.

## Longer experience: movement without the requested crossing

Six new runs start from the original weights; no closed 32-episode run is
continued. ABA has K/A/B/A per side. A=1, eta=.05, lambda=.95 and scale=10
remain fixed, with D2 and H64. Each arm retains its own 120-second/2,000,000-node
cap, 8,192 nodes per query and the existing game limits. Eight played legal
opening paths use seed 20261022. RNG opponents use the new seed 2026102202;
the D2 opponent has fixed uniform weights. The latter is **not self-play**.

| Opponent / initialization | Final B after 320 episodes | Learner W / D / L / UNKNOWN | Search nodes |
|---|---:|---|---:|
| RNG / uniform | .612213 | 101 / 215 / 0 / 4 | 31,069 |
| RNG / plus, B=1.03 | .657940 | 97 / 219 / 0 / 4 | 31,606 |
| RNG / minus, B=.97 | .587402 | 101 / 215 / 0 / 4 | 31,107 |
| fixed D2 / uniform | .566523 | 20 / 300 / 0 / 0 | 111,040 |
| fixed D2 / plus | .592220 | 20 / 300 / 0 / 0 | 109,512 |
| fixed D2 / minus | .543036 | 20 / 300 / 0 / 0 | 111,040 |

All 1,920 requested episodes exist, with 12 actual H64 UNKNOWNs and no missing
episodes. Total run time is 294.153 seconds. Coupled starts/seeds, repeated
openings and dependent training trajectories do not supply independent strength
samples. More wins against RNG than against D2 is not a measured training gain.
**None reaches B<.5.** The proposed 320-episode observation alone does not
decide slow convergence versus trapping; it gives no reason to top up these runs.

The complete-prefix post-hoc observer covers all 22,359 learner queries.
B=1/4 versus 3/4 changes the ideal D2 action set on 20 queries per arm, 120
occurrences in total. They still repeat the same boundary history from the
first section, with no difference in optimal-WDL action expectation. Actual
learner WDL-gap sums are 15/17/15 against RNG and 0/1/0 against fixed D2.
No exact label entered training. An observer started while the last arm still
had 31 episodes; its partial snapshot is preserved. Reading only its remaining
289 closed records repairs the coverage within the original combined
1,200-second/1,000,000-visit allowance: 333.183 seconds and 63,395 visits.
Training was not repeated or changed.

## A conditional explanation for the fixed-D2 drift

Once B is inside (.5,1), the fixed-D2 runs reproduce a 16-episode cycle of
physical games and literal PV choices. All 318/299/320 in-chamber episodes in
uniform/plus/minus match their final-cycle templates. This is a finite path
check, not a general convergence result. The three final cycles match each
other too.

Let F_e(B) be the one-episode TD update calculated from a retained template.
For nonterminal PV features `(a,b)`, prediction is `tanh((a+bB)/10)` and the
B-gradient is `b*(1-prediction^2)/10`; terminal PV gradients are zero. The
eligibility recursion is `.95*E + gradient`, and the final target is the
actual stored outcome. Composing the 16 updates defines F.

A global derivative bound uses `|p'|<=|b|/10` and `|g'|<=b^2/50`. Bounds on
eligibility and its derivative give each update a Lipschitz bound L_e. Here
every L_e<1, and the resulting bound on `F(B)-B` is .425564. Outward decimal
evaluation on 101 points in [.5,.6], plus the half-grid Lipschitz cover, gives

```
-.019624 < F(B)-B < -.017954, throughout [.5,.6].
Every within-cycle B is below .600713.
```

All 320 original minus-run updates reconstruct within 1.12e-16. The first
decimal implementation's default-context unary negation did not justify an
outward-bound claim; that output is qualified and preserved. Exact negation
and directed endpoint rounding repair it within the original 120-second and
120,000-row budget. No additional episodes are trained.

Consequently, **under the fixed-template real-arithmetic map**, there is no
cycle fixed point near these final weights. If completed deterministic search
continues to preserve its in-chamber choices, the finals must first cross .5
within at most 4/6/3 more 16-episode cycles. This is a conditional prediction,
not an executed crossing, a floating-point/program proof, a result for fresh
RNG streams, or proof of a unique/useful limiting price. The public q0 adapter
uses equal-price ordering, a fresh player per query, and disables PVS,
aspiration, tactical shortcuts and other advanced switches in this setting.
Resource failures and a changed action/PV regime would require new evidence.

A new 32-slot shadow-update probe tests the boundary from both sides. Each
slot resets the actor to B=.49 or .51, with the same eight openings/two colors
and fixed uniform D2 foe. The TD update is calculated after the game but never
carried into the next slot. All 32 games terminate, with no missing/UNKNOWN,
in 8.789 seconds / 11,121 search nodes. The sums of shadow B updates are
-.0195918 below and -.0184198 above the boundary. Both point downward; these
two points do not show an immediate attracting boundary, nor prove a whole
neighbourhood or eventual convergence. All records and updates replay.

Only slot 13 changes its physical trajectory/PV sequence: the original
B0 a1-b2 boundary, with both actual outcomes DRAW against this deterministic
foe. Recomputing the arithmetic on fixed paths gives:

| Saved paths | Evaluate TD at B=.49 | Evaluate TD at B=.51 |
|---|---:|---:|
| generated at .49 | -.0195918 | -.0198253 |
| generated at .51 | -.0181688 | -.0184198 |

Off-diagonal entries are frozen-path arithmetic, not executed training. The
changed path alters the update even when the actual outcome remains a draw.

The original [TDLeaf paper](https://arxiv.org/pdf/cs/9901001), section 4,
applies temporal differences to minimax-backed evaluations and their PV-leaf
gradients. Its discussion also distinguishes fixed-policy linear results from
nonlinear approximation and parameter-dependent actions. This supports
qualifying the present semi-gradient/control process; it does not prove its
convergence or identify its fixed point with global minimax-optimal prices.
The opponent changes experience and targets, but a minimax-PV predictor is not
automatically a calibrated estimate of return against that opponent. A separate
post-hoc search of 44 non-closed terminal-DRAW-PV histories found no certificate
of the stronger proposed zero-gradient/positive-return example; that remains
unproved and is not claimed as a finding.

## A finite price obstruction, including boundaries

Reuse the 13 previously admitted starts with own A/B still present, under the
four horizontal/vertical C and C-absent controls. A=1; vary **both B and C** in
the closed [0,4]^2 box. Literal complete-history D4 trees cost 6,212 Core visits.
Equality lines between all affine leaf values induce a finite arrangement.
Vertical decomposition evaluates every open 2D cell, 1D edge and 0D vertex;
167 representatives suffice. All 416 earlier D4 checks are recovered.

The minimum uniform-tie expected-error sums across the 13 roots are 1 for
horizontal C, 1/2 for vertical C, and zero for either C-absent control. No point
in the box removes all errors, even if each C-axis world chooses its own prices.
These are sums of action-error probabilities, not game win rates or area of a
parameter region. Representative counts are not area either.

Three individual roots explain the obstruction without a grid approximation.
Their exact root actions have one WIN and otherwise DRAW (one vertical action
is LOSS). The critical D4 player-0 score expressions are:

| Admitted root | Unique WIN action score | Competing DRAW action score |
|---|---|---|
| horizontal 137 | `1-C` | `max(B-1-C,1-C)` |
| horizontal 1658 | `max(0,1-C)` | `max(B-1-C,1-C)` and `max(0,B-C)` |
| vertical 1658 | `max(1,1+B-C)` | `1+B` |

For nonnegative B,C a drawing alternative is always at least as large as the
winning score. Horizontal 1658 uses its first competitor when C<=1 and the
second when C>=1. Thus uniform selection among maximizing actions has error
at least 1/2 at each root. The raw affine argument extends beyond the tested
box; it does not authorize oversized deployed model values or a claim about
every possible tie rule. A position-aware deterministic tie rule could choose
the WIN member of a tie. This is not an all-depth impossibility theorem for
material-based policies.

The published inputs include actual standalone RuleSets and all-defense WIN
strategies, independently replayed through GameSession/Core: ranks 11,7,7,
with 22/8/12 proof nodes. DRAW alternatives still use complete-graph reference
labels, not finite positive WIN certificates.

A separate D2-D6 price-arrangement check on just these three mechanism roots
uses 2,029 Core visits. Minimum aggregate errors are respectively
1/2, 1, 3/2, 3/2, 3/2; the D4 obstruction persists at D5 and D6. These selected
roots are not an independent distribution or an equal-resource strength test.
At depth at least each root's proved winning rank, a complete search with mate
scores above all static leaf values must select a WIN action for every price
in the box. That follows from the all-defense strategy; D7/D11 execution costs
were not measured here. One extra ply and searching beyond the proof horizon
are different claims.

### The sign restriction matters

The nonnegative result must not become a claim that no material parameters
can work. A separate sign-assumption control reuses the same closed trees and
labels over [-4,4]^2. It completes 629 arrangement representatives in 5.918
seconds, with **zero minimum error in all four worlds and jointly**. There are
104 safe representatives, not 104 independent solutions or an area estimate.
An illustrative rational point is **B=-1/4,C=0**. Requiring B>=0 still leaves
no zero-error representative even if C may be negative; allowing negative B
can remove the selected obstruction without requiring negative C.

Public mainline q0 at that point completes all 52 D4 requests, zero errors,
zero UNKNOWN/missing, in 1.175 seconds / 3,908 search nodes. The compact data
provides all four base RuleSets, the 52 actual initial boards and choices.
This is selected using the exposed reference labels, not experiential learning,
held-out validation, a strength gain or evidence that a B actor has negative
intrinsic value. It can be a compensation for a particular horizon/position
distribution. The C-absent intervention removes an actor as well as its moves;
it is not a count-matched isolation of C identity.

A broader exposed-domain cached stress check completes within 150 seconds
(10.046 seconds used), reusing all existing complete labels without new Core
or public-search requests. The domains are 52,456 ongoing fresh ABA positions
and 33,859 ABC positions. The result does not support general adoption:

| Domain / depth | Uniform B=1,C=1 | Selected B=-.25,C=0 | Positive B=.25,C=0 |
|---|---:|---:|---:|
| ABA D2 | 2032.400 | 2239.567 | 1747.300 |
| ABA D4 | 532.633 | 459.667 | 452.000 |
| ABC D2 | 1638.500 | 1838.233 | 1172.683 |
| ABC D4 | 849.867 | 875.333 | 490.467 |

These are exact uniform-tie error sums, not game strength. The apparent ABA D4
gain against uniform prices does not establish a benefit from a negative sign:
the low *positive* B control is better still. A separate missing-cell factorial
calculation, 14.656 seconds, holds C=0 or C=1 while comparing B=-.25 with +.25.
Negative B is worse in both worlds at both depths and either C coefficient.
The C-factor placebo is exactly zero in ABA, where C is absent. In ABC the
error-difference interaction is -231.25 at D2 and -142.5333 at D4: magnitudes
change, but the preference does not reverse. This isolates a B-sign contrast
from the simultaneous B/C changes in the original signed control.

Both world distributions were previously exposed and differ in reachability;
this is not held-out validation or a state-matched causal rule intervention
between worlds. It separates a successful local compensation from broader
decision quality. No default or trained model is changed.

## Fresh legal layouts: diversity is not itself learning progress

Within the existing complete Core graph, hash-order the 2,480 side-0 positions
with exactly K/A/B per owner, using seed 2026102203. The first 64 candidates
are selected without WDL, action, score or outcome filtering. Public initial
validation accepts 49 and rejects 15, with no replacement. The component's B
parities and old root reachability remain selection limits.

Two new arms start uniformly and use the same RNG seed and 98 episodes. The
control repeats the first accepted fresh board; the intervention traverses all
49 fresh boards, with both learner colors at each. This keeps inventory fixed
*within this six-actor AB comparison*. It does not isolate coverage as the
cause of the earlier eight-actor ABA result. No played history is transplanted
into a new initial board. The existing runner now accepts these boards as
ordinary public initial-setup options and retains the setup identity in logs.

| Start distribution | Final B | W / D / L / UNKNOWN | Nodes |
|---|---:|---|---:|
| one fresh board | .959438 | 49 / 38 / 9 / 2 | 8,351 |
| 49 fresh boards | .955107 | 10 / 83 / 0 / 5 | 11,042 |

The two arms take 15.071 seconds, with zero missing episodes. Their different
training outcome totals are not a strength contrast on matched starts. Both
finals occupy the same ideal decision region. On all 49 accepted fresh roots,
the exact D2 uniform-tie error sum goes from 1/3 at uniform prices to 1/2 at
either final: increased layout diversity did not improve this measure.
B=.25 and .75 also both have sum 1/2 here. The older ABA-global preference for
B<.5 cannot be imported as a preference on this new distribution.

All 1,587 new learner queries receive complete-prefix observation. The diverse
arm has 12 distinct B=.5 action-boundary histories, versus none for the control,
but again zero optimal-WDL expectation contrasts. Learner WDL-gap sums are
4 versus 0. Draw-only queries number 721/906 and 574/681. Diversity increases
visited decision boundaries in this sample without supplying the intended
quality distinction or establishing a better price.

## Actual public-policy return comparison

The fixed 49-root, two-color, 96-trial comparison completes **9,408 paired
trials / 18,816 games, zero missing**, in 1,701.722 seconds / 2,263,307 search
nodes. It uses public lexical D2, fixed B=.25/.75,
uniform legal RNG foe, paired streams seeded by 2026102204, H64, and **no
training**. The aggregate hard cap is 1,800 seconds / 8,000,000 nodes; per-game
limits are 2 seconds / 8,192 nodes. Price order alternates within pairs.
Unknown payoffs remain [-1,+1]. The run is closed without extension.

| Fixed price | Actual W / D / L / UNKNOWN | Conservative sample payoff |
|---|---|---|
| B=.25 | 1,197 / 7,890 / 95 / 226 | [.093112, .141156] |
| B=.75 | 1,202 / 7,909 / 95 / 202 | [.096195, .139137] |

High minus low has conservative sample bound **[-.044962,.046025]**. It
does not establish a winner. All 428 UNKNOWNs remain unresolved.

The exact 49-root quality census clarified the interpretation while this panel
was already running, before inspecting its paired result: both prices tie on
aggregate root quality here. The frozen question's suggestion of a lower-price
advantage refers to the older ABA census, not these roots. Prices, roots,
seeds, stopping rules and requested slots were not changed.

For the uniform fixed-root/color mixture, a fixed-sample Hoeffding bound on
paired payoff differences in [-2,2] has 95% radius .056008, added to the
conservative sample interval including every unknown/missing slot. This is
conditional on the fixed roots and independent ideal random streams; the
implementation uses pseudorandom streams. It is not population inference over
rules or a sequential significance test. The resulting interval is
**[-.100969,.102032]**. It contains zero and is not equivalence evidence.

Post-hoc reuse of every pair finds 8,121 identical trajectories and 1,287 action
divergences, at 36 distinct complete histories. The first divergent actions
have equal exact WDL in all 1,287 cases. Among actual outcomes, 110 pairs are
low WIN/high DRAW, and 109 low DRAW/high WIN; 1,085 both WIN, 7,776 both DRAW,
95 both LOSS. The remaining 233 pairs contain at least one UNKNOWN, including
195 with both UNKNOWN. First-divergence observation costs 6.750 seconds / 80
replayed common-prefix Core edges, plus cached full-history attractors. The
two published examples are the first contrasts in frozen order, not independent
confirmations. Later policy choices and RNG-selected actions can differ too;
this does not attribute the entire result to the first move alone.

## Validation, retained failures and cost

All 2,116 new training records replay on their own actual RuleSets, initial
setup identities and full histories. All 38,697 public queries and 75,683 PV
edges are checked; 53,407 played edges and every TD update reconstruct. There
are 2,097 actual terminals and **19 original UNKNOWNs**, preserved. This local
verification costs 12.149 seconds / 184,613 counted Core/replay visits, below
600 seconds / 300,000 visits. It is not another researcher's execution.

176 relevant tests pass, including an actual two-setup/color replay regression.
The source audit matches all 238 shared package files to the fixed mainline
after CRLF/LF normalization. Its general atomic-state regression was restored
unchanged and both tests pass (178 total across the two runs); its implementation
was already identical. 481/485 mainline test files match. The remaining fixture
binding and three PRIMARY/DeepSeek or legacy role-workflow test differences
are listed with reasons in the data; they do not constitute an engine fork or
authorize replacing this role's session/stop protocol.
The meaningful implementation addition is the existing learner runner's small
fresh-setup option; no learner algorithm or second rules/search backend is
introduced. The probability observer and affine calculations are scoped
research references using Core authority, not alternate product searchers.

The 18,816 actual evaluation records also replay in full: 365,776 Core edges,
182,127 RNG-foe choices checked against their paired streams, 18,388 actual
terminals and 428 still-ongoing H64 records. All recorded search-node totals
reconcile. This takes 32.841 seconds, below 600 seconds / 1,000,000 edges;
public searches are not rerun. The compact outgoing copy independently checks
three actual WIN proofs, 17 symbolic score expressions, return-prefix/clock
binding, exact probability conservation and the public-template Lipschitz
cover. It does not relabel the retained decimal grid as a formal program proof.

The sparse one-ordinary-per-owner A/B graph calculations complete on 4x4 and 5x5:
29,252 vertices / 139,790 edges in 36.316 graph seconds, and 223,492 vertices /
1,420,120 edges in 313.238 graph seconds. Every vertex is draw-only and there
are no decisive terminals or WDL-distinct actions. **The existing foundation
report had already proved this impossibility by exhaustive terminal census,
including these sizes and a larger-board locality argument.** The new reachable
counts do not change a decision. Launching these graphs without first recovering
that stronger prior result was an efficiency mistake, not a new scientific
finding or a reason to continue scaling them. Their 365.636 seconds of total
producer work are retained as cost evidence, not added separately to Agent work
credit. Owner 0 has orthogonal A, owner 1 diagonal B. No closed homogeneous
5x5 cap was reopened, but that alone did not justify this redundant work. These
costs also cannot estimate dense six/eight-actor larger boards. The route is
closed again by the existing structural result.

All fixed old task2620/task2625, training, label and exposure caps remain closed.
No missing slot is filled and no UNKNOWN becomes a draw. The initial live-file
observer snapshot and decimal-rounding qualification are retained; their
repairs consume the original allowances. The old Slack SEND_UNCERTAIN report
is not resent. New advice was read, privately saved and assessed, without Dot
waiting or changes to the existing 90-minute recurrence.
