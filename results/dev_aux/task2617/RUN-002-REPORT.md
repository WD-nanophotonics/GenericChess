# DEV_AUX task2617 run-002 — randomized cap sensitivity

## Question and frozen conditions

On 32 fresh root families, does the assigned combined-both-sides endpoint cap (20k versus 40k nodes per slot) change endpoint W/L or the paired endpoint-minus-initial result? The run reused task2616's frozen initial/TD/WDL/TreeStrap endpoints, four seeds, uniform fixed foe and both learner colors. Cap was randomized by whole family (16 families per cap), with all four endpoints, seeds and colors retained within each family. The registered total was 1,024 slots; no inputs, caps, endpoints, or analysis rules were changed after launch.

## Execution

Run-001 failed before its first search call with `KeyError: ordering_seed_offset`; it has no game/query rows and zero paid nodes. It is preserved as a failed start. Run-002 repairs only that omitted deterministic ordering input by inheriting the frozen task2616 offset (`972568000`). Run-002 completed 1,024/1,024 slots, with no missing rows, 148,208 query receipts, 16,443,208 paid nodes, and 2,225.822 seconds under the registered 5,400-second cap. It observed 859 actual terminals and 165 UNKNOWN slots. UNKNOWN is not scored as a draw or quantity reward.

## Outcomes and finite-panel bounds

The registered analyzer's reward bounds and paired bounds use learner-perspective rewards. Its displayed `Actual L/D/W` count column instead counted the raw outcome from player 0's perspective. The separate [orientation audit](run-002/analysis-orientation-audit.md) reproduces the original counts, verifies each saved reward against learner color, and gives both player-0 and learner W/D/L counts; it does not change the preregistered analyzer or result. The original analysis remains available at [analysis.md](run-002/analysis.md).

UNKNOWN completion bounds for candidate-minus-initial, within each cap-assigned finite subpanel:

| Cap | Endpoint | Bound | Censored paired slots |
|---:|---|---:|---:|
| 20k | TD | [-0.203125, 1.171875] | 67/128 |
| 20k | WDL | [-0.257813, 0.960938] | 50/128 |
| 20k | TreeStrap | [-0.359375, 0.906250] | 62/128 |
| 40k | TD | [0.289063, 0.367188] | 5/128 |
| 40k | WDL | [0.179688, 0.195313] | 1/128 |
| 40k | TreeStrap | [0.007813, 0.039063] | 2/128 |

Each 40k candidate-minus-initial completion bound is positive on this registered 128-slot subpanel; each 20k bound crosses zero. This is a finite-panel statement, not a confidence interval or a population claim. The 40k-minus-20k bounds for all three endpoint reward means and all three endpoint-minus-initial contrasts cross zero. Thus this study does not establish a cap effect on strength. UNKNOWN falls from 159/512 slots at 20k to 6/512 at 40k, so the higher cap improves completion on this panel; that does not by itself establish a general strength effect.

## Reproducibility and limits

The registered reports remain frozen. The orientation audit is a post-run reporting supplement. Raw JSONL originals stay local; deterministic gzip copies under `run-002/published-traces/` are byte-exact after decompression and have a credential-pattern scan in `compressed-streams.json`. All claims are limited to this randomized finite 32-family panel; no confidence intervals, population effects, model selection, cap extension, retraining, or generic-rule transfer are claimed.
