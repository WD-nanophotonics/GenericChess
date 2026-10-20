# DEV_AUX task2615 — tighter finite-panel bounds for UNKNOWN endpoints

## Question and method

The task2606/2609/2610 paired summaries assigned the full `[-2,+2]` difference interval whenever either endpoint was UNKNOWN. That is safe but unnecessarily wide when the other endpoint has a known reward. This read-only reaggregation keeps every known reward fixed and varies only each UNKNOWN endpoint independently over `[-1,+1]`. It uses the same frozen matched strata, foe, slots and denominators. No game, search, training, or weight was generated, and old reports/data were not edited.

For endpoint reward sums `S = wins - losses`, unknown counts `U`, and `N` frozen paired slots, the exact finite-panel completion interval is:

`[(S_left-U_left-S_right-U_right)/N, (S_left+U_left-S_right+U_right)/N]`.

## Recomputed bounds

| Panel | Contrast | Recomputed blanket bound | Tight finite-panel bound |
|---|---|---:|---:|
| task2606 | TD95 − initial | +0.0117 to +0.3867 | +0.0742 to +0.3086 |
| task2606 | LocalLambda − initial | +0.1055 to +0.4492 | +0.1836 to +0.3555 |
| task2606 | LocalLambda − TD95 | −0.1328 to +0.2734 | −0.0391 to +0.1953 |
| task2609 | TD95 − initial | −0.0488 to +0.3809 | +0.0371 to +0.2793 |
| task2609 | LocalLambda − initial | +0.0430 to +0.4414 | +0.1191 to +0.3574 |
| task2609 | LocalLambda − TD95 | −0.1406 to +0.2891 | −0.0430 to +0.2031 |
| task2610 | TD95 − initial | +0.0469 to +0.4688 | +0.1328 to +0.3867 |
| task2610 | LocalLambda − initial | +0.0195 to +0.4414 | +0.1465 to +0.3809 |
| task2610 | LocalLambda − TD95 | −0.2441 to +0.2402 | −0.1387 to +0.1465 |

## Interpretation and limits

The point correction that changes the reading is task2609 TD95 − initial: its conservative lower bound on this exact frozen panel changes from negative to `+0.0371`. Thus TD95's observed advantage over initialization is positive for every completion of the saved UNKNOWN endpoint rewards on that panel. task2606 and task2610 TD95 − initial also have positive tight lower bounds. These are deterministic bounds on the existing finite panels, not confidence intervals, new independent samples, or population/generalization effects. Both trained methods still have positive bounds versus initialization in these panels, but every LocalLambda − TD95 bound continues to include zero; the relative learner-method ranking remains unresolved.

Independent audit PASS: all 8 previously published machine-summary intervals reproduced; all 3 saved game ledgers exactly match their frozen slot manifests and paired foes; all 9 tight bounds match the endpoint-sum identity. See `audit.json` and `audit.py`. Historical reports and the conservative bounds remain unchanged; this report supplements them with the sharper valid bounds.
