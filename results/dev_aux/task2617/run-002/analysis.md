# DEV_AUX task2617 finite-panel cap analysis

This report is descriptive for the frozen randomized 32-family panel. It is not a confidence interval or a population claim. UNKNOWN and missing slots remain censored; only actual terminal W/D/L is scored.

Observed game rows: 1024/1024; missing: 0; paid nodes from query receipts: 16,443,208.

## Endpoint reward bounds by assigned cap

| Cap | Endpoint | Lower | Upper | Censored | Actual L/D/W |
|---:|---|---:|---:|---:|---|
| 20000 | initial | -0.351562 | 0.335938 | 44/128 | 33/13/38 |
| 20000 | TD | 0.132812 | 0.820312 | 44/128 | 41/5/38 |
| 20000 | WDL | 0.078125 | 0.609375 | 34/128 | 40/12/42 |
| 20000 | TreeStrap | -0.023438 | 0.554688 | 37/128 | 40/15/36 |
| 40000 | initial | 0.257812 | 0.273438 | 1/128 | 57/23/47 |
| 40000 | TD | 0.562500 | 0.625000 | 4/128 | 49/14/61 |
| 40000 | WDL | 0.453125 | 0.453125 | 0/128 | 54/16/58 |
| 40000 | TreeStrap | 0.281250 | 0.296875 | 1/128 | 58/14/55 |

## Endpoint-minus-initial paired bounds

| Cap | Endpoint | Lower | Upper | Censored pairs |
|---:|---|---:|---:|---:|
| 20000 | TD | -0.203125 | 1.171875 | 67/128 |
| 20000 | WDL | -0.257812 | 0.960938 | 50/128 |
| 20000 | TreeStrap | -0.359375 | 0.906250 | 62/128 |
| 40000 | TD | 0.289062 | 0.367188 | 5/128 |
| 40000 | WDL | 0.179688 | 0.195312 | 1/128 |
| 40000 | TreeStrap | 0.007812 | 0.039062 | 2/128 |

## 40k minus 20k finite-panel bounds

No interval below is a statistical confidence interval.

| Quantity | Lower | Upper |
|---|---:|---:|
| initial mean reward | -0.078125 | 0.625000 |
| TD mean reward | -0.257812 | 0.492188 |
| WDL mean reward | -0.156250 | 0.375000 |
| TreeStrap mean reward | -0.273438 | 0.320312 |
| TD minus initial contrast | -0.882812 | 0.570312 |
| WDL minus initial contrast | -0.781250 | 0.453125 |
| TreeStrap minus initial contrast | -0.898438 | 0.398438 |
