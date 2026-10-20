# Static-board promotion-potential interaction utility — 2026-10-21

## Question and frozen contrast

Does the existing rule-derived promotion-potential bonus merit retention when the scoped static-v2 board prices are active in the leaf evaluator? The pre-registered 64-slot panel held static-v2 board values, Unit hand values, profile-derived promotion gains, dynamic terms, capture/target ordering, opponent and search limits fixed. Only `promotion_potential_weight` changed, 0 versus 3; the fixed foe used the bonus-off evaluator in both arms. Eight fresh generated 5x5 rules (seeds 622099–622106), 16 unfiltered legal-random roots (9/12-ply prefixes), both candidate owners, D3/8192-node/0.5-second/q0, TT off, and a 48-candidate-ply horizon were used. The plan expected 600 seconds with a 3600-second cap; actual elapsed time was 272.719 seconds. Source HEAD: `e009c4a531aebd21bf8d07cb2115b43786cc3d94`; plan SHA-256: `91F12E3C7F6B8027ED1060647F572234049785F7ABB0A50A8947F63BE9066191`.

This interaction was worth testing because the earlier bonus-only panel evaluated Unit board values, while the integrated static package changed board prices, hand prices, bonus and ordering together. Neither can identify the bonus effect under the retained static-board candidate.

## Results

All 64 slots completed: 52 actual terminal wins/losses and 12 retained horizon UNKNOWNs; no draws, invalid actions, replay mismatches or unstarted slots. Both arms had identical marginal outcomes (13 wins, 13 losses, 6 UNKNOWN). All 26 resolved paired outcomes had reward difference 0; all 6 unresolved pairs were UNKNOWN in both arms. The UNKNOWN-aware reward-difference bounds were `[-0.375,+0.375]` overall, `[-0.375,+0.375]` for each owner, `[-0.25,+0.25]` for odd roots and `[-0.5,+0.5]` for even roots. No candidate first action changed in 26 comparable pairs. The bonus was nonzero in 8/16 roots, with signed deltas from -2 to +2.

Both predeclared retention gates failed. Median candidate-node reduction was 0 in every view; aggregate candidate nodes fell from 449,302 to 448,787 (0.115%), with opposite small owner-level shifts. Candidate search time increased from 63.673 to 65.093 seconds (+2.23%), and total caller time from 126.801 to 128.163 seconds (+1.07%). These elapsed values are sums of measured `choose_action` times, not a separately controlled machine-wall benchmark.

## Independent validation and decision

The public analyzer preserved all slots and calculated the predeclared owner/parity/leave-one-seed-out bounds. A separate audit regenerated all 8 rules and profiles and replayed all 64 complete serialized histories across 16 roots: PASS, zero invalid actions and zero replay mismatches. The full games JSONL SHA-256 is `BE89BE5DE696E8D12FD095FB8F06720822E08B95AACCF58B029FFEC484576D88`. The completion receipt is `data/static_board_promotion_bonus_utility_20261021/promotion-bonus-run/execution-closure.json`; its start-only `execution-start.json` status is not authoritative for final state.

Do not retain the promotion-potential bonus as part of this scoped static-v2 5x5 candidate and do not change the global evaluator default. This finite result shows no resolved paired reward or first-action benefit in this sample, uncertain bounds due to UNKNOWNs, and no measured cost improvement. It does not establish that promotion distance has no value in other rules, budgets or generated-rule domains.

## Relation to prior work and limits

Pell's primary report on METAGAMER distinguishes position-independent static material values from dynamic promote-distance advice: it notes that the static pawn price is low when promotion value is excluded, while the dynamic advisor is used during play. Its generated-game tournament reports an advantage for the full-knowledge evaluator despite higher evaluation cost, but the evaluator bundles multiple advisors and does not isolate promotion or transfer a numeric ratio to this project. See [Pell, “A Strategic Metagame Player for General Chesslike Games”](https://cdn.aaai.org/AAAI/1994/AAAI94-212.pdf), pp. 1380–1383. This motivates separating the mechanisms; it does not override the present scoped outcome result.
