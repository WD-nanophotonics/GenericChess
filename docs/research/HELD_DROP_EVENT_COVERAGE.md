# Shogi held-token drop event boundary

## Bounded question

Can the compiled Standard Shogi RuleSet supply a game-independent
hand-to-board event identity and target-square mask without treating a
coarse event as a fully legal drop? The direct observation is the seven
base types' compiled drop patterns and owner masks. No material values,
search outcomes, or human references are inputs.

`collect_intrinsic_held_drop_events` records an event keyed by owner,
held type, hand source, target square, empty target condition, and
resulting board type. It requires the one-for-one `remove_from_hand` and
`place(target)` effect pair, verifies the type binding, and applies the
compiled owner-specific allowed-square masks. It aborts above 1,000
targets per type. The resulting ledger is a set of **coarse intrinsic
options**, with one `target empty` occupancy cube per option. No
hand-conditioned occupancy probability has been defined.

| Held type | Drop targets, both owners |
| --- | ---: |
| P | 144 |
| L | 144 |
| N | 126 |
| S | 162 |
| G | 162 |
| B | 162 |
| R | 162 |

All seven have zero unsupported intrinsic effect or mask forms. The
promoted `TP` has zero allowed drop squares and contributes no held
event. Chess B and Xiangqi C likewise have only compiler-emitted,
mask-disabled legacy drop patterns; these are recorded as disabled.

Shogi pawn's `standard_drop_contract` additionally tests the same-file
unpromoted-pawn state guard and has postconditions for check and no
legal reply. Those conditions, plus dynamic own-anchor safety, are
explicit exclusions in this static coarse ledger. Other held types
also retain their dynamic own-anchor safety exclusion. Existing
executable RuleSet tests cover such legal constraints; the coarse
ledger does not claim to reproduce them or actual drop frequencies.

The board-event ledger already distinguishes `capture_to_hand` from
`remove_from_game` by physical disposition. That does not itself give a
cardinal board-versus-hand conversion rate or a distribution over held
states. Before a cross-mode material prior, declare a hand-conditioned
context measure and test its relation to the board measure. Do not
impute the missing state guards as satisfied with probability one.
