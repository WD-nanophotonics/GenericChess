# DEV_AUX task2617 outcome-orientation audit

This post-run supplement does not alter the preregistration, frozen analyzer, original analysis, or evaluation outputs.
The reward bounds were already calculated from learner-perspective rewards. Only the displayed `Actual L/D/W` counts in the original table used the unflipped outcome field.

For this Chess adapter, player 0 is White and the terminal outcome is +1 for a White win, 0 for a draw, and -1 for a Black win. The slot color is the learner's color (0=White, 1=Black).

Observed rows: 1024; actual terminals: 859; censored UNKNOWN: 165.

| Cap | Endpoint | Player-0 L/D/W (original count perspective) | Learner L/D/W | UNKNOWN censored |
|---:|---|---:|---:|---:|
| 20000 | TD | 41/5/38 | 9/5/70 | 44/128 |
| 20000 | TreeStrap | 40/15/36 | 21/15/55 | 37/128 |
| 20000 | WDL | 40/12/42 | 19/12/63 | 34/128 |
| 20000 | initial | 33/13/38 | 36/13/35 | 44/128 |
| 40000 | TD | 49/14/61 | 17/14/93 | 4/128 |
| 40000 | TreeStrap | 58/14/55 | 38/14/75 | 1/128 |
| 40000 | WDL | 54/16/58 | 27/16/85 | 0/128 |
| 40000 | initial | 57/23/47 | 35/23/69 | 1/128 |

UNKNOWN slots are not counted as draws or learner outcomes. All rows remain in the fixed 128-slot denominator used by the finite-panel bounds.
This is a descriptive finite-panel correction, not a confidence interval or population estimate.
