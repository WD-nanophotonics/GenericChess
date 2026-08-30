# ADR-068: F23V mechanic-active signal corrective

## Status

Accepted as a scope-clean corrective audit checkpoint; no production
integration or promotion is authorized.

## Context

The F23V first pass was structurally compliant but scientifically invalid as
cross-mechanic evidence: its three groups reused dormant K/R-only boards. Chat
also identified measurement defects in child history construction, semantic
attack authority, recapture accounting, terminal winner handling, and
pairwise tie scoring.

## Decision

Additive R1 artifacts repeat the same five-feature hypothesis with the fixed
coefficient vector `[1, 1, 1, 1, 1]` and unchanged score form
`S * sum(feature_i)`. The frozen R1 plan contains 30 distinct compact semantic
descriptors (10 per group), with active capture-to-hand/drop/promotion,
remove-from-game/promotion, and mixed path/special examples. It is not a copy
of the first-pass plan and no candidate was replaced after scoring began.

The corrective evaluator uses the pushed `SearchPathRuntime` child projection
for position, ply count, repetition counts, history, and terminal status. It
uses SemanticEngine legal, attack, and check APIs for semantic compiled
RuleSets; the legacy compiler is used only to build the static RuleSet-derived
normalization profile. The recapture feature adds an immediate legal capture
pressure term and a bounded term for a legal capture onto the authoritative
most-recent action target when history provides one. Terminal scoring is generic:
winner root actor is WIN-dominating, winner opponent is LOSS-dominating, and a
null winner is DRAW. Pairwise evaluation uses one unordered unequal-WDL pair;
an analytic tie is incorrect.

## Result

The mechanics and measurement contract probes pass, including active semantic
renaming, child history/repetition identity, terminal winner semantics, strict
pairwise tie classification, and a positive recapture probe. The exact
admission result is `0/30`: active roots either hit the configured isolation
cap or depend on MAX_PLY terminal leaves, so none can be used as strict
supervision evidence under the work-order admission rule. Planned mechanic
coverage is also below the requested drop/promotion minimums in the frozen
plan. The report therefore emits
`INSUFFICIENT_MECHANIC_ACTIVE_EXACT_COVERAGE`.

## Consequence

No evaluator signal metric is interpreted as cross-mechanic transfer, and no
F23W shadow or self-play boundary is started. The selected next boundary is
`F23W_EVALUATOR_SUPERVISION_STRATEGY_REASSESSMENT_R2`. The first-pass F23V
artifacts remain unchanged and are retained as historical evidence.
