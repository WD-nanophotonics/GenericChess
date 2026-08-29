# ADR-044: Exact generic preference reference corpus

## Status

Accepted F23E reference corpus. This is an audit/reference artifact only; no
Evaluator-v2 fitting, production flag, search change, Native change, or Shogi
transfer check is included.

## Decision

Add `evaluator_v2_corpus_v3.json` as a new version derived from V2. V1 and V2
fixtures are copied by value and verified byte-identically through recorded
SHA-256 hashes. The F22 ten-position stratum, all prior generic entries, and
the existing identity-based DEVELOPMENT/HOLDOUT split remain intact.

The new `exact_generic_preference_solver.py` evaluates a complete bounded
GenericChess tree using only authoritative legal successors, transitions, and
terminal adjudication. It scores only root-actor WIN/DRAW/LOSS, preserves all
optimal ties, includes history/repetition context in cycle identity, and
returns `REFERENCE_SOLVE_UNRESOLVED` on a node/depth cap or unresolved cycle.
It imports no evaluator and has no material, mobility, feature, corpus-ID, or
AlphaSho dependency.

Twenty-four new roots are certified `PREFERENCE_STRONG`: six each from four
independent generic ruleset identities (orthogonal ray, bishop/knight,
knight, and drop-lance). Their `max_ply=1` finite trees are fully expanded;
each proof records the exact W/D/L value of every legal root action, the full
optimal action set, state/leaf/cycle/cap statistics, and solver version.
The resulting strong supervision is 20 DEVELOPMENT and 4 sealed HOLDOUT roots,
with four independent DEVELOPMENT rulesets and no ruleset over 50% of strong
DEVELOPMENT roots. Existing weak and structural labels are not reclassified.

## Gate and next boundary

The strong-supervision minimum passes: 24 strong roots total, 20 strong
DEVELOPMENT roots, 4 strong HOLDOUT roots, and four independent rulesets.
F23E stops before any feature selection, coefficient fitting, HOLDOUT ranking,
or Shogi transfer analysis.

Select exactly `F23F_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R2` for the next phase.
F23F may consume only strong DEVELOPMENT roots for fitting, freeze its complete
candidate specification before opening HOLDOUT, and retain V1/V2/V3
immutability and production isolation.
