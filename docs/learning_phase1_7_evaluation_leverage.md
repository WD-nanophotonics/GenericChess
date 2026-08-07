# Learning Phase 1.7: Evaluation Leverage / Benchmark Identification

## Question

Under which ruleset and search budget does the evaluation function have
enough leverage over AlphaBeta decisions to make "learning an evaluation"
a measurable, comparable, product-relevant problem?

This phase never changes the learner or the native search.  It measures.

## Learner freeze

`tdleaf.py`, `features.py`, `selfplay.py` are byte-identical to the Phase 1.6
commit (`1da38ee`); native search semantics are untouched.

## Pre-registered protocol

All protocol constants below were fixed before any measurement in this phase
and are also emitted to `artifacts/learning_phase1_7/config.json`.

### Experiment A — artificial material perturbation (R2)

* Global-scale control: `w' = c·w` for `c in (0.5, 0.75, 1.25, 1.5)`.
  This is a sanity control only: a uniform linear rescale that leaves
  mate/terminal constants unchanged is not expected to change move
  ordering, so it is never used as a leverage indicator.
* Single-piece relative perturbation (primary): for every non-anchor type,
  `w_t' = f·w_t` (board and hand channels of that type together) with
  `f in (0.5, 0.75, 0.9, 1.1, 1.25, 1.5)`; all other types unchanged.
  Zero-weight types are skipped and recorded (`zero_weight_type`), never
  perturbed to a meaningless value.
* Directional vector perturbations (checkpoint-independent): four fixed
  directions — alternating sign, first-half-positive, board/hand
  differential, and a normalized pseudorandom vector (fixed seed).  Each is
  scaled to L2 = 25% of the Gen0 combined weight L2.
* EVAL_LEVERAGE (fixed definition): mean best-move flip rate over the
  single-piece ±25% perturbations at 2000 nodes.

### Experiment B — budget sweep (R2)

Budgets fixed at `250, 500, 1000, 2000, 4000, 8000`; artificial bundle =
single-piece ±25% + directional perturbations; learned comparison =
Gen0 vs Gen1/2/3 (Phase 1.5 seed-7 checkpoints).  Every search uses a fresh
engine; base results are cached per `(checkpoint_id, budget)`; no TT
sharing across evaluators.

Corpus: positions are taken positionally (`positions[0:N]`) from the fixed
checkpoint-independent R2 corpus: 128 for the perturbation sweep, 64 for the
budget sweep.

### Experiment C — candidate discovery (checkpoint-independent)

* 32 candidates, 6×6 boards, presets cycling
  `free_random / bilateral_random / classic_like`, seeds
  `20260807000..031` from master seed `20260807`.
* Eligibility thresholds (fixed before screening):

  | metric | threshold |
  | --- | --- |
  | terminal rate | = 1.0 |
  | average plies | 4 .. 200 |
  | endless (repetition+max-ply) fraction | ≤ 0.5 |
  | owner0 win rate | ≤ 0.90 |
  | owner1 win rate | ≥ 0.05 |
  | shallow(500)/deep(4000) agreement | 0.30 .. 0.98 |
  | eval leverage (±25% @ 1000 nodes) | ≥ 0.10 |
  | forced-move fraction | ≤ 0.30 |
  | mean legal actions | ≥ 2.0 |

* Selection: evaluation-sensitive = max leverage among eligible
  (tie-break owner0 win rate, then fingerprint); mixed = closest to
  leverage 0.15 with leverage in [0.05, 0.35] and agreement in
  [0.40, 0.95] (tie-break fingerprint); tactical = R2 retained.
* Selection re-applies the fixed thresholds from the summary metrics and
  never receives trained checkpoints or learned results (selection-bias
  guard).  All candidates, including rejected and generation-failed, are
  recorded in `candidate_rulesets.json`.

### Experiment D — frozen retest (selected benchmarks only)

* Seed 7, Gen0..Gen3 (Phase 1.5 artifacts for R2; frozen calibrated
  training for new rulesets).
* Search sensitivity at `250..4000`; teacher = Gen0 at 20,000 nodes vs
  student at 2,000 (64 positions); paired arena 16 pairs at 1000 nodes/move,
  fixed openings, color swap, fresh engines, no exploration.

### Product budget

PRODUCT_SEARCH_BUDGET = smallest budget in `250..4000` where learned mean
flip rate ≥ 0.02, Gen0 teacher agreement ≥ 0.50, and zero failed searches,
evaluated on the **evaluation-sensitive benchmark retest** (the setting where
learned evaluation is visible); otherwise
`NO_PRODUCT_BUDGET_IDENTIFIED`.  The R2 budget sweep is reported alongside
as comparison only.

## Verdicts

* R2_EVAL_LEVERAGE: LOW < 0.05, MODERATE 0.05–0.20, HIGH > 0.20.
* BUDGET_EFFECT: shallow(250/500) minus deep(4000/8000) artificial flip
  rate; >0.02 shallow, <−0.02 deep, non-monotonic if ≥2 sign changes,
  else stable.
* LEARNED_DIRECTION: learned/artificial flip ratio ≥0.5 high-leverage,
  ≤0.1 low-leverage, else mixed.
* BENCHMARK_IDENTIFICATION: suitable / incomplete / only-tactical /
  none.
* LEARNING_RETEST: per benchmark (positive if arena ≥0.55 and teacher
  improves; negative if arena ≤0.45; else no positive signal).
* NEXT_PHASE_DECISION: exactly one of the pre-registered gates.

