# Geometric action inclusion does not establish task dominance

Under the prehashed MOVEMENT_INCLUSION_TASK_BOUNDARY_PROTOCOL.md, one sparse
Chess frame passed the common quiet screen for all five focal ordinary types.
All focal actions and opponent replies were exhausted for R and Q. R's legal
coordinate/promotion set is a strict subset of Q's, but complete task scores
are R=1,Q=0. There was no layout repair, weight adjustment or coefficient sweep.
The base is sandbox 432e6236bacaedcdbbb83cb28234b45b48cf9c7c plus the hashed
script. Raw evidence is data/movement_inclusion_task_boundary_20261003.json.

| Focal type | Same capture (3,3)->(3,4) | Immediate gain | Enemy check | Reply | Task |
| --- | --- | ---: | --- | --- | ---: |
| R | ongoing | +1 | no | K(7,6)->(6,7), ongoing | 1 |
| Q | stalemate | +1 | no | none | 0 |

Own K=(6,4), B=(5,5), enemy K=(7,6), target P=(3,4). The Queen on(3,4)
additionally controls(6,7) diagonally, while the other escape squares are already
controlled by own K/B. It does not check the enemy King. Thus the extra attack
creates an authoritative stalemate draw; the frozen task counts draw=0 despite
the immediate token gain. R leaves one escape and positive ongoing net custody.
Raw-position legal-action enumeration confirms both reply sets independently
of terminal GameState gating. 94 materializations include two public replays,
about 0.063 s under a 2,000/10-second cap. All other Q actions also fail this
task, so this is a complete local root-order reversal, not one selected action.

## What this changes

The optional-action monotonicity proof in SECURED_EXCHANGE_TASK_CONTRACT.md
remains valid: adding an action while preserving all prior successor/payoff
semantics cannot decrease max-min success. R-to-Q replacement does not satisfy
that premise. The same coordinates now reach a different typed Position with
different attack relations, opponent legality and terminal result. Queen cannot
choose to switch off its diagonal attacks after the capture. Coordinate-event
inclusion therefore is not full transition/payoff simulation dominance.

Do not demand pointwise Q>=R for this task merely from movement inclusion, or
call this reversal an implementation failure of the optional-action theorem.
Validate genuine unchanged-action dominance only after its semantic premise
is proved. The broader material prior is an approximation and could still
differentiate types usefully under a justified common population; this one
context supplies no population mean or human-value judgement.

This sparse semantic frame is outside the earlier full-inventory sampling law.
Do not mix it into that law's records or use it to change context weights.
Keep the nonterminal full-inventory support controls as a separate result.
The remaining question is an independently justified strategic population and
static use criterion, not another type-ranking or stalemate construction.
