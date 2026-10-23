# Small rule changes: history, strategy and policy are separate coordinates

DEV_AUX, sidemission, 2026-10-24 JST. This consumes existing PRIMARY inputs;
it does not select new rules/layouts or run a forward-game campaign.

Two existing one-orbit changes now have literal strategic explanations. In
3×3 K+A versus K+B, `(6,27) → (22,27)` adds a capture that escapes into a
closed draw domain. In 4×4 K+A versus bare K, `1 → 5` changes two common fresh
starts from DRAW to forced WIN, although both movement graphs stay connected.
Neither result establishes a material price or a learning benefit.

The runtime source is sandbox `0815ac6cb8268266c215c0cd8a24bce12bf52a66`.
Rules, Core, search, terminal/history and public Session interfaces match it;
the two existing AUX learner files remain the only package differences.
H6 forecasts actually executed at `cffcd6d2975375d3a91dfce325c4bb48559c2516`.
The H64 input freeze is PRIMARY `3eb9998822c281834e37443456a36e664e0c1493`.
The unchanged input packets were delivered on sidemission
`1e6728c385dae2461710d22526ae337b5e920bd7`.

## H6: what transfers, and what does not

The pair was the only one-bit adjacency among the previously frozen eleven
defined H6 families. The comparison keeps all 128 common admitted fresh
histories, H6 and repeat-two. The eight old-only starts remain excluded from
this common measure, with their original labels retained separately.

Replaying the sixteen old forced-loss certificates under both rules gives:

- All 80 prefixes retain their physical path, ply, repetition equality pattern,
  check history and terminal result. Their actual rule/state identities differ.
- All 64 transitions require matching each rule's own public semantic action;
  opaque pattern/geometry IDs are not portable physical-action identities.
- All 64 proper subtrees verify after rebinding. All sixteen root proofs fail:
  each omits the new legal defender escape. Keeping a path is insufficient to
  keep an all-defense proof.

The new A long diagonal captures the last B. The resulting no-B domain is
closed and has no decisive terminal. On the common starts, sixteen LOSS roots
become DRAW and sixteen new WDL forks appear. Cooperation remains TRUE at
every start; all 352 common root actions retain their original WDL.

The same-support coordinate table is:

| Quantity | Old rule | New rule |
|---|---:|---:|
| Common admitted fresh starts | 128 | 128 |
| Physical closure reachable from those starts | 1,132 | 1,040 |
| Edges in that closure | 2,304 | 2,104 |
| Complete H6 history-tree contexts | 40,328 | 40,768 |
| Edges in those history trees | 40,200 | 40,640 |
| Initial WDL-fork rate | 3/8 | 1/2 |
| Mean minimax player-0 WDL | −5/8 | −1/2 |
| Cooperative decisive-path rate | 1 | 1 |

The stored old graph has 1,164 vertices/2,352 edges because its original
construction used all 136 old admitted starts. Thirty-two of those vertices
are outside the common-start closure. Delivery review caught this distinction;
the table above uses the explicit common measure. The larger unpruned history
tree despite a smaller physical closure is not a measured search slowdown or
speedup. Alpha-beta pruning and actual search budgets are different objects.

## Policy effects and common-prefix coverage

Both seats first choose independently and uniformly from their own legal
actions. At a still-identical physical prefix, couple each common action with
mass `min(1/m,1/n)`, where `m,n` are the two legal-action counts. Stop the joint
trace at its first different action or terminal result. This maximizes agreement
at that decision; it is not a globally optimal coupling of entire trajectories.

| First outcome of this coupling | Exact probability |
|---|---:|
| Same physical actions through the same terminal | 3643399/4064256 ≈ .89644919 |
| Different physical action first | 361273/4064256 ≈ .08889032 |
| Different terminal status first | 19/1296 ≈ .01466049 |

All 128 laws were independently checked through 38,696 paired full-Session
contexts and 77,136 public transitions. An additional full-GameState risk
calculation checked 81,096 contexts/80,840 edges and the payoff decomposition.

