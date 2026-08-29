# ADR-045: Rule-derived evaluator-v2 prototype R2

## Status

F23F audit-only prototype trial. No production evaluator/search/Native path,
V1/V2/V3 corpus fixture, HOLDOUT result, or Shogi transfer result was changed
or opened.

## Candidate construction

Only the 20 `PREFERENCE_STRONG` DEVELOPMENT roots were loaded for fitting.
Weak and structural roots contributed zero loss. Pairwise constraints compare
every exact optimal action with every strictly inferior action, preserve ties,
deduplicate identical feature/preference signatures within each ruleset, and
macro-weight the four ruleset groups equally.

The deterministic audit selected four multi-ruleset, nonredundant ADR-040
families: `attack_defense_hanging`, `anchor_check_pressure`,
`legal_safe_mobility`, and `capture_recapture_pressure`. The bounded correction
uses evaluator-v1 as its base, robust DEVELOPMENT-only normalization, integer
coefficients from `[-2, 2]`, and a correction clip of `+/-2`.

The complete rejected-before-HOLDOUT candidate specification and SHA are kept
in `evaluator_v2_candidate_spec_f23f.json`; it is not a production candidate.

## Grouped result

Pooled development metrics improve slightly (deduplicated pairwise accuracy
from 0.9848866 to 0.9899244; macro equal-ruleset accuracy from 0.9891304 to
0.9927536; best optimal rank mean from 1.05 to 1.0). This is not sufficient:
all four leave-one-ruleset-out folds show no positive improvement, and the
roots are related `max_ply=1` synthetic constructions. The apparent pooled
gain is therefore not credible cross-ruleset generalization.

The candidate is rejected before HOLDOUT. HOLDOUT and F22/AlphaSho transfer
checks remain sealed, with no retuning or post-selection access.

## Next boundary

Select exactly `F23G_REFERENCE_PREFERENCE_CORPUS_R2`: obtain deeper,
less-correlated exact preference roots before attempting another evaluator-v2
prototype.
