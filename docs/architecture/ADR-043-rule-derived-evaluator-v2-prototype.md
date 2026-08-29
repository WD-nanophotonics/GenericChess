# ADR-043: Rule-derived evaluator-v2 prototype decision

## Status

F23D audit-only prototype decision. No production evaluator, search policy,
Native runtime, or corpus fixture was changed.

## Supervision contract

Every V2 generic entry is partitioned before any fitting decision:

- `PREFERENCE_STRONG`: a complete mathematically optimal/forced root-action
  set under its authority.
- `PREFERENCE_WEAK`: an immediate terminal win is proved, but all other root
  actions are not completely ordered.
- `STRUCTURAL_ONLY`: exact legality, suppression, event, promotion, drop, or
  legal-action-set evidence that does not establish a playing preference.

The six one-ply mate cases are `PREFERENCE_WEAK`. The exact legal-action,
promotion, semantic, drop, and preserved F22 evidence is `STRUCTURAL_ONLY`.
There are zero `PREFERENCE_STRONG` DEVELOPMENT roots. In particular, an exact
legal-action set never licenses preferring its arbitrary diagnostic child.

## Prototype decision

F23C DEVELOPMENT evidence deterministically identifies at most four candidate
families for a future prototype, with monotonicity and redundancy checks. That
selection is recorded as an audit-only future candidate set; no coefficients,
normalization fit, candidate specification, HOLDOUT evaluation, or Shogi
transfer check is produced because the corpus cannot justify preference
fitting. This avoids manufacturing labels and keeps HOLDOUT sealed.

The V1 and V2 fixture bytes are frozen and hashed in the audit output. The F23C
probe remains DEVELOPMENT-only. Baseline reference-rank metrics are reported
only for the weak roots and structural cases contribute zero ranking loss.

## Next boundary

Select exactly `F23E_REFERENCE_PREFERENCE_CORPUS`: add independently
preference-authoritative generic roots (preferably complete bounded minimax or
forced outcome sets) before attempting another evaluator-v2 fit. Do not make a
production feature flag or promote evaluator-v2 from this phase.
