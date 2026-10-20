# Standard Shogi static-profile owner-label symmetry — 2026-10-20

## Question and scope

Does the existing rule-only static profile change when a ruleset's physical
board is rotated 180 degrees, owner labels are exchanged, and owner-indexed
drop/promotion/forced-promotion masks are transformed with them? This tests
label symmetry of the profile on the production Standard Shogi ruleset, not a
whole-rule isomorphism or value-utility claim.

## Method and result

`data/profile_owner_rotation_shogi_20261020/probe.py` starts from
`build_standard_shogi_ruleset()`, rotates every occupied square and swaps each
piece owner, rotates and swaps both owners' 81-cell drop masks, promotion pairs
and forced-promotion squares, then rebuilds the profile for both rule inputs.
It compares all exposed per-piece fields for all14 types and the non-anchor
median. Every compared field is equal.

This fixture has active owner-specific restrictions: P and L drop masks each
allow72/81 squares per owner; N allows63/81. Promotion-pair counts are P27,
L189, N48, S123, B416, R594 per owner; forced counts include L9, N18, P9.
Thus the positive symmetry result exercises actual hand/drop and promotion
profile inputs, unlike the earlier Western fixture whose drop masks were empty.
Exact per-type values and masks are in `data/.../results.json`.

## Interpretation

The current profile is invariant on this symmetric production ruleset. A
separate deterministic sensitivity control removed one initially legal P drop
square for owner0 only, then applied the same owner swap/rotation. Only P's
`drop_freedom_ratio` changed (71/81 versus72/81); raw capability, normalized
board/hand price, promotion value and drop mobility did not. This owner-asymmetric
mutation is outside the generated-rule mask contract and is not evidence for a
price/default change.

Source inspection confirms `drop_freedom_ratio` and `drop_mobility` are profile
diagnostics; the Evaluator's static board/hand values use the shared normalized
price tables and do not consume these diagnostics. The transformation leaves
semantic action/declaration metadata untouched, so this is deliberately scoped
to the existing static-profile inputs, not full gameplay equivalence. No source
or default change follows. The focused `test_ai_evaluation.py` and
`test_standard_shogi_product.py` modules pass33 tests; pytest emitted only a
cache-write permission warning for the workspace `.pytest_cache`.

## Full evaluator side-frame check

Two additional fixed SFEN states contain a promoted piece and asymmetric hand
inventory, with owner0 or owner1 to move. For each, the production default
Evaluator was applied to (a) a 180-degree board rotation and owner swap while
keeping the same side-to-move label, and (b) that transform plus a turn swap.
The first score is the exact negative of the source score; the second preserves
the score, as expected when following the same actor's advantage. Scores are
-1381/+1381 and +1138/-1138 in the two original/mirrored pairs. These states
exercise static board/hand prices and default dynamic mobility, anchor escape
and promotion-potential terms. They are fixed evaluator fixtures, not game
outcomes or a utility/strength sample.

A focused regression was added to `tests/product/test_ai_evaluation.py` for both
fixtures. The joint evaluation and Standard Shogi modules pass34 tests. No
production evaluator or price change is justified. The exact small probe output
is in `data/profile_owner_rotation_shogi_20261020/evaluator_results.json`.
