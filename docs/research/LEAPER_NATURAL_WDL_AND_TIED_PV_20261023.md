# Natural Leaper histories: exact WDL and tied-PV learning signals

DEV_AUX / sidemission. PRIMARY retains rule generation, openings, forward
screening and inverse proposals. This is a post-hoc truth and learning-mechanism
study of already committed histories; it generates no rules, games or training
starts and changes no engine, learner or production default.

## Main findings

The original near-uniform float question is answered: all 75 new public D4
queries return exactly the represented-weight values predicted by their local
formulas. A more important distinction appears at a third natural root: a
correct search value can accompany a selected-PV derivative that is outside
the local critic's generalized gradient. The existing TDLeaf implementation
uses that leaf derivative, as its classical arbitrary-tie approximation permits.
This is a scoped approximation issue, not a search-value defect or evidence
that TD as a whole fails.

A complete four-actor graph also supplies exact action WDL for 39 natural
late-game histories. Four roots have different-WDL legal actions, but **all
468 Unit/mobility/Static-material queries at D1/D2/D3/D4 choose an optimal-WDL
action**. The observed random game eventually throws away a win for an immediate
stalemate; even Unit D1 avoids that error. These roots therefore demonstrate
real action-quality opportunity without demonstrating a need for learned prices
or deeper search. They are one exposed trajectory, not independent samples.

The metadata-selected capture-reduced corpus closes all24 graphs. Its216
additional queries also show zero paired minimax-WDL gain over Unit D1;
three absolute action qualities remain one-sided, but their shared identical
actions make their paired differences exactly zero. No partial or uncertain
state is assigned a draw to obtain that result.

## Sources and unchanged infrastructure

- PRIMARY input: `55abf3de22f20ac03eb07b5260284466173a3264`, frozen small-family
  and resource/material packets. The original input hashes remain in
  [the previous report](LEAPER_PRICE_DEPTH_CONTEXT_20261023.md).
- Prior AUX capsule and exact local formulas:
  `7dda1a79d00175631cf22b586a5912df93b7843c`.
- Latest fetched sandbox: `edda38828d970cb6a1669ffa3ac95aa93167ce71`.
  No newer commit was available at recovery. Its rules/Core/Session/AI and
  public Leaper helpers remain the reused baseline. The only scientific
  package differences are the maintained AUX learner and receipt adapter.
- Public deployment queries use `generic_chess.learning.mainline_search.search`:
  fresh TT per call, equal capture ordering, q0, 8192 nodes/5 seconds, reserve0.
  The adapter delegates search and semantics to the committed public runtime.
  Graph generation reuses Core and `leaper_retrograde.fresh_state/attractor`;
  no second rule/search engine or infrastructure acceleration is claimed.

## Exact values versus the derivative of a selected PV

The initial query plan freezes unit plus four rational epsilons
`{1/8, 2^-20, 2^-40, 2^-52}` times six directions. Intended fractions and actual
float ratios/hex values are retained; represented conditions are deduplicated
before search. Each root has 25 distinct represented conditions. Two intended
off-diagonal perturbations at the smallest epsilon round onto a diagonal;
they are interpreted using actual weights, not the intended fractions.

The first two full-history roots are:

| Root | World / mover | Player-0 D4 critic near uniform |
|---|---|---|
| `88a181c1c72e45403fd2cc25b77e58735470409ce9ca75e1014d70446d3e239d` | 16 / 1 | `-abs(B-C)` |
| `40b723490e7fda6765ecaea9cb7df61c3601d57a39d7df151b1dbfe3d8d65c87` | 17 / 0 | `0` |

All 50 calls complete D4: 20,154 nodes / 3.430695 seconds. Every value matches
the exact rational formula evaluated at the actual floats, with zero tolerance.
The flat root keeps its served action and zero gradient throughout these probes;
its wider optimal support can still change. At the absolute-value root, zero
unit gradient and nonzero off-diagonal gradients are consistent with a cusp.
A rounded lower diagonal selects a nonzero leaf slope at zero value; that is
not a numerical score error.

