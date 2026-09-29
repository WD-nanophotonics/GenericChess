# Xiangqi static-event versus executable-legality boundary

## Smallest direct observation

The intrinsic physical-event ledger covers compiled Xiangqi movement,
screens, leg/eye blockers, and zones but excludes dynamic
`own_anchor_safe`. Does that exclusion change the available actions in
an actual position? `scripts/audit_xiangqi_intrinsic_legality_boundary.py`
evaluates the existing occupancy cubes against two exact board states,
then compares `(type, source, destination)` with public `legal_actions`
from the executable diagnostic RuleSet. It computes no material value
and reads no Xiangqi human-value reference.

| State, owner 0 | Intrinsic non-anchor actions | Legal non-anchor actions | Intrinsic only | Legal only |
| --- | ---: | ---: | ---: | ---: |
| Standard initial position | 43 | 43 | 0 | 0 |
| Soldier at (4,5) is sole screen between Generals (4,0) and (4,9) | 3 | 1 | 2 | 0 |

In the second state, the static ledger admits the Soldier's lateral
moves from index 49 to 48 and 50. Each removes the only screen on file
4 and exposes the moving side's General to the opposing General. Public
`legal_actions` correctly rejects both. The Soldier's forward move
remains legal. The initial equality is a useful local consistency
check; it does not prove global ledger completeness.

## Consequence

An intrinsic event probability is an optimistic local capability, not
a probability of a fully legal action under a distribution of game
states. The missing safety filter can be material-relevant because its
effect depends on board context. A later prior must either model
state-conditioned safety under a declared context measure or keep the
optimistic scope explicit and validate its bias. Applying a constant
piece correction from this two-state witness would be unjustified.
