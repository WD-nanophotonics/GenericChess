# DEV_AUX task2616 — Chess TreeStrap finite-panel evaluation

## Question and frozen design

Does the registered Chess TreeStrap arm improve actual fixed-foe W/L over its seed-matched initial weights, TD and WDL controls? The four learner endpoints were compared on the same 256 registered pairs each (32 disjoint evaluation families × 4 seeds × 2 colors; uniform fixed foe). Search settings and source pins are in `plan.json`, `eval-plan.json`, and the start/binding receipts. Evaluation was capped at 3,600 seconds; no caps or inputs were changed.

## Execution and audit

Training completed all four 1,000,000 candidate+foe-node budgets: 4,000,000 nodes, 242 games, 36,992 queries, 18,491 complete candidate receipts used for TreeStrap updates, and 48 censored/nonterminal UNKNOWN games, in 532.797 seconds. The 1,024-slot evaluation completed with no missing slots: 14,648,460 nodes, 123,850 queries, 712 actual terminal games and 312 UNKNOWN slots in 1,883.679 seconds. Combined search time was 2,416.476 seconds (40.27 minutes); this is the sum of sequential training/evaluation runtimes, not an end-to-end process wall-clock claim. Both phases remained within their registered caps.

The independent replay audit `audit_v2.py` PASSed: it reproduced 36,992 training-query updates and 4,000,000 paid nodes; replayed all 242 UCI histories/terminal outcomes; and checked all 1,024 registered evaluation slots, 123,850 queries, rewards, paid nodes and bindings. The frozen `audit.py` was preserved unchanged but cannot run on this output schema: it expects a `weights_after` key which `train_tree.py` does not emit. The retrospective v2 audit instead checks every logged pre-query weight against replay state, chains each per-game initial/final snapshot, and checks final arm weights.

## Actual outcomes and finite-panel completion bounds

W/D/L/UNKNOWN counts by endpoint:

| Endpoint | Wins | Draws | Losses | UNKNOWN |
|---|---:|---:|---:|---:|
| Initial weights | 107 | 19 | 44 | 86 |
| TD | 140 | 13 | 21 | 82 |
| WDL control | 142 | 12 | 34 | 68 |
| TreeStrap | 122 | 24 | 34 | 76 |

For each paired endpoint contrast, known outcomes (including draws) are fixed; only UNKNOWN endpoint rewards vary independently over [-1,+1]. These are exact completion bounds for this finite registered panel, not confidence intervals or population effects.

| Contrast (left − right) | Mean bound over 256 pairs | Both known | At least one UNKNOWN | Missing pairs |
|---|---:|---:|---:|---:|
| TreeStrap − initial | [-0.5352, +0.7305] | 132 | 124 | 0 |
| TreeStrap − TD | [-0.7383, +0.4961] | 133 | 123 | 0 |
| TreeStrap − WDL | [-0.6406, +0.4844] | 145 | 111 | 0 |
| TD − initial | [-0.4375, +0.8750] | 131 | 125 | 0 |
| WDL − initial | [-0.4258, +0.7773] | 157 | 99 | 0 |

Every interval crosses zero. This finite-panel study therefore does **not** establish that TreeStrap, TD or WDL improved actual strength over the paired alternatives. It also does not establish a stable learned price ordering: TreeStrap's four final vectors differ materially by seed. Training losses are diagnostics only and were not used to choose models.

## Evidence handling and limits

Raw `*.jsonl` traces remain locally available for replay and are not staged because the query streams exceed GitHub's per-file size limit. Deterministic gzip publication copies and their byte/hash/row manifest preserve the full traces. The local originals were left untouched. The run contains no human-price fitting, chess-human holdout, prover, or search-bound-as-exact-label use. It tests one standard-Chess protocol, four seeds, one fixed foe and a finite root panel; all broader transfer and population claims remain OPEN.

The pre-run registration test expects `tree-started.json` and `eval-started.json` not to exist. It is inapplicable after the registered run started; the other 20 focused learner/episode/runner/UNKNOWN tests passed. No pinned source or registered cap was changed.