The uniform-policy gain is `2792159/128024064 ≈ .02180964`: 48 starts improve,
80 do not, none worsen. Every contribution comes from the newly available A
capture of B. Removed King actions and changed stalemate status occur only after
B is absent, where both continuations already have payoff zero. A changed
trajectory or terminal name therefore need not change payoff.

This effect also survives a stronger specified opponent. Keeping player 0
uniform, player 1 uses FLOOR: take an actual immediate win if available,
otherwise choose uniformly. Immediate-win ties have identical terminal outcome
and zero future occupation, so their action identity cannot change these laws.

| Measure on the same 128 starts | Old player-0 utility | New | Difference |
|---|---:|---:|---:|
| Minimax | −5/8 | −1/2 | 1/8 |
| Uniform versus uniform | −.28060368 | −.25879404 | +.02180964 |
| Uniform versus FLOOR | −41/48 | −13/16 | +1/24 |

Under FLOOR, only the sixteen direct initial escapes improve; the other 112
starts do not. All 512 root/rule/opponent-mode laws were independently verified
with full GameState and rational path-mass propagation in 26.096 seconds.
These are analytical distributions, not new PRNG games or population estimates.
The legacy `uniform_terminal_LDW` field in this packet's policy tables denotes
the terminal distribution under the explicit `opponent` column.

Changing the measure also changes the apparent effect. Comparing each full
family gives a fork increment `3/34 ≈ .08823529`, whereas the common-start
increment is `1/8`. The difference is the old-support selection term `−5/136`.
For uniform utility, the different-measure increment is .02981335, decomposing
into the common-rule effect .02180964 and the old-measure term .00800371.

All three actual frozen fork forecasters predict zero change on this common
support; the true rate change is 1/8. Their root-contrast MSE is 1/8 and their
mean-rate-contrast squared error is 1/64. The cooperative forecasts correctly
predict a zero contrast, even when their marginal probabilities are poor.
These are exposed retrospective contrast diagnostics, not a new headline,
refit or independent held-out success.

## Why Position, clock and current occurrence count are insufficient

There are two actual histories in each pair rule with the same current board,
side to move, remaining two plies, current occurrence count one and legal action
set, but player-0 truth is LOSS in one and DRAW in the other.

Both end after four actions with K0 b1, A0 a2, K1 c3 and B1 a3. One starts with
B1 c1; the other starts with B1 a3. Their suffixes move A b1–a2, B to b3,
K0 a1–b1, then B b3–a3. K0 b1–a1 immediately repeats a prior position only in
the second history. In the first it remains ongoing and loses to actual mate.
The portable reader checks both pairs by literal short suffix exhaustion.

The existing full-GameState ExactTree independently checked every context and
action in the two common-start trees. A prefix-blocked attractor agrees on all
81,096 contexts/80,840 actions, including 29,416 ongoing contexts. There are
220 old-rule and 178 new-rule contexts whose WDL differs from the first
representative at the same Position/ply. These are correlated comparisons,
not 398 independent rules or uniquely counted physical counterexamples.

The actual learner caller also returns LOSS versus DRAW for the two histories.
One public player with a persistent TT preserves this distinction in both query
orders. These are six bounded integration calls, not a repair to PRIMARY code.

For the admitted position-local game with draw-only repetition and a finite
draw clock, an existing attractor can be reused with the actual prefix barriers.
Redirect future nonterminal arrivals at a position already seen `limit−1`
times to a draw sink; the current root still has its outgoing choices. Preserve
mate/stalemate precedence. A decisive rank that fits the remaining clock gives
a strictly decreasing all-defense strategy and cannot repeat a future vertex.
Conversely, a finite actual winning tree supplies a winning tree in that
prefix-blocked graph, so its minimum winning rank must fit the clock. This is a
scoped history reduction, not scalar Position-label copying or a generic TT key.

