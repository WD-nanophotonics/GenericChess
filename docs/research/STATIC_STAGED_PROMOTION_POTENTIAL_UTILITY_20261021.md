# Rule-derived promotion-potential utility on generated rules — 2026-10-21

## Question and frozen contrast

Does the existing rule-derived promotion bonus, enabled by the default promotion_potential_weight=3, improve finite-budget outcomes over a Unit board/hand evaluator on fresh generated rules? The completed 64-slot panel changed only this existing bonus (weight 0 versus 3); Unit board/hand values, capture ordering, promotion target ordering, dynamic terms, legal actions and fixed Unit foe stayed identical. It used seeds 622067–622074, 16 unfiltered deterministic legal-random roots, both candidate owners, D3/8192 nodes/0.5-second search/q0, TT off and a 48-ply horizon. Expected runtime was 600 seconds below a 3600-second cap; actual was 242.860 seconds. This panel was already complete in PRIMARY-private storage and was not rerun.

## Results

All 64 slots returned: 53 actual terminals and 11 retained horizon UNKNOWNs; no invalid actions, replay mismatches or unstarted slots. The profile-derived bonus was nonzero in 12/16 roots. Despite that mechanism exposure, the first candidate action changed in 0/24 comparable paired states.

Rule-derived bonus minus bonus-off finite reward bounds were [-0.375,+0.3125] overall (7 UNKNOWN pairs), [-0.125,+0.5] for owner 0, [-0.625,+0.125] for owner 1, [-0.25,+0.25] for odd roots and [-0.5,+0.375] for even roots. Both predeclared utility and cost gates failed; median paired candidate-node reduction was 0 overall and in the owner strata. Observed W/L/U was 13/12/7 with the bonus and 14/14/4 without it. This does not support retaining the bonus as a scoped strength candidate.

## Audit, decision and limits

The public analyzer rerun was byte-identical to the private source analysis. An independent audit regenerated all 8 rules and profiles and replayed all 64 full histories across 16 roots, with zero invalid actions or mismatch flags. The run is bound to source HEAD d76174241b534ecda62c94a1185a47b765a39813; generic_chess and tests were unchanged through e009c4a531aebd21bf8d07cb2115b43786cc3d94 at audit time. Public copies of the frozen plan, source, records and reports were scanned for personal paths, email and credential patterns. Their SHA-256 manifest and completion interpretation are in data/static_staged_promotion_potential_utility_20261021/promotion-potential-run/execution-closure.json.

Do not retain or enable this rule-derived bonus from this sample, and do not rerun these roots. The producer's execution-start.json still says ACTIVE because it is a start-only receipt; it is not an open-process signal. result.json records COMPLETE and all 64 returned slots. This is bounded finite evidence, not a universal promotion-price law, WDL proof or all-domain claim.
