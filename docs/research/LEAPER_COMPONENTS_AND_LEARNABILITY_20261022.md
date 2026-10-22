# Leaper components, representation limits and a learnable geometry control

The unchanged TD learner improves decisions in a new, still small Leaper world.
Giving B the four additional orthogonal steps, while A stays orthogonal and
both sides retain K+A+B, produces a complete 35,144-position benchmark. Starting
from uniform weights, two 768-episode runs reach B=2.4171 and B=2.4626. Both lie
in the better D2 price cell above 2. On 1,824 layouts excluded as training
starts, the frozen RNG-trained model makes 170 suboptimal public choices,
compared with 381 for uniform weights. There are also 12 WDL regressions.

This is finite evidence of useful experiential adaptation, not a universal
price, numerical convergence, an untouched test world or superiority over
oracle tuning. An oracle-selected untrained B=3 control matches the learned
model's decisions and complete evaluation games. The earlier diagonal-B
world's negative learning result remains intact.

The preceding inventory-conditioning proposal is paused. A specific D4
counterexample below cannot be repaired by *any* inventory-only scalar
evaluation that gives equal inventories zero, even if its other values are
nonlinear or negative. Deeper search repairs the same case. This does not
exclude useful inventory conditioning elsewhere or evaluation with positional
or tempo information.

Compact numerical evidence, complete selected rules, Core trees and winning
certificates are in
[leaper_components_learning_20261022.json](data/leaper_components_learning_20261022.json).
Full graphs, journals and exploratory drivers remain local. The compact bundle
does not make every raw trajectory remotely available or claim independent
external reproduction of every aggregate.

## Authority, shared infrastructure and preserved boundaries

Pinned committed sandbox is `32dc8ac898c76b7f440b5722a03667bfb68d5872`.
Its countermove cost-probe option and corresponding tests are reused. All 238
shared package files match after line-ending normalization; the only extra
package modules remain the existing AUX learner adapters. The three historical
test differences and one other-role test omission are unchanged. No rules,
move generation, search or terminal engine is duplicated.

New research code only batches the existing cached-graph diagnostic and exposes
an explicit B geometry in the existing Leaper constructor/training helper.
Default geometry and default training behavior remain unchanged. Rule execution,
all legal actions, full histories, public q0 search and played records use the
shared GameSession/Core. No product evaluator, weights or defaults are adopted.

The existing ACTIVE 90-minute recurrence and role boundaries are unchanged.
Old experiments, caps, failures, UNKNOWN and the 394 unprocessed old oracle
queries remain closed. No worker, Agent, Goal or replacement timer is created.
Claude's new comment `1792637349.439849` is adopted with qualifications: pause
representation and diagnose information before expansion; do not turn the old
16-root price-pair contrast into a universal ceiling, impose an arbitrary 1%
gate, repeat already completed sparse 4x4/5x5 graphs or adopt PRIMARY tasks.
The historical uncertain Slack report is not resent.

## Starting-component restrictions matter

Diagonal B preserves square color. On 3x3 its even-square movement component is
a four-leaf star with the center square; its odd-square component is a cycle.
The old six-actor observations inherited two odd-square Bs. They did not cover
every possible layout of those pieces.

A label-blind control fixes K0,A0,K1,A1 at flat squares 6,3,1,2. Before reading
oracle labels, it chooses quiet, compiler-admitted B placements in three color
cohorts. New even/even and even/odd graphs complete; the odd/odd graph is reused.

| B starting colors | New graph vertices | Edges | Matched root result |
| --- | ---: | ---: | --- |
| even/even | 25,088 | 68,992 | DRAW |
| even/odd | 22,660 | 59,528 | WIN in one |
| odd/odd | existing graph | existing graph | DRAW |

The middle root's win is an actual two-node all-defense Core certificate.
It is an immediate-mate layout control, not evidence of a challenging learning
problem. An initial old-graph lookup omitted fingerprint rebinding; the saved
correction finds odd/odd root 50021 without rerunning any graph.

Seventeen rational representatives cover every leaf-order cell and boundary
for B in [-4,4], A=1, in these one-A/one-B inventories. D1/D2/D4 are evaluated
with exact root-action labels, including returns to the fresh root as draw.
Ideal argmax ties are randomized uniformly for the diagnostic; actual public
tie choices are checked separately.

| Cohort | Intact ongoing roots | D2 roots whose WDL expectation changes across positive prices | D2 B=.25/.75 contrasts |
| --- | ---: | ---: | ---: |
| even/even | 5,344 | 64 | 0 |
| even/odd | 5,088 | 152 | 0 |
| odd/odd | 4,880 | 144 | 16 |

Thus the old 16 is a particular price-pair count, not an upper bound over all
prices or representations. These are exposed component counts, not independent
samples or frequencies in future games.

