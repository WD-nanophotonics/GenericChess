# F117 Shogi Gumbel Completed-Q Policy Improvement Arena2

Status: `SHOGI_GUMBEL_COMPLETED_Q_POLICY_ITERATION_ARENA2_REJECTED`

F117 replaced F116’s visit-count/Q-only policy update with the specified
completed-Q Gumbel improvement loop. Root halving ranks candidates by
`gumbel + parent_logit + sigma(Q)`, where
`sigma(Q) = (50 + Nmax) * 0.1 * Q`. The training target is the full legal
action softmax of `parent_logit + sigma(completedQ)`; completedQ uses empirical
Q for visited actions and the frozen root value for unvisited actions. The
historical visit policy is retained only for diagnosis.

Frozen inputs and result:

- F117 baseline: `58770b273ed8fbc1299a914b6d4fc54943166dae`
- value checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
- parent policy: `2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955`
- candidate policy: `f4ed13924813ede88073cd7f330c66de6922eda46132d53712fd1d207123fbf5`

Correctness gates passed: 64 simulations were consumed, the corrected
8→4→2→1 schedule remained green, all completed-Q values were finite and
bounded, improved targets had full positive support and unit sum, and Native/
Python logits matched across 100 positions with maximum error
`4.440892098500626e-15`. Generic Shogi, Western Chess, and lowered-semantic
smokes remained legal and deterministic.

The diagnostic rerun on 64 persisted F116 roots found only 4.6875% selected
action agreement between the F116 Q-only selector and F117’s improvement-score
selector. Mean `KL(visit_policy || completed_q_policy)` was 2.64771, and the
completed-Q target placed 0.5344 mean mass outside F116’s initial top-eight
candidate set.

Fresh F117 self-play produced 192 train, 62 dev, and 64 holdout informative
roots. Full-batch Adam used 100 steps, learning rate `0.001`, proximal
coefficient `0.001`, and seed `1170111`; alpha `1` passed the parent-anchored
train/dev gates. CE/KL to the completed-Q target were:

| split | parent CE | candidate CE | parent KL | candidate KL |
|---|---:|---:|---:|---:|
| train | 3.214965 | 2.949798 | 0.793818 | 0.528652 |
| dev | 3.382505 | 3.323560 | 0.758260 | 0.699314 |
| holdout | 3.526189 | 3.535355 | 0.754734 | 0.763901 |

The completed-Q policy-improvement diagnostic was positive on every split:
mean expected-value deltas were 0.4544 train, 0.4515 dev, and 0.4334
holdout, with 100% nonnegative roots. The old visit target was weaker and had
negative holdout mean delta (-0.0415).

Arena2 used requested opening seed `1170801` (selection offset 0), search
seeds `1170901 + 10000*g + p`, two role-swapped pairs, and the 512-ply safety
boundary. All four games were valid checkmates at 107, 265, 201, and 67
plies. Pair scores were `0.5, 0.5`, mean `0.5`, with zero child-better and
zero child-worse pairs. The candidate therefore failed the strength gate,
despite valid completed-Q policy-improvement and termination behavior.

Full root, transform, completed-Q, training, consistency, and arena telemetry
is retained in `.generic_chess_flow/f117-shogi-gumbel-completed-q-arena2/report.json`.
No promotion or Arena4/8 follow-up is authorized by this result.
