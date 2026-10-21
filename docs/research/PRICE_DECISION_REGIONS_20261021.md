# Price decision regions and goal-sensitive search

PRIMARY_SANDBOX, 2026-10-21. Pre-change public source:
`897a110db22483c8fa99b8156a6d4547a655ca0d`. This is mechanism research,
not a new learner, solver, Elo campaign or product default. DEV_AUX was untouched.

## Decision

Keep rule-only static, Unit and learned candidates. Diagnose the actual decision
surface under a stated evaluator/search budget before treating a feature count,
score change or parameter convergence as useful learning. Neither root feature
presence nor a D1 sensitivity result is a training gate. Positive rule prices and
unconstrained signed heuristic coefficients have different feasible regions.

A concrete existing Gumbel terminal-value defect was independently reproduced
and fixed: use the rule authority's `winner`, including stalemate loss and
continuous-check outcomes, rather than recognizing checkmate alone. This does
not integrate MCTS as a Player or demonstrate its strength.

## Blocked-leg price probe: value changes can leave policy unchanged

Eight prespecified exposed 4x4 layouts, seeds732001..732008, retain their original
admission outcomes. Seven fail initial anchor safety in BOTH guarded and
unguarded variants; none was refilled. The accepted seed732005 supplies three
legally played roots at plies0/4/8. Guard-aware opportunity gives H:B=623:1377;
removing the guard only for the price control gives728:1272. Both price tables
are evaluated on the same guarded executable rules.

Complete D2 trees use199 nodes; fifteen public checks agree. The optimal action
sets are invariant throughout H/B in[1/8,4]. A posthoc D3 control uses1277 tree
nodes, with fifteen matching public checks. Some D3 action sets change at H/B=1,
but the two actual price tables remain in the same regions on all three roots.
Six additional exact-integer table queries agree. At ply8 the actual backed-up
scores are +131 and -184, with the SAME selected action.

The separately declared four-slot exploratory continuation reuses `play_game`:
fixed Unit board opponent, inert hands0, candidate owners0/1, D3/q0,4096nodes,
0.1seconds per decision,90seconds overall, absolute external ply72. All256
queries complete D3; all four games remain ONGOING/UNKNOWN at that cap. Within
each owner the two candidate tables produce identical complete records.
No extension or utility claim. Their actual rule max_ply128 was not reached.

A separate one-axis guard-removal rule control legally replays all three
prefixes. It changes D3 optimal action sets on two roots. This is a different
executable game, not a price effect or a whole-game isomorphism assertion.

## Promotion and hand BASE prices move the decision boundary

Reuse the existing 8x8 lifecycle fixture, not an AUX pilot: real captures,
occupied hands, a semantic current-type change R to TP, an expiring auxiliary
bool, and guarded drops. Three full-history roots at plies4/5/6 produce1179
complete D2 tree nodes. Thirty grid queries and eighteen boundary queries match;
the boundary checks include837 actual Native calls with zero fallback.

At ply6 write r for board-CURRENT R price, t for board-CURRENT TP price, and h
for hand-BASE R price. The actual tree has these four possible leaf forms:

| Form | (board R, board TP, hand R) | Value |
|---|---|---|
| A | (2,2,2) | 2r+2t+2h |
| B | (3,1,2) | 3r+t+2h |
| C | (4,1,1) | 4r+t+h |
| D | (3,1,0) | 3r+t |

For r,t>0 and0<=h<=r, C dominates B and D. Three actual promotion actions attain
A against every D2 reply;53 safe drop actions attain C. Thus the exact finite
value is max(A,C), with boundary **t+h=2r**. If h=eta*r, the r/t boundary is
1/(2-eta):1/2 at eta0,10/11 at eta0.9. This is a decision-equivalence plane,
not an intrinsic universal price or a proof that eta0.9 is useful.

Full base/current identities, promoted flags, hands, auxiliary expiry and history
are retained by Core and replay. The bool is preserved; this fixture does not
establish that its current value is a useful evaluation feature. Omitting it
from a leaf feature vector does not authorize deleting it from rule/history
identity. No positive-price or no-drop restriction is imposed on GenericChess's
long-term target; these are declared experimental scopes.

## Actual finite goals distinguish lack of information from shallow blindness

A NEW authored3x3 world has an explicit RULE max_ply6, guarded knight-like H,
orthogonal-ray B, two anchors, no executable drops/promotion/auxiliary actions.
This is not a longer run or relabeling of any earlier UNKNOWN. All legal uniform
random prefixes through two plies yield four slots of mass1/4: one actual
stalemate draw and three continuing roots.

The existing `reference_minimax`, with an entry fuse150000nodes/90seconds,
completes198 calls. A nonterminal horizon evaluator raises, so no heuristic
frontier can masquerade as WDL. Every continuing root has a genuinely winning
action. All sampled positive prices and the exact D2 regions choose draw-valued
actions. The first two roots' winning actions necessarily give up H at the D2
frontier; a safe alternative preserves H+B. For positive UNCLIPPED H,B and inert
hands0, H+B strictly exceeds B. This explains the blindness beyond the finite
grid. In the third root a winning action ties with draw actions at identical
material features.

Six actual games hold a D3 foe and Unit prices fixed, changing candidate depth
only. D2 gives three actual rule draws (one stalemate, two max_ply); D3 gives
three actual checkmates. Whole-game paid nodes, including the foe, are169
versus304. This is a local depth mechanism with more work, not equal-resource
strength or three independent rule-family replications.

A posthoc signed-region check is essential: H=-1000 or-4000 permits the D2 player
to choose winning actions on the first two roots; the third remains draw-valued.
All fifteen signed public queries complete. No weights are fitted or adopted.
Do not generalize the positive-price limitation to an unconstrained learner.

