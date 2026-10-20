# Rule-derived hand-price utility on generated 5x5 rules — 2026-10-21

## Decision

Close this finite hand-only channel test. Do not adopt rule-derived hand values as a scoped evaluator candidate or change defaults from this panel. Keep all 64 planned games and the one UNKNOWN in the denominator.

The candidate changed only `hand_value_by_base_type`: both candidate arms used Unit board values, zero promotion gain, the same default capture/type ordering, dynamic mobility and anchor-escape weights, search settings and complete histories. The fixed foe used the Unit evaluator. This isolates hand values from the already tested board, promotion, ordering and integrated-package contrasts.

## Frozen design and validation

The pre-run plan is [`price_package_plan.json`](data/static_hand_price_utility_20261021/price_package_plan.json), SHA-256 `2C481B16D1EC22CB8E3846BADCDE770F0033B6F32E7A17A71024D53676605D8A`. It uses eight fresh generated 5x5 rule seeds (622083–622090), two deterministic legal-random roots per seed (prefix plies 9 and 12), both candidate owners, and both arms: 64 games / 32 paired root-owner units. No root, outcome, drop, action or promotion-exposure filter was applied. Search was D3, 8192 nodes, 0.5 s, q0, TT off, ordering on. The frozen experiment cap was 3600 s.

The run used source HEAD `d76174241b534ecda62c94a1185a47b765a39813`; it ran 171.657 s from `2026-10-20T17:04:11.442Z` through `2026-10-20T17:07:02.980Z`. All 64 slots completed: 63 terminal and 1 UNKNOWN, with zero invalid actions, unstarted slots, or full-history replay mismatches. The game JSONL SHA-256 is `0D6524B66E6475ACE031A037A277E2F0CEFB4967C70E24368A23DE07D1FABCF2`; result SHA-256 is `B35D8D455BED13C7C83E31063CF75343E73CFF13C48997B58A0E559513FFBBAA`; analysis SHA-256 is `7A13EE0ACD4BE6DDCA8763709E724AB0F3A3190607C5D53AB0B3E2A870CB6FEC`. Independent checks confirmed plan/source hashes, all 32 paired roots, all 8 profile-isolation assertions, and replay equality for every game. The exact plan, producer, analyzer, profiles, rules, roots, records and receipts are in the [evidence bundle](data/static_hand_price_utility_20261021/).

## Results

| View | Paired units | Conservative utility difference, hand-only − Unit | Median candidate-node reduction |
|---|---:|---:|---:|
| Overall | 32 | [−0.3125, −0.2500] | 0.00% |
| Candidate owner 0 | 16 | [−0.3750, −0.2500] | −2.45% |
| Candidate owner 1 | 16 | [−0.2500, −0.2500] | 0.00% |
| Odd-ply roots | 16 | [−0.3750, −0.3750] | 0.00% |
| Even-ply roots | 16 | [−0.2500, −0.1250] | −0.21% |

The strict utility gate required positive lower bounds overall, by owner, by parity and for every leave-one-seed-out view; it failed. The cost gate required at least 10% median node reduction in every such view and no negative utility lower bound; it failed. Candidate-arm game outcomes were 11 wins, 20 losses and 1 UNKNOWN, versus 16 wins and 16 losses for the Unit-arm games. First actions differed in 10 of 23 comparable candidate states, which did not translate to utility or robust median cost gains.

A drop-availability split, kept exploratory and never substituted for the full denominator, showed 22 no-legal-drop root-owner pairs with exact utility difference −0.455 and 10 drop-available pairs with bounds [0,+0.20], one UNKNOWN, and median node reduction −0.21%. This small stratum does not justify a drop-conditioned evaluator. Per-seed outcomes are heterogeneous; do not select or rerun a favorable subset.

## Scope and next step

This is one finite generated 5x5 sample against a fixed Unit foe. It does not establish a population-wide hand-price law, all-domain transfer, or a global default. No product code, prices, generator, training or model changed. The previous board-only, promotion, capture-order and integrated-package panels remain distinct; their results are not pooled into this hand-only gate.

The next mainline question moves to unfamiliar-rule search stability: does public AlphaBeta reuse a warm transposition entry across same-board, same-ply legal semantic states whose auxiliary slots differ? Existing identity tests show auxiliary values affect the canonical key, but the current inventory does not show this paired public warm-search case. The existing `castling_ruleset()` fixture is unsuitable: its only moving pieces for the rights owner are the king and rook, and either leaving its home square clears the slot, so it cannot supply two equal-board/equal-ply histories with differing rights. First identify a public legal fixture with an auxiliary-changing action and an independent reversible movement; compare shared-warm and cold search results only if both histories can be replayed through public APIs. This can close the suspected key-reuse gap or expose actual cross-identity reuse; do not fabricate state or run a timing sweep.
