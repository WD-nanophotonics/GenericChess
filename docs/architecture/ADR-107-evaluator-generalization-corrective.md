# ADR-107 — F39 evaluator generalization corrective

- Status: protocol frozen; analysis pending
- Date: 2026-09-01
- Work order: `GENERICCHESS-F39-EVALUATOR-REENTRY-GENERALIZATION-CORRECTIVE`

F39 is diagnosis-only. Before calculating any new R37A/R37B holdout result,
the manifest freezes the F37/F38/R1 evidence identities, tie-aware rank
definitions, component-additivity and causal labels, distribution-shift rules,
the limited 2048-node A/B-only search protocol, and the mechanical F40 mapping.

The consumed F38 holdout is validation evidence, not an optimization oracle.
F39 cannot select, tune, or integrate R37A/R37B/R37C into production.