We then retain both complete source trajectories: small-ladder slots131
(world16, FLOOR/random, 96 observed plies, ongoing) and136 (world17,
random/random, actual stalemate after50 plies). All 146 roots receive a frozen
Unit D4 query: 27,118 nodes / 9.384181 seconds. An exact integer-vector tree
control evaluates all146 roots at37 rational price representatives, 147,621
Core visits / 13.273237 seconds.

This control uses the previous complete local arrangement argument: leaf
coefficients are in `{-1,0,1}^3`; non-through-unit equality planes cannot cross
the open box `|B-1|,|C-1|<1/4`; twelve rays partition all through-unit leaf-order
lines. Two independent directions inside each sector plus continuity identify
its affine critic. It covers that entire open box, not just fitted sample points.
Terminal values are price-constant and dominate these bounded material leaves.

At slot136/ply3, root
`7353875caaa94cff369c7b0b4c345e64a61564b3dc46d7b5d8a07b4b75c08a52`,
the player-0 critic is exactly `min(B,C)-1`. Its limiting raw B/C gradients are
`(1,0)` and `(0,1)`; their convex hull is its Clarke generalized-gradient set
at unit. The public Unit PV has player-0 feature `(A,B,C)=(0,1,-1)`, giving
raw slope `(1,-1)`, outside that hull. Along `B=C=t`, the actual critic is
`t-1`, while this fixed leaf remains zero. Thus this selected leaf's derivative
is not a derivative of the root value, even in that simple joint direction.

All25 new float checks at this third root still return the exact critic value:
3,771 nodes / 0.915487 seconds. The unit point alone serves the non-critic slope;
the other24 represented conditions serve one of the valid limiting leaf slopes.
The producer's original membership summary accidentally compared tuples with
lists and flagged all25. A separate saved correction recomputes membership
from the unchanged raw JSON; no query, value, source or cap was rewritten.

Three of146 unit PV slopes are absent from the open-sector slopes. Two are
zero slopes lying inside the corresponding convex hull; only slot136/ply3
is outside it. No sampled locally constant critic has a nonzero B/C PV slope.

