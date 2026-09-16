# F61R1 Chess initialization-seed localization

## Purpose

Test whether the observed F61 Chess strength failure is sensitive to the
nonlinear model initialization seed while holding the training data, targets,
openings, and search budgets fixed.

## Frozen configuration

- Ruleset: canonical Western Chess.
- Training data: 3 D0 reachable roots, record seed `620100`, with the existing
  F61 smoke root/search budgets and frozen `PAIRWISE_RANKING` targets.
- Arena: opening seed `620701`; 2 role-swapped pairs per candidate (4 games);
  100 nodes/move; depth 4; 2 MiB transposition table; 1 worker; equal parent
  and child budgets.

## Aggregate outcome

Both alternate model initialization seeds, `59011` and `59013`, produced the
same result: mean pair score `0.375`, pair scores `[0.5, 0.25]`, 0 better / 1
tied / 1 worse pair, WDL `0-3-1`, and `directional_failure=true`.

## Interpretation and limitation

The failure was not localized to model initialization under this frozen
training/data path and tiny Arena pilot. This is sufficient to stop this
candidate/pilot and redirect the next investigation toward data or objective
choices; it is not sufficient to estimate a stable win rate or prove the whole
algorithm impossible. No candidate is selected or promoted.
