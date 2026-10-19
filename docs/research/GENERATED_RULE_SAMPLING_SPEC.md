# Generated-rule sampling population — draft spec (AUX_CLAUDE, 2026-10-19)

**Status: DRAFT, not registered, no runs.** Written per Dot 107a. Any per-rule failure-*rate* claim about the Generic learner needs a defined sampling population and distribution first. The 16–20 rules used in DEV_AUX102–108 were inspected repeatedly, so they are a development/regression set and cannot serve as confirmation.

## 1. Population

The population is the output of `generic_chess.generation.generator.generate_game(GeneratorConfig(...))`. A *population cell* is one fixed config tuple. Proposed cells, each a pre-declared stratum and never pooled silently:

| Cell | Config | Reason |
|---|---|---|
| C1 | board_size=4, defaults | the baseline studied in 102/103 |
| C2 | board_size=4, allow_hybrid=True | 106 |
| C3 | board_size=4, leap_probability=1.0, ray_probability=0.0 | 108 |
| C4 | board_size=5, defaults | 104/105 (types P/A/B; rule-derived channels) |

A claim about a mixture of cells must state its cell weights before any data is seen.

## 2. Sampling

- **Generator seeds:** drawn uniformly without replacement from a declared, never-used integer block, e.g. a fresh 6-digit block checked against both checkouts' plans/code/docs, as in 102–108. The draw uses a declared PRNG seed. **No regeneration** and no outcome or playability filter beyond the generator's own soft filters.
- **Generation failures:** recorded as their own outcome class and counted in the denominator of "fraction of attempted seeds".
- **Admission failures:** if the type set does not match the cell's channel design, record the case as such. Never replace the rule.

## 3. Unit, outcome and estimand

- **Unit:** one rule. Its outcome is the registered per-rule contrast Cold@100k − Cold@0, with full paired bounds over 4 initializations × held-out families × 2 roles × 2 fixed foes. It is classified positive (lower > 0), negative (upper < 0) or undetermined.
- **Estimand per cell:** the fraction of sampled rules in each class, reported with an exact binomial interval over rules. Rules are the independent units; seeds and roots within a rule are not.
- **Sample size:** fixed before running. For example, n = 20 rules per cell gives an exact 95% interval of about ±0.2 on a 20% failure fraction. A cost estimate comes first, from measured rates: 4×4 ≈ 3k nodes/s TRAIN and ≈ 0.45 s/EVAL game; 5×5 ≈ 1.8k nodes/s and ≈ 2 s/game. Each cell is likely ≥ 120 min, so **Dot review is required first**.

## 4. Held-out roots (fixing the 108 failure)

For each rule, EVAL families must not overlap any possible TRAIN family:
- **Either** cap TRAIN at `max_games` and check against the full span `offset … offset + max_games/2`,
- **or** give TRAIN and EVAL disjoint family blocks *and* check root records against TRAIN roots across that full span.

Report the actual overlap after the run, and keep terminal roots.

## 5. Not covered

This spec does not cover learner changes; a new learner must first state how it differs from λ = 1 (Dot 107a). It also does not cover Chess or Xiangqi, or any human-price comparison.
