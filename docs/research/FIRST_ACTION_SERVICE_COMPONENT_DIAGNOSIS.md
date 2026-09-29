# Why first-action service did not repair the static prior

## Smallest direct observation

After the frozen Chess gate failed, compare the pilot's exact raw board
values with the already-frozen V2C successor-option totals, type by
type. This is a decomposition of two pre-existing rule-derived
artifacts, not another candidate run or human-value fit. The local V2C
candidate `.generic_chess_flow/static-semantic-material-prior-v2c-board.json`
has SHA-256
`ca8a87b5acd872feaf951e7fbb2a2f41e812059c2458b6e48a3e060bfdd7e1d1`.
The pilot's frozen exact vector and source hashes are in
`data/first_action_service_chess_shogi_preref.json`.

The pilot/V2C raw ratio is exact:

| Chess type | Ratio |
| --- | ---: |
| P | `306183/321404` ≈ 0.9526 |
| B | `1/2` |
| N | `1` |
| R | `1` |
| Q | `1` |

For **all thirteen** Standard Shogi non-anchor current types (P, L, N,
S, G, B, R, TP, TL, TN, TS, TB, TR), the same ratio is exactly `1`.
Thus the action-conditioned reach factor leaves the frozen V2C board
vector unchanged in Shogi. In Chess it changes little except halving
B for its permanent color class. Chess knight, rook, and queen can
eventually access every board square from each positive first result
in the optimistic directed graph, so their factor is one. The bishop
cannot change square color, giving a factor of one half. Pawn's
promotion and forward restrictions leave a smaller correction.

This exact reduction explains the observed gate pattern. The new
metric did not add a general estimate of strategic material usefulness:
it mostly inherited V2C's action-count behavior and applied one blunt
topological penalty. The Chess B/P ratio moved from the historical V2D
high side to 2.2076, below its frozen lower band; N/P 3.7421 and R/P
6.1245 remain above their upper bands. The Shogi gate pass is not an
independent confirmation of the new reach objective, because its
vector exactly equals V2C's board vector.

The evidence rejects this route-count formula as a sufficient static
material prior. A successor must have an independently motivated
mechanism that responds to action cost, reply/survival, or another
game-relevant consequence; changing the reach horizon, bishop factor,
promotion branch weight, or target distribution solely to repair these
ratios would be tuning. Xiangqi human values remain sealed.
