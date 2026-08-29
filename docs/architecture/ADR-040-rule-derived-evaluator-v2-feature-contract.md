# ADR-040 — Rule-Derived Evaluator-v2 Feature Contract

Status: Accepted as an F23A audit decision; production implementation is not
authorized by this ADR.

## Context

F22 identified eight persistent AlphaSho disagreements and two agreement
controls in the frozen ten-position corpus.  It also showed that the current
generic-v1 evaluator's component decomposition is exact, while its feature
vocabulary is shallower than the semantic legality engine.  F23A was therefore
authorized to measure generic feature families without changing evaluator,
search, or Native behavior.

The audit recovers the exact F22 corpus and reference moves read-only from
commit `3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38`.  It uses the current
compiled semantic executor for legal children and uses the legacy compiled
view only for v1 parity and bounded comparison.  Candidate computations are
position-local and contain no game-specific piece values, square tables, or
opening knowledge.

## Contract

The audit-only probe measures these families:

- value-weighted attack/defense/hanging exposure;
- immediate legal capture and last-target recapture pressure;
- legal safe mobility with value-weighted captures;
- anchor escape, checking threats, and defensive pressure;
- promotion opportunity, forced promotion, and promotion threats;
- hand/drop pressure, including checking and defensive drops;
- semantic legality suppression or additions relative to the legacy legal
  candidate set.

Counts are normalized by board area and value terms by the median non-anchor
board value.  This is diagnostic normalization, not a fitted evaluator
weighting.  The probe reports root, frozen AlphaSho child, and F22 HIGH
GenericChess selected child values and deltas for every family.  It also
reports direction consistency across the eight failures, pairwise correlation,
and measured position-local cost with shared legal-context caching.

## Findings

The ten-position recovery and the current HIGH child selection both pass their
provenance checks.  Reconstructed evaluator-v1 components match
`Evaluator.evaluate()` for 30 root/reference/current state rows.  Candidate
directions are contradictory across the eight failures: legal-safe mobility
is mixed, attack/defense and capture/promotion families do not consistently
favor the reference child, and hand/drop plus semantic-constraint effects are
unobserved in this corpus.  The two agreement controls remain included as
controls, not as training data.

The candidate information falls into three layers:

1. movement-atom/static capability, already represented by the v1 profile and
   pseudo mobility;
2. position-dependent legal information available from the current semantic
   executor, including legal captures, safety, checking, promotion, drops,
   and constraint suppression;
3. richer history/game-policy abstractions not exposed by the current generic
   feature boundary, which require a new semantic API before evaluator use.

All measured features are deterministic and type-name invariant when equivalent
rules are renamed.  No production behavior or configuration changed.

## Decision

Select exactly `F23B_EVALUATOR_CORPUS_EXPANSION`.  F23A provides a clean,
semantics-preserving audit boundary but the ten positions do not establish a
coherent feature direction, and several families have no observations.  A
larger generic corpus is required before fitting weights or implementing an
Evaluator-v2 prototype.  F23A makes no Elo or playing-strength claim.

## Consequences

The durable implementation is limited to the audit script and invariance/parity
tests.  Generated reports remain transient and are not committed.  Future work
must preserve generic rule-derived inputs, the board-area/median-value
normalization contract, exact v1 parity, and type-name invariance.
