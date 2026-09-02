# ADR-119: F49 learning-signal architecture reassessment

Status: accepted protocol boundary; measurements not yet run

F48 closed at `4bd25d405af0890668c2940eefc8b68faae1b594` with classification
`MIXED_OR_UNRESOLVED` and next boundary
`F49_LEARNING_ARCHITECTURE_REASSESSMENT`. F49 is diagnosis-only. Its
pre-measurement authority is the standalone H49A manifest
`tests/fixtures/h49a_learning_signal_architecture_protocol_manifest.json`;
that manifest is signed and explicitly contains no observed F49 results.

## Scope and preservation

The H48C control remains training `480700`, holdout `480703`, and arena
`480708`, with holdout positions generated at plies 2..6. The accepted F48
classification and measurements are preserved as the control condition. H49A
binds the three accepted RuleSet fingerprints and the authoritative
`generic_chess.core.identity.position_identity_key`.

The F48 R4 documentation erratum is recorded here: the fresh execution root
is `.generic_chess_flow/f48-r4-prerequisite-closure-final-v3/`, and the actual
R4 Git diff contains exactly six files, as enumerated in H49A. No F48 rerun is
authorized for this documentation correction.

## Frozen diagnostic design

H49A requires evaluator-neutral structural reporting for the F48 control:
total and unique identities, duplication and ply histograms, effective unique
fraction, legal-action distribution, inventory/capture/remove/type/promotion
events, and hand/drop-state changes where applicable. It pre-registers exactly
two holdout-style diagnostic strata per RuleSet:

- `S49-M` (`MID_REACHABLE_UNIQUE`): seed `490100`, 64 unique non-terminal
  positions, target plies 8..20, core legal actions, first-valid deterministic
  generation order, and a 100000-candidate attempt cap.
- `S49-E` (`INVENTORY_EVENT_UNIQUE`): seed `490200`, 64 unique non-terminal
  positions, target plies 6..24, at least one generic inventory-changing
  history event, at least two legal actions, the same deterministic order and
  attempt cap.

Failure to fill either stratum is recorded as
`STRUCTURAL_STRATUM_UNAVAILABLE`; the predicate and cap cannot change after
observing results. Neither stratum becomes training data automatically.

The leverage surfaces are fixed as L49-0 single-type local at factors ±25%,
L49-1 learner-direction local using the frozen M48-1 direction families,
positivity and median rescaling, and L49-2 diagnostic single-type factors
0.50 and 1.50. L49-0 and L49-1 run at 500, 2000, and 8000 nodes. P48-0
teacher stability is measured at 10k/20k, 20k/40k, and 40k/80k, including
failed searches, score-sign agreement, top-action stability, and convergence.

Only where a diagnostic teacher is stable may the audit run the non-training
control over existing dynamic mobility, promotion-potential, and applicable
anchor escape/safety coefficients. Production defaults remain untouched and
no feature family is added.

## Interpretation and boundary

H49A freezes descriptive gates for learner-direction signal, single-type
signal, 40k/80k stability, and a 0.05 absolute structural-corpus gain over
the control. It preserves the four causal distinctions: learner geometry,
corpus architecture, native teacher stability, and material-only
representation limits. An executable precedence and F50 mapping is frozen in
the manifest before any measurement. No TDLeaf training, M48-1 optimization,
production evaluator/search change, AlphaSho comparison, F50 execution, or
master promotion is allowed.
