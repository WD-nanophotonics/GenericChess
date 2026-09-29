# History sampling and position sampling give different context weights

**Unknown.** Could uniformly weighting reachable legal histories at a
fixed depth serve as a canonical context measure for a static material
prior? The smallest direct concern is whether distinct histories can
reach the same material-relevant position and therefore count it more
than once.

`scripts/audit_chess_history_weighting.py` uses executable Western Chess
RuleSet actions from the standard initial state. Four depth-four routes
commute White's `Ng1-f3` / `Nb1-c3` and Black's `Ng8-f6` / `Nb8-c6` in
their respective move orders. All four finish at equal
`Position` values, including side to move and auxiliary state. A fifth
legal route replaces Black's second knight move with `a7-a6` and ends
at a different position. All routes have four plies.

| Context measure on this declared five-route set | Shared knight position | Other position |
| --- | ---: | ---: |
| Uniform over histories | 4/5 | 1/5 |
| Uniform over distinct positions | 1/2 | 1/2 |

This is an exact **subset witness**, not the distribution over all
depth-four Chess histories. The `GameState` records different path
histories and repetition counters even when its `Position` agrees, so
the witness does not claim complete future-game equivalence. It does
show that a static prior conditioned on board/side/auxiliary position
gets different context weights from two seemingly natural measures.
Uniform histories is a valid *declared sampling policy*, but path
multiplicity then becomes part of the valuation assumption; rules do
not identify it with strategic visitation or utility. Uniform distinct
positions is another policy, likewise lacking a rule-given utility
interpretation. Neither measure can be silently substituted for the
independently justified comparison objective still needed after the
first-action service failure. No material references or Xiangqi
holdout values were used.
