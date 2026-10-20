# Staged promotion-target ordering utility on generated rules — 2026-10-21

## Question and frozen contrast

Does the existing static-v2 type_value promotion-target order merit retention on the opt-in StagedMovePicker path? The sealed 64-slot contrast changed only target-order price values; Unit leaf values, capture order, Unit foe, legal actions, dynamic terms, D3/8192 nodes/0.5-second search/q0 and TT-off conditions were fixed across 8 fresh generated 5x5 seeds (622059–622066), 16 roots, both candidate owners. Expected runtime was 600 seconds under a 3600-second cap; actual runtime was 246.656 seconds. No product/default changes followed.

## Results

All 64 slots returned: 57 actual terminals, 7 UNKNOWN, zero invalid actions, replay mismatches, or unstarted slots. The preflight exposed multi-promotion states and changed 12 root target orders across the 8 rules, but the outcome panel changed 0/27 comparable first candidate actions. The overall finite utility bound was [-0.25,+0.1875] with 4 UNKNOWN pairs; owner 0 [-0.25,+0.125], owner 1 [-0.25,+0.25], odd parity [-0.25,+0.125], and even parity [-0.25,+0.25]. The predeclared utility and cost retention gates both failed. Median paired node reduction was 0 in the overall and every reported owner/parity view.

## Decision and scope

Do not retain staged promotion-target ordering as a price candidate and do not change defaults. This is a finite utility result for the sampled 5x5 rules and budgets; it does not imply that price ratios are generally irrelevant or invalidate scoped static leaf candidates. Do not rerun this panel or select favorable strata.

## Reproducibility

Plan, order-exposure preflight, producer, analyzer, complete game records and independent audit are in data/static_staged_promotion_order_utility_20261021/. Independent replay regenerated 8 rules/profiles and verified all 64 histories, 16 roots, zero invalid actions and zero mismatch flags. Source HEAD was d76174241b534ecda62c94a1185a47b765a39813; code/test contents in generic_chess and tests were unchanged through current HEAD e009c4a531aebd21bf8d07cb2115b43786cc3d94 at audit time.