Six prospectively enumerated A/B/C type-label bijections each preserve the FULL
reachable finite tree:206 nodes,205 transitions,105 terminal leaves, exact
base/current/promoted state, custody, actor/check events and repetition identity
bijections. Semantic pattern/geometry identities are explicitly mapped. One tied
choice varies with encoding; all selected action WDLs remain0. No encoding-quality
gain is claimed. Initial move correspondence alone was not called isomorphism.

## A cheap exact D1 sensitivity diagnostic, with explicit limits

Reuse the published six-rule/24-history calibration source; generate NO new
trajectories. Prefixes0/9/18/27 define96 planned slots:83 ongoing, one terminal
at its prefix,12 ending earlier. All types are retained: board CURRENT and hand
BASE coefficients; anchor coefficients0. The box is board125..4000 and hand0..4000;
the Unit baseline is board1000/hand900. Dynamic terms, promotion bonuses, q,TT
and ordering are off. All material scores are bounded by48000, below clipping.

For baseline selected action k and competitor j, maximize the affine difference
(v_j-v_k).w+(c_j-c_k) at its analytic box corner. A positive difference, or a
zero difference with earlier lexical priority, constructs a different argmax.
Otherwise k is invariant over the entire box. This O(actions*parameters) check
needs no LP dependency or new optimizer; terminal values use the actual winner.

| Rule seed | Ongoing | Full-box sensitive | Board-only sensitive | Hand-only sensitive |
|---|---:|---:|---:|---:|
|731501|5|0|0|0|
|731502|14|11|11|9|
|731503|16|10|10|10|
|731504|16|12|12|6|
|731505|16|13|13|13|
|731506|16|14|14|14|

Of60 responsive states,18 have a completely zero root material vector. Of23
invariant states,14 have a nonzero root vector;12 of the23 already have an
immediate winning baseline. All60 have a changed integer witness strictly inside
the box. This is descriptive, exposed, correlated data, not a population estimate,
a TD eligibility claim or evidence of utility. The computation visits2267 full
children in1.98seconds. Independent enumeration of5312 corners on11 selected
controls agrees;22 public D1 checks agree, including six Native calls/no fallback.

The first non-immediate-win invariant natural root,731503/policy0/ply0, remains
unchanged in nine D2 single-type perturbations. Retain this negative result.
A separately authored4x4 exchange supplies the missing counterexample: D1 always
captures a positive-price immobile victim, while D2 includes a legal recapture
and compares -actor with -victim. Actor500/victim1000 captures; actor2000/victim1000
avoids it. Four public queries agree. **D1 invariance is not a safe D2 filter.**
No closed hand-price or static-order utility panel was reopened.

## Fixed dynamics and literature assumptions

Keeping all material ratios fixed while scaling their absolute values can change
choices if current dynamic weights2/5/3 remain fixed. On the SAME mixed fixture,
24 public queries match exact finite-tree boundaries23/250,97/450 and7/45.
This is different from the old all-active-integer x4 control. It establishes no
benefit for any scale and changes no normalizer/default.

[TDLeaf](https://arxiv.org/pdf/cs/9901001), section4, differentiates the backed-up
value through a selected principal leaf, with qualifications at ties. That is
not a policy-gradient or an identifiability guarantee. In our unclipped positive
finite-world counterpart, value H+B has nonzero gradient even when the selected
D2 action stays in a draw-valued region. This is our example, not a refutation of
TDLeaf or evidence about executing AUX's learner.

[Clune2007](https://cdn.aaai.org/AAAI/2007/AAAI07-180.pdf), pp1137–1139, combines
payoff, control and termination models, and compares against early payoff. Its
Chess model uses control when payoff-correlated features are unavailable.
The paper does not isolate stability alone or supply matched GenericChess cost
or strength evidence. Defer a full port rather than import its shown coefficients.

[Danihelka et al.](https://davidstarsilver.wordpress.com/wp-content/uploads/2025/04/gumbel-alphazero.pdf),
sections3.3–3.4, distinguish exact action values from estimated values and
sequential-halving estimation. The improvement argument does not promise strong
play from arbitrary zero leaf estimates. The existing uniform-prior smoke mode
is not the old terminal-rollout UCT probe; neither result settles the other's
strength. Keep the no-adapter/no-default decision for lack of utility evidence.

## Reproduction, validation and next step

[Compact technical evidence](data/price_regions_20261021/evidence.json) retains
rules, records, outcomes, exact regions and witnesses without raw Chat/account
logs. Four current scripts are `scripts/price_regions.py`,
`price_regions_mixed.py`, `price_regions_goal.py`, and
`material_choice_sensitivity.py`. Additional actual producer sources accompany
the evidence. Raw originals, setup/mapping failures and all diagnostics remain
ignored locally. Some posthoc algebra/checks ran inline; no byte-identical
all-phases regeneration is claimed. Current scripts preserve the declared
protocols; run to fresh ignored outputs, never overwrite frozen evidence.

Before the Gumbel repair, the actual eight-case regression fails exactly the
two owner-symmetric stalemate-loss cases. The correction then passes both owners'
checkmate/draw/loss paths and12/13-ply legal checking cycles, with exact Native
history transport and back-up checks. The integrated affected run passes71 tests.
No static assertion expectation, native binary, budget default or rule was changed.

The next single rule-axis control is ALREADY STARTED: append one empty row to the
finite world, retain the same pieces/coordinates/typed rules/max_ply6, and legally
replay the same four prefixes. Opening actions change4to5; the old terminal-draw
prefix is ongoing in the new game. No new WDL or game result has been computed.
Freeze150000reference nodes/90seconds for the next segment. These are matched
source-world prefixes, not the new game's natural opening distribution.