## Results

Full run (commit `1da38ee`, project `0.8.0a4`, native `0.3.0`); artifacts in
`artifacts/learning_phase1_7/*.json`.

### R2 perturbation sweep (Experiment A)

128-position corpus at 2000 nodes, ±25% single-piece bundle mean flip rate
≈ **0.053** (LOW/MODERATE boundary; verdict MODERATE).  Per-type ±25%
flips: A 0.031/0.031, P 0.109/0.047, X 0.055/0.047.  Directional
perturbations (L2 = 25% of Gen0 weight L2) flip 0.078–0.195; global-scale
controls flip 0.0 everywhere (expected: uniform rescale does not change
ordering).  Zero-weight types were skipped explicitly; none occurred on R2.

### R2 budget sweep (Experiment B)

| budget | artificial flip | Gen1/2/3 learned flip |
| --- | ---: | ---: |
| 250 | 0.0594 | 0.0 / 0.0 / 0.0 |
| 500 | 0.0625 | 0.0 / 0.0 / 0.0 |
| 1000 | 0.0688 | 0.0 / 0.0 / 0.0 |
| 2000 | 0.0703 | 0.0 / 0.0 / 0.0 |
| 4000 | 0.0734 | 0.0 / 0.0 / 0.0 |
| 8000 | 0.0844 | 0.0 / 0.0 / 0.0 |

Artificial material leverage **rises monotonically** with budget on R2
(0.059 → 0.084), contradicting the "deeper search drowns evaluation"
hypothesis.  Learned Gen1–3 flip rates are 0.0 at every budget on this
64-position subset (consistent with Phase 1.6 seed-7 rates of 0.2–0.6% on
512 positions).  The pre-registered BUDGET_EFFECT rule (shallow mean − deep
mean = −0.018, just under the ±0.02 threshold) yields `LEVERAGE_STABLE`; the
raw monotone increase is reported as an observed fact.

### Candidate discovery (Experiment C)

32 candidates (6×6, master seed 20260807): 0 generation failures, 4
eligible.  Eligibility metrics for all 32 (including rejected) are in
`candidate_rulesets.json`.

### Benchmark selection

* tactical: R2 (retained).
* evaluation-sensitive: candidate 9 (`9f7e7201…`), eval leverage 0.203,
  shallow/deep agreement 0.438.
* mixed: candidate 12 (`597f8191…`), eval leverage 0.164, agreement 0.625.

Selection used only structural + Gen0 + artificial-perturbation metrics;
no learned checkpoints were passed to `select_benchmarks` (enforced by
signature and tests).

### Frozen retest (Experiment D, seed 7)

Evaluation-sensitive benchmark:

| budget | Gen1/2/3 move flip |
| --- | ---: |
| 250 | 0.063 / 0.063 / 0.063 |
| 500 | 0.063 / 0.063 / 0.063 |
| 1000 | 0.078 / 0.078 / 0.094 |
| 2000 | 0.047 / 0.047 / 0.063 |
| 4000 | 0.016 / 0.016 / 0.031 |

Teacher agreement (Gen0 @20k vs student @2k): Gen0 0.672, Gen1 0.641,
Gen2 0.641, Gen3 0.656 (teacher self 0.953).  Paired arena (16 pairs,
1000 nodes/move): Gen1 0.531 [0.438, 0.625], Gen2 0.531 [0.438, 0.625],
Gen3 0.594 [0.469, 0.719] — suggestive but not significant; teacher did not
improve → `NO_POSITIVE_SIGNAL`.

Mixed benchmark: learned flip 0.0 at every budget; teacher agreement flat
0.609; arena 0.5/0.5/0.5 → `NO_POSITIVE_SIGNAL`.

### Product budget

On the evaluation-sensitive benchmark, learned mean flip is 0.0625 at 250
nodes (0.083 at 1000), Gen0 teacher agreement 0.672, zero failed searches →
**PRODUCT_SEARCH_BUDGET = 250**.  R2 Gen3 flip remains 0.0 at every budget
(comparison only).  Interpretation: at a cheap 250-node budget the learned
evaluator visibly changes decisions (6%) while Gen0 already plays
reasonably; however the change is not yet a measured strength improvement
(arena CIs include 0.5, teacher flat).

### Verdicts

* R2_EVAL_LEVERAGE: **MODERATE** (≈5.3% ±25% single-piece flip at 2000)
* BUDGET_EFFECT: **LEVERAGE_STABLE** (raw trend increasing; pre-registered
  effect-size threshold just missed)
* LEARNED_DIRECTION: **LEARNED_CHANGES_LIE_IN_LOW_LEVERAGE_DIRECTIONS**
  (learned 0.0 vs artificial ~6.7% mean on R2)
* BENCHMARK_IDENTIFICATION: **SUITABLE_BENCHMARKS_FOUND**
* LEARNING_RETEST: **NO_POSITIVE_SIGNAL** (both new benchmarks)
* PRODUCT_SEARCH_BUDGET: **250**
* NEXT_PHASE_DECISION: **KEEP_MATERIAL_AND_FIX_LEARNING_DIRECTION**

### Selection-bias audit

`select_benchmarks(candidate_summaries, r2_fingerprint)` receives only
precomputed summary dicts; no `LearnableMaterialCheckpoint`, no Gen1–3
results, and no training call exists in the selection path.  Rejected and
failed candidates are retained in `candidate_rulesets.json`.  Thresholds
and sorting rules were fixed before screening and are re-applied by the
selection function itself.
