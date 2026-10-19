# Static material transfer on fresh 5x5 generated rules — 2026-10-20

## Decision question and frozen comparison

Does the existing rule-only full-type static material candidate improve finite
game utility over Unit on fresh generated 5x5 rules, at fixed search budgets?
This fills a board-size gap in PRIMARY's prior 4x4 and 6x6/8x8 static-utility
panels. DEV_AUX's published 5x5 cold-TD gain is not a static-price comparison;
no AUX code, checkout, model, result or training run was used or changed.

The frozen design uses eight generated rules, two deterministic legal 4-ply
prefixes per rule, two candidate checkpoints (Unit/static_v2), two fixed foes
(Unit/static_v2), and both candidate colors: 128 game slots. The candidate uses
D8/8192 nodes/0.5 s/q0, the foe D2/32768 nodes/0.5 s/q0, with root-window
pruning off and TT off. Promotion, drops, full Session history, repetition and
actual terminal results are retained. Outcomes are the candidate-relative Core
reward in {-1,0,+1}; unresolved slots stay UNKNOWN. The same-root/foe/color
contrast is static_v2 candidate reward minus Unit candidate reward. Each foe is
reported separately. This is not a population-confidence calculation.

The initial `521001..521008` panel completed, but its producer used a 96-total-
ply cap where the frozen plan required 96 candidate plies. It therefore stopped
at no more than 48 candidate plies. All 128 records, query receipts and source
are retained in `data/static_5x5_price_20261020/`; its independently replayed
all-slot bounds were +0.1875..+0.75 against Unit and +0.5625..+1.125 against
static. This is a protocol-deviant shorter-horizon result only and does not
close the registered 96-candidate-ply question. It was not extended, replaced,
or pooled with the corrected panel.

## Corrected fresh-seed validation

The separate, prospective `data/static_5x5_price_20261020/candidate96/` panel
uses never-used rule seeds `522001..522008`. It stops after 96 successful legal
candidate moves, or earlier at an actual Core terminal; ongoing games at that
point remain UNKNOWN. All 128 slots closed in 74.688 s: 126 actual terminals,
2 UNKNOWN, 3,984 queries, 17,179,981 main nodes and no unstarted slots. The
18-UNKNOWN shorter-horizon panel and this 2-UNKNOWN corrected panel remain
separate.

| Fixed foe | Paired slots | Fully finite pairs | UNKNOWN pairs | Finite-pair mean | All-slot conservative bound |
|---|---:|---:|---:|---:|---:|
| Unit | 32 | 30 | 2 | +0.3000 | [+0.21875, +0.34375] |
| static_v2 | 32 | 32 | 0 | +0.46875 | [+0.46875, +0.46875] |

The all-slot bounds retain UNKNOWN candidates as [-1,+1] before differencing;
they make no assumption about the missing outcomes' dependence. Both lower
bounds are positive for this fixed sample and budget. A post-hoc descriptive
leave-one-rule-seed-out calculation remains positive for every omission: the
lowest remaining lower bound is +0.142857 against Unit and +0.321429 against
static. This is a sensitivity check over eight linked rule families, not a
confidence interval or a claim of independent population draws.

The predeclared candidate-color swap matters to interpretation. By candidate
owner, the static-minus-Unit bounds are:

| Fixed foe | Candidate owner 0 | Candidate owner 1 |
|---|---:|---:|
| Unit | [+0.5, +0.625] (15/16 finite) | [-0.0625, +0.0625] (15/16 finite) |
| static_v2 | [+0.625, +0.625] (16/16 finite) | [+0.3125, +0.3125] (16/16 finite) |

Thus the registered equal-color aggregate is positive against both foes, but the
Unit-foe result when the candidate is owner 1 remains unresolved. The sampled
benefit is not established for every opponent/color combination.

