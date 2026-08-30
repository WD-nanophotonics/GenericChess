# ADR-067: F23V minimal analytic evaluator signal probe

## Status

Accepted audit result; production integration is not authorized.

## Context

F23U selected an audit-only probe using a small, frozen plan. F23V tests
whether one common evaluator can provide a useful signal across three rule
families without game-name or concrete-piece branching. The probe must not
change production evaluation, search, Native, rule semantics, or V1--V12
fixtures.

## Decision

The candidate evaluator is implemented only in
`scripts/audit_f23v_minimal_analytic_evaluator.py`. It uses exactly five
bounded, signed feature families with the fixed coefficient vector
`[1, 1, 1, 1, 1]`:

1. material and inventory;
2. safe mobility and control;
3. attack, defense, and anchor safety;
4. forcing capture and recapture;
5. capability-gated promotion and drop.

The common score is `S * sum(feature_i)`, where `S` is the RuleSet-derived
median non-anchor board value. Root actions are applied through the
authoritative `SearchPathRuntime`; terminal child outcomes take precedence,
and non-terminal children use the five-feature static score.

The frozen plan SHA is
`426768dfc74d08db905c7440b1231759859386ac16a9cc9d51b5290d5a88a47e`.
It contains eight compact V12 structural templates per group and admits six
fully certified roots per group after exact V3 and abstraction agreement.
The mixed-mechanic smoke test covers capture-to-hand, drop inventory
consumption, remove-from-game, promotion, path restriction, state identity,
runtime balance, and terminal machinery. Renamed-equivalent RuleSets produce
equal feature vectors and scores.

## Result

The probe is a genuine FAIL against the signal thresholds: overall top-set
precision is `0.6667` (required `>= 0.70`) and overall optimal-hit is `0.6667`
(required `>= 0.75`). Pairwise ordering is `0.8333`, coverage is `6/8` usable
roots per group, and all mixed-mechanic, type-name, fixed-coefficient, and
complexity gates pass. No technically compatible evaluator-v1 baseline was
invoked, so no v1 delta claim is made.

## Consequence

Do not route this evaluator into production search or evaluation. Select the
next boundary `F23W_EVALUATOR_SUPERVISION_STRATEGY_REASSESSMENT_R2` for a
strategy reassessment. The next work order must decide whether the coherent
but insufficient equal-scale signal warrants a revised supervision strategy;
it must not silently fit coefficients or lower the F23V thresholds.
