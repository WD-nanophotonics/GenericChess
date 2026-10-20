# task2625 — fixed-scale Generic TDLeaf versus initialization

Status: complete finite-panel comparison; Generic strength/generalization remain
open. No product default, PRIMARY or DEEPSEEK state changed.

## Registration and execution

This was a fresh, separately registered task after the task2622 schema failure
and task2623 partial interruption. It used task2624's outcome-blind replacement
pool: four existing generated 4x4 rules, 120 training and 16 evaluation roots
per rule, with exact full-history training/evaluation start disjointness and
prior-record exclusions. The pool audit replayed 544 roots from 43 source hashes
and found zero train/evaluation intersections. The task2625 plan SHA is
`9cca31fae284f8f88120a58c8128294455346f1a1bc4c813a30c12cf111e0b3f`; registration
SHA is `340b1decf71cabd5d21ced72aec92739b7250d8392470ad1c2744c04772231ec`.

Training ran once and completed all 16 rule/seed arms at 250,000 combined
candidate-plus-foe nodes each: 4,000,000 nodes, 66,797 queries, 3,693 episodes,
3,579 actual rule-terminal outcomes and 114 UNKNOWN. Elapsed producer time was
1,750.237 seconds, below the registered 2,400-second training cap. Independent
replay passed full histories, actual-terminal/UNKNOWN accounting, per-arm node
caps and TD updates reconstructed from logged complete search receipts. This
audit does not independently rerun every search target.

Only after that audit passed, the registered evaluation was bound to the frozen
training result and run once: 1,024/1,024 slots, 1,254,951 nodes, 22,305 queries,
980 actual terminal games, 44 UNKNOWN and zero missing slots in 555.656 seconds
(under the 3,600-second hard limit). No evaluation slot reached its per-root
node cap. The independent `PASS_1024_SLOT_ACTUAL_TERMINAL_HISTORY_AND_CAP_AUDIT`
replayed legal actions and complete `GameSession` histories, checked rule
terminal authority, endpoint-relative rewards, all source pins, and node/query
totals. Every UNKNOWN remains censored.

Across the 512 preregistered pairs (rule, seed, root family and learner color),
472 pairs have two actual outcomes and 40 include at least one UNKNOWN. The exact
finite-panel TDLeaf-minus-initial reward-sum completion bounds are [61,149], or
mean `[61/512,149/512]` = `[0.1191,0.2910]`; the lower bound stays positive when
each UNKNOWN endpoint independently ranges over [-1,+1]. This is not a
confidence interval, population effect, or evidence of broad Generic transfer.
Endpoint W/L/D/UNKNOWN counts are:

| Endpoint | Wins | Draws | Losses | UNKNOWN |
| --- | ---: | ---: | ---: | ---: |
| TDLeaf | 295 | 2 | 188 | 27 |
| Initialization | 248 | 1 | 246 | 17 |

Descriptive exact completion bounds by rule show that three rule slices are
strictly positive, while rule271003 remains unresolved because 35/128 pairs
contain UNKNOWN:

| Rule | Pairs with UNKNOWN | Mean reward-difference bounds |
| --- | ---: | ---: |
| 271001 | 5/128 | [0.2578, 0.3359] |
| 271002 | 0/128 | [0.4688, 0.4688] |
| 271003 | 35/128 | [-0.3438, 0.2656] |
| 271004 | 0/128 | [0.0938, 0.0938] |

All four descriptive seed slices have positive lower bounds: seed1977
[0.0234,0.2266], seed8173 [0.2422,0.4453], seed27182 [0.2031,0.3281] and
seed31415 [0.0078,0.1641]. Roots and seeds are crossed; these are finite slice
descriptions, not independent estimates.

The 44 UNKNOWN endpoint slots are all `HORIZON_UNKNOWN` at the registered H=128;
none was a rule terminal and none hit a node cap. Rule271003 contributes 39/256
UNKNOWN endpoints (15.23%); rule271001 contributes 5/256, while rules271002 and
271004 have none. The horizon censoring is correctly retained and cannot be
resolved by relabeling those games as draws.

## Cost and limits

Training plus evaluation producer time was 2,305.894 seconds (38.43 minutes),
before setup and audit overhead; the source-pinned prospective whole-task
estimate was 66.70 minutes. Both remain below the 120-minute Chat assessment
threshold, with the registered caps unchanged. The experiment covers only four
existing generated 4x4 rules and exact start-record disjointness. It does not
establish complete generated-domain coverage, descendant-state independence,
transposition independence, population effects, stable piece prices or an engine
default. The 271003 result remains uncertain at H=128. The task2622 failure and
task2623 partial run are preserved as separate failures/partial evidence and
were not retried, topped up or reused as training results.

## Reproducible evidence

- `run/training-result.json` SHA256: `760bb829c2f0424b6e780f1541a6fe70fe7b824c998b0671e5c9794108b84304`
- `run/training-audit.json` SHA256: `87d09877ca88d473d44ec472f3de62085f2fdea7a1d9998b9e7a529f69210439`
- `run/eval-result.json` SHA256: `e4ac648f12a4609d19e6176cb1a0c7406c24b6ed0e34f7f51f28f332481dd1f9`
- `run/evaluation-audit.json` SHA256: `84114fc0910e8cc1497f2b8624d722b2849d45b69ba15905195e44b13731d62c`
- `run/analysis.json` SHA256: `098d5686e03dea2583f15e7fa366549c1414819462ed768e1c64aebc58aaf764`
- `run/stratified-bounds.json` reconciles all rule/seed slice sums to the frozen 512-pair aggregate.
- `run/unknown-diagnostic.json` SHA256s and independently checked endings show every UNKNOWN is H=128 censoring and no node-cap hit.
- `run/public-traces.json` records deterministic gzip archives for all four
  JSONL traces; each archive round-trips byte-exactly to the local source, and
  compressed members are small enough for the repository host. The raw JSONL
  originals remain local and were not staged.

Next: retain these frozen outputs and choose the next pre-outcome rule-coverage
study from the direct Chess-first, same-learner route. Science remains OPEN.
