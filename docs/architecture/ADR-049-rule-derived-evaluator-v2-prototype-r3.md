# ADR-049: Rule-derived evaluator V2 prototype R3 audit

## Status

F23I development gate failed. No candidate evaluator was frozen, the V5
HOLDOUT remained sealed, and the next boundary is
`F23J_REFERENCE_PREFERENCE_CORPUS_R4`.

## Scope and protocol

This audit consumed only the 20 orbit IDs explicitly listed in V5 as
fit-eligible DEVELOPMENT data. It recomputed the ADR-040 generic feature
families from the current ruleset implementation, selected at most four
families using grouped margins across five rulesets and two mechanic families,
and fit bounded coefficients only inside each training fold. It did not use
F23F coefficients, historical rows as fitting data, HOLDOUT rows, Shogi, or
AlphaSho.

The evaluation used five leave-one-ruleset-out folds plus two leave-one-mechanic
family-out transfer folds. The baseline was evaluator V1 with no correction.
The development report is intentionally transient and is not a repository
artifact.

## Result

The full development fit selected four families:

`legal_safe_mobility`, `semantic_constraint_effect`, `anchor_check_pressure`,
and `attack_defense_hanging`.

The baseline deduplicated pairwise accuracy was 0.3333, while the in-sample
prototype reached 0.5556 and improved mean best-optimal rank from 1.60 to
1.35. These descriptive gains were not sufficient for advancement: only 2/5
leave-one-ruleset-out folds improved, and 0/2 mechanic-transfer folds
improved. Therefore the grouped generalization gate failed and no HOLDOUT
result may be inspected in F23I.

## Decision

Do not publish a V2 candidate specification or change production evaluator,
search, or Native behavior. Build a fresh reference preference corpus in F23J
to break the observed ruleset/mechanic relatedness before attempting another
fit.