Among quiet side-0 initial layouts, D4 has minimum total ideal errors 0/1800,
4/1760 and 0/1888 respectively. The middle cohort prefers B in (1/2,1), while
the last prefers (1,2). Across all 5,448 such roots, the best global price has
8 expected errors; separate oracle-selected component prices have 4. This is
a small diagnostic opportunity, not a learned conditional policy.

One explicit equal-inventory pair is even/odd root 13297 versus odd/odd root
17393. Their zero-error B sets in [-4,4] are disjoint; their minimum combined
uniform-tie error is 1/2. Actual public D4 chooses WIN/DRAW at B=.75 and
DRAW/WIN at B=1.5. Both choose WIN at D7. Their actual all-defense certificates
have ranks 7 and 5. This is a depth-dependent useful-parameter conflict.

## Actual experience and the representation counterexample

For each diagonal-B color cohort, select the first 128 hash-ordered quiet
initial layouts without labels, keep immediate wins, and play both candidate
colors once. The fixed candidate is B=.75,D2 against legal RNG.

| Cohort | W / D / L / UNKNOWN | Candidate queries | Observed nonoptimal choices | Winning games containing a candidate error |
| --- | --- | ---: | ---: | ---: |
| even/even | 53 / 193 / 0 / 10 | 2,673 | 44 | 6 |
| even/odd | 67 / 180 / 7 / 2 | 2,396 | 42 | 5 |
| odd/odd | 42 / 205 / 1 / 8 | 2,325 | 7 | 0 |

All 768 games and 7,394 full-history query diagnoses complete. The 20 horizon
endpoints remain UNKNOWN. Every candidate error in a final winning game is a
missed WIN converted to DRAW, not a demonstrated escape from forced LOSS.
B=.25/.75 produces no D2 WDL contrast on these visits; B=.75/1.5 produces
7/9/1 contrasts. Narrow price pairs can miss available information.

An independently bounded, explicitly error-enriched diagnostic evaluates all
93 observed D2 mistakes at D6 and D8. All 186 checks complete in 195,376 Core
visits. D6 still has total ideal errors 31/6, 5/3 and 0; D8 has zero on these
selected histories at both tested prices. This is not an unbiased estimate
of deeper-search quality or proof that deeper search never introduces errors.

At even/odd root 4089, the unique exact WIN is A b1-a1. Its rank is 7.
For any scalar leaf evaluator depending only on the four ordinary inventory
counts, assume equal inventories have score zero and terminal wins dominate
leaf scores. Do not assume additivity, positive contributions or monotonicity.
Write four otherwise arbitrary inventory values as a,b,c,d, as identified in
the evidence. The complete actual Core D4 tree reduces to:

```
WIN action W = max(min(a,0), min(b,0), min(c,d), min(d,0))
DRAW action D = max(min(a,0),           min(c,d), min(d,0))
DRAW action Z = 0
W = max(D, min(b,0))
```

If W<=0, Z is not worse. If W>0, W=D. Therefore no such inventory evaluator
can make the sole WIN the unique D4 argmax. A reflected root 8966 has the
same obstruction. Public D2 through D6 misses both wins for all four tested
prices; D7 and D8 find them. The win certificates replay against every defense.

The initial free-lattice equality test does **not** find identical unrestricted
inventory expressions; that attempted stronger argument is not used. Exhausting
128 threshold patterns with balanced inventories fixed to zero verifies the
stated obstruction, and 625 direct tree/formula checks validate its extraction.
Dropping the balanced-zero assumption admits an explicit biased inventory
table that fixes these selected roots. No such table is adopted. A tempo term,
spatial evaluation, other tie policy or deeper search lies outside this negative
claim. Counts alone cannot establish that all inventory conditioning is useless.

## A richer geometry supports useful learning

Two further bounded controls complete without larger boards or new engines:

| Control | Vertices | Edges | Fresh W / D / L | Observation |
| --- | ---: | ---: | --- | --- |
| K+A+2B per side, diagonal B | 85,217 | 229,222 | 12,013 / 66,380 / 6,824 | More quantity is not automatically an informative initial pool |
| K+A+B per side, king-like B | 35,144 | 93,024 | 13,968 / 11,864 / 9,312 | Many more price-relevant decisions |

The quantity control replaces the second A in the old eight-actor ABA layout
with B, preserving occupancy. All 79,816 ongoing roots are labeled, and all
D1/D2/D4 price cells complete within its 900-second census cap. Yet only five
intact positions, two quiet side-0 starts, occur in this particular forward
component. It is not a broad initial-layout benchmark. No training is launched
on the premise that doubling quantity must improve information.

For king-like B, all 31,040 ongoing roots and their complete price cells are
labeled. There are 8,240 intact roots, of which 1,920 have positive-price D2 WDL
contrasts. Among 1,952 quiet side-0 initial layouts, that count is 704; 1,808
have actions of different exact WDL. D2's best bounded global cell is (2,4],
with 160 expected errors, compared with 1202/3 at uniform B=1. This stronger
signal, rather than a bigger board alone, motivates the small learning pilot.

