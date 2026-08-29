# ADR-042: Evaluator-v2 corpus R2 coverage

## Status

Accepted diagnostic boundary for F23C. Production evaluator, search policy,
Native runtime, and AlphaSho behavior remain unchanged.

## Decision

Create `evaluator_v2_corpus_v2.json` as a new version derived from the V1
fixture. The V1 fixture is copied byte-for-byte as the first generic stratum,
and its ten frozen F22 positions remain unchanged. Thirteen additional
non-Shogi cases are constructed from small generic ray, drop, semantic cannon,
and semantic file-guard rulesets. Their inclusion is feature-blind and uses
only deterministic provenance, event presence, exact-solver availability, and
canonical deduplication.

New labels use independent authority classes: exact one-ply terminal mate-in-one
outcomes and full exact legal-action sets. Captures, attacked/defended targets,
available recapture witnesses, safe mobility, drops, and semantic suppression
events are recorded as structural evidence. No evaluator score is used to
select a case, issue a label, or choose the diagnostic child.

The existing identity split is retained exactly:
`HOLDOUT iff int(state_identity_sha256[:8], 16) mod 4 == 0`; all feature
screening and boundary selection use DEVELOPMENT only. The resulting V2 has
21 generic cases, 18 DEVELOPMENT, and 3 sealed HOLDOUT cases.

## Evidence and gate

The F23A probe observes six of seven feature families across more than one
ruleset identity in DEVELOPMENT: attack/defense/hanging, capture/recapture
pressure, legal/safe mobility, anchor/check pressure, hand/drop pressure, and
semantic constraint effect. Promotion remains represented by the preserved V1
stratum. Attack/defense and capture/recapture both have independent generic
event evidence, and exact references are reproducible without evaluator
dependency.

The prototype eligibility gate passes, including two nonredundant signals and
the frozen split/provenance checks. This is evidence that a small prototype is
eligible, not permission to fit production weights.

## Next boundary

Select exactly `F23D_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE`. F23D must keep the
V2 corpus and HOLDOUT sealed, start with a small coherent generic feature set,
and remain outside production behavior until its own gates pass.