Fresh-root/action checks cover all 3,616 supplied H6 roots and 10,936 actions.
They take 13.840 seconds. The prior compact solver's history component was
5.530 seconds, with graph construction separate; no speedup is established.
The reduction's independent abstract control exhausts the 625 four-vertex
alternating games at repeat-two and repeat-four. Those are semantic tests,
not additional Leaper experiments.

## H64: connected movement graphs, different strategic regions

Use PRIMARY's existing one-bit `1→5` control and its two shared fresh layouts.
Mask 1 has the previously certified no-mate obstruction and remains DRAW.
Mask 5's newly checked closure has 3,952 vertices/18,408 actual Core edges.
Both fresh layouts are WIN with rank 9. Its two separately supplied four-ply
prefixes are WIN with rank 5; they are not paired with the other rule's different
random prefixes. Four literal all-defense certificates verify 48 nodes/44 edges.

Both fresh mask-5 roots have no WDL fork: every legal first action preserves
WIN. Later on the selected proof paths, 41 distinct nonterminal histories contain
24 winner-turn contexts and 17 defender contexts. Seventeen winner contexts
have forks; twelve of those have no immediate mate. This is conditional proof
support, not natural policy occupation or oracle-selected training starts.

One frozen diagnostic queries those twelve contexts at D1/D2/D4 using the
committed mainline q0 adapter, A fixed to one, all other weights one, zero capture
ordering prices, fresh TT per query, 8,192 nodes and three seconds per call.
All 36 calls finish the requested depth, costing 4,378 nodes/.948 seconds total.

| Requested depth | Inferior exact choices / 12 | Actual nodes |
|---|---:|---:|
| 1 | 3 | 137 |
| 2 | 0 | 408 |
| 4 | 0 | 3,833 |

All 78 retained PV actions replay through the public Session. Each D1 mistake
permits immediate capture of A and a closed bare-King draw. A separate literal
334-edge check finds that all nominal two-ply material maximizers preserve WIN
on these twelve contexts; one-ply ties include inferior moves. This supports a
shallow capture mechanism here, not an extra D4 benefit, a policy win rate or
a general depth law. A chosen winning action may leave the selected proof tree;
correct choices on its sampled prefixes do not prove an entire D2 policy wins.

The material learner has channels `(board,A)` and `(hand,A)`, with board A fixed.
Across the complete domain their features are `(1,0)` at 3,640 positions and
`(0,0)` at 312. There is no active free material parameter. This roster is a
search control; the result does not justify launching material TD training.

## Collaboration, boundaries and verification

Adopt the latest F(R; μ, policy/budget) direction and the instruction to stop
legacy-only UNKNOWN reduction. Defer the proposed new 31-mask/board-scale
campaign: PRIMARY owns selection and its full measured budget is not supplied.
There is also a scope correction to comment `1792766992.946839`: among 75
one-bit edges, 11 have two single-parity ends, 23 cross that boundary, and 41
have two mixed ends. The single-parity argument alone does not certify the
remaining 52 edges unchanged. A stronger obstruction may classify some mixed
cases; mixedness itself never guarantees mate.

Only this checkout changes. No new worker, Goal, timer, rule/layout sample,
forward policy game, training update or default was created. Actual search calls
are 36 diagnostic plus six integration calls. The old 1,904 missing policy slots,
unavailable H6 family, stopped caps and historical partial outputs stay intact.

The [packet and commands](data/leaper_pair_transfer_20261024/README.md) expose
all scientific objects and source hashes. Sixty-one distinct focused tests pass
(64 executions). A complete public-reader run reproduced all longer controls
in 207.365 seconds before the final policy addition; the policy addition has its
own complete literal control. The final combined reader passes in 61.372 seconds at delivery.
Representation and support-audit corrections are recorded without changing
history labels or probabilities. New code ran before this segment's commit;
final code hashes are post-execution qualification, not blinding receipts.

Next: consume PRIMARY's independently frozen next pair/common full-history μ
and actual forecasts. Preserve the distinct rule, strategy, policy and cost
coordinates. Further teacher-only queries on this closed batch are not queued.