Freeze 128 quiet layouts by hash before consulting labels. Reuse the existing
learner, A fixed at 1, all initial weights 1, scale 10, eta=.05, lambda=.95,
D2, three passes and both colors. Each arm retains the existing 120-second,
two-million-node cap. The RNG arm has no searched opponent; adaptive selfplay
shares the current model on both sides, frozen during each episode.

| Arm | Episodes / missing | Final B | Search nodes | Seconds | W / D / L / UNKNOWN |
| --- | --- | ---: | ---: | ---: | --- |
| RNG | 768 / 0 | 2.417109611 | 40,398 | 31.93 | 451 / 274 / 42 / 1 |
| adaptive selfplay | 768 / 0 | 2.462603514 | 71,550 | 48.61 | 197 / 374 / 197 / 0 |

These outcomes describe changing training policies, not frozen strength. The
RNG arm has 604 distinct complete records; selfplay has only 136. Repeated
episodes and the two final numerical values do not establish independence,
unique prices or convergence.

The complete post-training observer covers 6,046 learner queries. B=1/B=3
produces 316 strategic WDL contrasts in RNG experience and 290 in selfplay.
Of these, 186 and 182 have nonzero selected-PV B gradients. Frozen-gradient
TD credit reconstructs every one of the 1,536 updates within 2.23e-16.
Strategic-query origins contribute +.764267 and +.550103 to the net B changes;
other origins also contribute. This is not causal reward attribution or an
ablation, because later TD errors credit earlier gradients.

Observed draw-only queries contribute exactly zero B credit in both new arms.
Their nonterminal PVs have B feature zero; the remaining PVs are terminal.
This is a property of the visited training traces. The complete new graph
still contains draw-only vertices with B present, so it is not a theorem that
every B-containing position can reach mate.

## Frozen evaluation, limitations and next question

Freeze the two final models. On the 128 training-start layouts, actual D2
nonoptimal choices fall from 35 for uniform weights to 10 for either final
model. Both finals and the oracle-selected B=3 control match action, PV and
node count on every root.

On **all remaining 1,824 quiet initial layouts**, public D2 queries have no
missing or incomplete results. Errors fall from 381 to 170. WDL choices
improve at 231 roots and regress at 12; improved WDL need not imply that the
new action is fully optimal. The learned model again matches B=3 on action,
PV and nodes at every root. These layouts were excluded as training starts,
but may have occurred as descendants, and the world was already exposed by
the exact benchmark. They are not untouched holdout rules or a population test.

New-seed frozen games on the original 128 layouts and both colors give:

| Model | W / D / L / UNKNOWN |
| --- | --- |
| uniform | 128 / 119 / 7 / 2 |
| RNG final | 154 / 93 / 7 / 2 |
| oracle-selected B=3 | 154 / 93 / 7 / 2 |

On the 256 paired slots, learned-minus-uniform score gain has censoring bounds
**[11/256,15/256]**. This is not a confidence interval. The learned and B=3
controls have identical complete records on every slot. Of 53 first policy
forks from uniform, exact common-prefix WDL improves at 44 and stays equal at
9; none worsens at the first fork. Later trajectories and RNG opportunities
differ, so this is not an attribution of every terminal gain to that first move.

A diagonal-B training control uses the same set of 128 initial boards and
finishes at B=.923763/.755727. It is **not** a strict matched-order/seed control:
serialized setup options are lexically key-sorted, and extracting their tuple
order reassigns 126 of 128 setup indices. Initial-board set, learner, caps and
global seed are shared, but update order and per-board RNG seed differ. Preserve
the runs, original source and qualification; do not attribute all adaptation
differences solely to geometry or rerun/reset the closed caps. Future projection
and comparison code must resolve explicit setup keys through GameSession.

The same positional-index mistake initially broke one portable fork example;
it was repaired inside the observer's original 180-second deadline using the
actual initial GameSession board. Game production and common-prefix scoring
already used explicit keys. The first failure and separate repair source remain.

No evaluator/default is selected. The next useful question is whether adding C
changes the useful B regime in this more informative world, with an eight-actor
ABA versus ABC occupancy control and explicit horizontal/vertical C geometry.
Start with actual compiler admission and a bounded exact-cost check; do not
automatically expand training, restore old caps or launch the old Chess panels.

This next feasibility step is begun: all three King-B ABA, ABC-H and ABC-V
eight-actor rules are admitted by actual Core, with 5/4/5 legal initial actions.
No new graph solve or training is claimed for them. A prospective 600-second,
300,000-position allowance per graph is a cost checkpoint, not an estimate
that every graph will complete.

Validation covers 174 relevant passing tests. Independent literal replay checks
all 4,608 new game records, 38,057 public PVs, 19,475 RNG choices and 3,072 TD
updates; all 65 censored game records retain UNKNOWN. The actual outgoing
selected rules, complete D4 tree, winning certificates and censoring-bound
arithmetic are checked separately. Optional GUI/native coverage is not claimed.