At the first same-state candidate decision, static and Unit choose different
actions in 6/15 shared owner-0 contexts and 5/13 shared owner-1 contexts against
either fixed foe (15/16 owner-0 roots and 13/16 owner-1 roots had a common
candidate state). This confirms that the material
candidate changes real choices in the observed common contexts; it is not a
utility measure and does not resolve the owner-1/Unit-foe outcome interval.

Actual role work is retained separately from game outcomes:

| Fixed foe | Candidate | Candidate queries / nodes / caller seconds | Foe queries / nodes / caller seconds | Actual terminal / UNKNOWN games |
|---|---|---:|---:|---:|
| static_v2 | static_v2 | 339 / 2,777,088 / 9.891 | 334 / 127,990 / 0.656 | 32 / 0 |
| static_v2 | Unit | 463 / 3,762,754 / 13.485 | 465 / 193,988 / 0.972 | 32 / 0 |
| Unit | static_v2 | 551 / 4,503,450 / 16.873 | 540 / 165,020 / 1.044 | 31 / 1 |
| Unit | Unit | 650 / 5,324,800 / 19.102 | 642 / 324,891 / 1.636 | 31 / 1 |

Those totals depend on realized game lengths; they are not matched per-game
latency or a speed claim. Each query retained its own node count, depth, stop
cause and caller/kernel timing in `queries.jsonl`.

Per-seed finite bounds are heterogeneous. Against the Unit foe, seed `522008`
has a -0.5 paired mean, while several seeds are neutral; against static, four
seeds are neutral. The positive pooled finite bounds therefore do not mean that
the static candidate wins on every generated rule. The corrected panel's raw
candidate-relative outcomes are 80 wins, 4 draws, 42 losses and 2 UNKNOWN.
Actual choices include 1,061 drops and 320 promotions. All 128 serialized final
records independently replayed to their saved final-state hashes; the analysis
also verified the exact 128 planned slot identities and all 3,984 query rows.

Per-seed paired mean intervals (each seed has four root/owner contrasts per
foe; UNKNOWNs remain bounded) make that heterogeneity explicit:

| Rule seed | Against Unit foe | Against static foe |
|---|---:|---:|
| 522001 | [0, 0] | [0, 0] |
| 522002 | [0, +0.5] | [+0.25, +0.25] |
| 522003 | [+0.5, +0.5] | [0, 0] |
| 522004 | [0, 0] | [0, 0] |
| 522005 | [+0.5, +0.5] | [+0.5, +0.5] |
| 522006 | [+0.5, +1] | [+0.5, +0.5] |
| 522007 | [+0.75, +0.75] | [+1.5, +1.5] |
| 522008 | [-0.5, -0.5] | [+1, +1] |

## Decision and limits

Retain `static_v2` as a viable 5x5 rule-only material candidate for the tested
50/50 candidate-color mix under fixed D8/D2 budgets and both tested fixed foes.
The owner-1/Unit-foe subgroup is unresolved. This fills the local
5x5 comparison gap and agrees directionally with, but does not pool with, the
shorter-horizon panel. It does not establish a universal price vector,
cross-board-size law, population win rate, strength guarantee, training target
or product default. Keep Unit controls and preserve adverse per-seed cases.
Do not run another unchanged 5x5 price panel: reopen only for a changed regime,
population claim requirement, or a concrete downstream consumer that could
change the model/default decision. The next mainline selection should return to
a different decision-changing unfamiliar-rule search question.

The safe record-audit/analysis command from the repository root is:

```powershell
.\.venv\Scripts\python.exe docs/research/data/static_5x5_price_20261020/candidate96/analyze.py
```

The producer is a single bounded run with a 2,400-second internal cap; its
expected duration was below four minutes. Its saved source and SHA are retained
for provenance. Do not rerun the producer: it would overwrite the frozen
records. The analysis replays records but does not launch searches. The first
shorter-horizon source is preserved as `producer_total96_v1.py` with its
original source hash in `producer-source.json`.