[Baxter, Tridgell and Weaver, TDLeaf(lambda), section4](https://arxiv.org/pdf/cs/9901001)
explicitly discuss minimax ties and choose an arbitrary candidate leaf. Our
natural uniform-material counterexample shows why that derivative should be
called a tie-dependent surrogate here. It does not contradict differentiability
almost everywhere or establish a failure rate for other rules or initialization.

## Complete-history TD arithmetic, without a training experiment

Each actor's stream is evaluated separately using frozen weights, scale10,
eta0.05 and lambda0.95. The recorded actions remain PRIMARY's RNG/FLOOR choices;
they differ from the queried public choices at33/48,33/48,18/25 and23/25 roots.
These are **off-policy arithmetic controls**, not new on-policy training,
deployed models or strength results. Only the real stalemate supplies a final
zero target; the ongoing slot131 has no fabricated final reward.

| Slot / actor | Search observations | Nonzero-gradient observations | Offline delta B | Offline delta C |
|---|---:|---:|---:|---:|
| 131 / 0 | 48 | 4 | -0.000551519108 | +0.000581294918 |
| 131 / 1 | 48 | 5 | -0.001345802409 | -0.000205329899 |
| 136 / 0 | 25 | 17 | +0.000663185962 | +0.000236440934 |
| 136 / 1 | 25 | 12 | +0.002460148436 | +0.002079495889 |

The initial selected roots themselves do not have rescuing earlier eligibility:
slot131's prior same-actor ply1 gradient is also zero, and slot136 is an opening.
Later roots provide nonzero gradients. Later zero-current-gradient observations
can contribute through accumulated eligibility. A separately implemented
backward discounted-error sum, evaluated as exact rationals of the recorded
floats, equals the forward eligibility sum and reproduces all four library
updates. This refutes a whole-episode no-update inference from one PV.

One named mathematical counterfactual replaces only slot136/actor1/ply3's
`(0.1,-0.1)` derivative with the symmetric generalized-gradient choice
`(0.05,0.05)`, holding every action, prediction and other derivative fixed.
The final off-policy B/C values change from `(1.0024601484,1.0020794959)` to
`(1.0034998964,0.9989602521)`. This demonstrates arithmetic influence, not an
improved learning policy or permission to tune derivatives using this outcome.

## Literal depth and short-WDL controls

The new full-trajectory D4/D6 panel freezes292 tree slots at nine B/C prices.
It closes282 new trees, reuses six identical previously checked trees, and
retains four capped D6 trees. All292 slots were attempted; no missing slot is
filled. Total: 5,133,755 visits / 500.409055 seconds. The initial driver syntax
error occurred before any calculation and is retained privately.

An independent reader recomputes every new complete tree, its full legal root
support and conservative terminal-WDL bounds: 282 trees / 3,733,751 visits.
It also binds196 queried receipts and762 PV edges and independently checks the
backward TD arithmetic. PASS in360.866393 seconds. Reused trees remain bound
to the previous capsule; capped trees are never promoted to complete supports.

At slot136/ply49, three actions force a win within three plies; the actual
random King move `(2,0)->(1,1)` immediately stalemates. Thus its action is a
true DRAW while a WIN is available. The complete D4 support is the same winning
triple at all nine prices. Unit D1 already selects a WIN, so proof depth three
does not establish a three-ply deployment requirement or a depth-strength gain.

## Closed graph: exact WDL on the actual late histories

From ply11 onward slot136 contains only player0 K against player1 K+A+B.
We build the union of reachable Positions from all39 recorded roots using the
same fixed rule, Core legality and capture removal. The complete graph has
25,774 Positions /123,842 edges; terminal nodes are648 checkmates and620
stalemates. Its relative graph values count11,492 LOSS,9,128 WIN,5,154 DRAW;
maximum decisive rank10. Build time34.805061 seconds.

These are not generic Position-only labels. The fixed RuleSet has only Leap
movement, no hands, drops, promotions, auxiliary state or history-dependent
legality/adjudication. Repetition4 and max_ply128 draw. Every complete observed
prefix has prior occurrence counts at most2; an action can make only its current
key reach3. A rank-decreasing winning strategy, including every defender reply,
never revisits a Position and therefore cannot trigger repetition4 against
those prefixes. Every decisive rank is at most10, below the remaining79–117
rule plies. Residual draw strategies avoid loss; additional repetition or a
finite draw clock cannot make them lose. The complete graph thus supplies
actual-history WDL here. This argument does not authorize arbitrary histories,
perpetual-check losses, other adjudication, partial graphs or TRAIN labels.

All graph edges are independently regenerated through Core, with local
win/loss/rank/draw constraints, root reachability, complete actual histories
and the clock margin checked. A missing-root-edge negative control is rejected.
PASS:25,774 Positions /123,842 edges /39 roots /468 choice bindings,26.934436s.
An additional84,672 finite abstract-graph controls compare a full count-history
DFS to the reused attractor/rank result at repeat4 and horizons1–8. They support
the stated argument, not a broader history quotient.

All39 roots are WIN for player1; only four have mixed-WDL root actions, at
plies21,41,43,49. The actual random trajectory preserves the win until ply49.
For all39 roots, Unit, exact4x4 mobility B/A=`84/36=7/3` and Static-material
B/A=`1707/756=569/252` are queried at D1/D2/D3/D4. All468 calls complete their
requested depth:40,001 nodes /16.330860 seconds. Every choice is exact-WDL
optimal. This is an exposed finite decision panel, not matched-cost strength
testing; faster/shallower policy adequacy here is not a general depth result.

## A structural deadzone, distinct from the previous rule-clock tail

The no-B subset of the graph is closed:2,298 Positions /9,510 edges, only20
stalemate terminal nodes and no possible winning terminal. Both frozen layout
rules differ only in initial position/metadata. Every subset edge and terminal
is rechecked through Core under slot131's actual fingerprint, rather than
assuming a representation equivalence. PASS in3.039549 seconds.

Slot131/plies36–95 map into this closed subset, and its actual ongoing ply96
endpoint is bare K versus K. All future terminals are DRAW; actual repetition
or the finite rule clock guarantees eventual termination. These are structural
no-win states, unlike the previous edda ply124 result whose proof relied on
only four remaining clock plies. The original source slot131 remains observed
UNKNOWN; this is a separate post-hoc truth annotation, not resumed play or
replacement of its observation/utility interval.

## Metadata-only capture-reduced corpus

Before running any new graph, we freeze one ongoing four-actor history per24
existing small-ladder worlds, selected by the lowest SHA256 of
`AUX-postcapture-fouractor-v1:<complete-state-hash>`. Selection uses neither
terminal outcome, oracle label, price response nor graph success. All source
histories are exposed post-hoc evidence; this creates no held-out sample or
experiential TRAIN start. A new90s/101,280-Position cap per graph sits inside
one1800s whole-panel cap. The prior PN/depth/price studies stay closed.

All24 graphs close in1256.121818 seconds. The construction pays for959,604
Position entries and4,649,688 edges across separate graphs. Those are **paid
entries, not unique independent states**. Conservative behavior-plus-physical-
vertex-set grouping yields17 component groups; it does not prove every other
group inequivalent. World17's selected history also overlaps the earlier
39-root trajectory. Its repeated component construction is counted as cost,
not a new independent result or an efficiency gain.

| Actual-history root qualification in the original corpus output | Worlds |
|---|---|
| Exact WIN | 3 |
| Exact LOSS | 9,11,13,17,23 |
| Exact DRAW | 1,2,4,5,6,7,8,10,12,14,15,18,19,20,22 |
| One-sided, unchanged | 0:`[0,1]`;16,21:`[-1,0]` |

The one-sided cases have a prior repetition count3. Fresh Position WIN/LOSS
alone is not silently substituted for their history-conditioned label. For
world0 only, a separate new fixed-policy rank replay constructs a six-node,
rank5 actual GameSession all-defense WIN certificate. The maintained verifier
accepts its complete record/terminal binding and rejects a target flip. The
original corpus `[0,1]` row remains unchanged; this positive root certificate
does not automatically label every other action or the two uncertain LOSS roots.

Only worlds5,12,15 lie in a structural draw-only closure: no decisive terminal
is reachable by any policy. For the other21 roots, a shortest cooperative
Position path to mate is actually replayed under the saved full history before
being described as a legal mate path. A minimax DRAW with such a path is not
a structural no-win deadzone. Only world3 has mixed *fully qualified* root
action WDL; world0 has fresh mixed values with one-sided decisive alternatives.
None of the sampled original actions is a certified strict WDL error under
the unrefined bounds.

The fixed query panel executes all24 roots at Unit/mobility/Static-material
prices and D1/D2/D4, irrespective of graph result. Exact rule-derived mobility
uses the maintained compiled movement projection and Core empty-board mobility;
Static-material uses the maintained profile's actual table. All216 calls
complete:14,604 nodes /6.678271 seconds. At a fixed depth the three price
baselines choose the same action at every root. Relative to Unit D1, D2 changes
actions at worlds4,7,12,14,18; D4 changes actions at3,4,7,12,14,18,22.

Every condition is WDL-optimal at the21 roots with fully qualified absolute
quality. At worlds0,16,21, all nine conditions select the same action at the
same complete history. The action's absolute WDL remains uncertain, but its
paired difference against itself is exactly zero. Consequently all eight
nontrivial conditions versus Unit D1 have finite-panel mean minimax-WDL gain
`[0,0]`, without assigning a value to an UNKNOWN action. This is neither a
population confidence interval nor a universal price/depth ceiling.

This panel also exposes a tractability/parameter tradeoff. Four actors mean
two Anchors plus only two ordinary pieces. In12 roots just one ordinary type
remains; in12 there are two. Within these positive material baselines and the
terminal-dominance range, common positive material scaling preserves leaf
ordering, so these contexts have respectively zero or one effective ordinary-
price ratio. They do not test two independent relative prices or full ABC
composition interactions. This is not a hard admission rule for learning;
it explains the scope lost when capture reduction makes exact graphs cheap.

Finally, equal minimax action WDL does **not** establish equal conversion
probabilities against Random, equal future policy trajectories, equal compute
cost or no possible TD benefit. Those are different estimands. These data do
not supply evidence to launch another TD panel merely from a changed score,
gradient or tie. PRIMARY's rule generation and forward screen remain its work.

## Cost follow-up and a cheaper next question

A new cost-only preflight selects one natural five-actor A/B/C history by a
separate metadata hash, across the same committed trajectories. It reaches the
100,000-discovered-Position cap after86.398645 wall /86.109375 process-CPU seconds.
The producer's63,478 `expanded` counter counts popped nodes:63,477 are fully
expanded and the last is partial when a new child hits the cap. Another36,522
remain queued. The observed capture frontier contains17,093 distinct four-actor
Positions; none matches the already closed component under this same fingerprint.
There is **no new root/action WDL**, no completion estimate asserted from this
partial frontier, and no continuation or reset of its90s/100k cap. A concurrently
running portable verifier is part of the recorded ordinary machine conditions.

A separate membership-only census is cheaper:2060 references reduce to2047
distinct full histories;1107 lie in existing complete components,898 meet the
conservative repetition/whole-component-clock margin, and527 covered roots
contain two ordinary types. The latter two counts need not be the same subset.
It takes23.777158 seconds and assigns no new WDL or TRAIN start. Components and
worlds remain dependent.

The next executable question is therefore the D1 price-capacity census on this
larger *natural* covered pool, before a large five-actor launch. Use qualified
history labels, exact finite price-cell representatives in a stated bounded
positive-ratio window, full argmax sets and a separate actual-tie control. Keep
all unqualified/missing roots visible. The maintained fresh-repeat-two D4
observer must not be reused as a repeat-four history oracle; D1's safe one-step
semantics and existing tie arithmetic can be reused. This is a changed exposure/
truth premise, not a retry of old3x3 panels or a prerequisite imposed on every
learning method. Any later full five-actor closure needs its own realistic
whole-run/verification/memory budget; >=120min still needs Chat assessment.

## Selected evidence and verification

The portable capsule is580,287 bytes, SHA256
`ff05c0273a6d0d8565a57722edf43a5c6c80ba4a79abd4249a479afb4c3d66b7`.
It contains905 public-query receipts, complete source records, the compact
25,774-Position representative graph, all local/support controls, selected
executed source strings and the six-node certificate. Other full corpus
graphs remain ignored and are reproducible from their frozen input records.
The packing import-path failure occurred before producing any capsule and
is retained privately; it caused no scientific call or cap reset.

`data/leaper_natural_wdl_20261023/verify.py --corpus` checks every query/PV,
the rational local critic controls, TD arithmetic, D4 supports and the entire
representative graph, then independently rebuilds every completed corpus graph
through Core and binds reported WDL/closure results. `--literal-six` additionally
regenerates D6; the separate full D4/D6 reader already passed282 new trees.
The portable reader passes in996.728429 seconds:905 queries,2491PVedges,
146D4supports,146rational local trees,fourTDstreams,two negative controls,
the representative graph and all24 corpus rebuilds. Its actual final receipt
is saved beside the capsule (`corpus=true`, `literal_six=false`).
Seventy relevant mainline-learner/Leaper interface tests pass in2.24 seconds.
Large raw graph/trajectory payloads and standalone temporary drivers stay ignored.

The original caps, UNKNOWN outcomes and rule clocks are retained. No new Agent,
Goal, worker, conversation, timer, Slack resend or other-role write is created.
The existing60-minute cadence is unchanged. Research session accounting and
publication receipts are finalized at the safe checkpoint, with administrative
transport excluded.
