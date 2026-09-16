# F61R2 Chess objective localization

## Purpose

Test whether changing only the F61 training objective recovers the Chess
strength lost by the original `PAIRWISE_RANKING` candidate.

## Frozen configuration

- Ruleset: canonical Western Chess; same parent checkpoint as F61R1.
- Training data: D0 reachable distribution, record seed `620100`, exactly 3
  smoke roots, existing spectrum/search budgets, model initialization seed
  `59012`, unchanged features, targets, width, and regularization.
- Arena: opening seed `620701` and the same 2 deterministic openings; 2
  role-swapped pairs per candidate (4 games); 100 nodes/move; depth 4; 2 MiB
  transposition table; 1 worker; equal parent and child budgets.

## Aggregate outcome

Both alternate objectives were not directional failures:

- `POINTWISE_Q`: mean pair score `0.5`, pair scores `[0.5, 0.5]`, 0 better / 2
  tied / 0 worse pairs, WDL `0-4-0`.
- `SOFT_POLICY_DISTILLATION`: mean pair score `0.5`, pair scores `[0.5, 0.5]`,
  0 better / 2 tied / 0 worse pairs, WDL `0-4-0`.

## Interpretation and limitation

Changing the objective alone removed the directional failure observed for the
original `PAIRWISE_RANKING` candidate on this frozen pilot, so the result is
objective sensitivity evidence. Neither candidate is automatically selected or
promoted. This tiny sample is sufficient to stop this localization pilot but
not to estimate a stable win rate or establish general superiority; teacher and
fit metrics remain diagnostic only.
