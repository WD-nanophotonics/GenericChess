# ADR-120: H50A semantic Native search architecture audit

Status: Audit checkpoint; awaiting independent review

Parent sandbox checkpoint: `e5263689d8f4f5dff8b33560ed786b4e23b4a6c5`

## Decision

Select `F50B_EXTEND_EXISTING_NATIVE_SEMANTIC_SEARCH` (Route A). The existing
semantic Native path already owns the compiled semantic payload, exact action
identity, full semantic position including auxiliary slots, checked
make/unmake, attack/check, terminal primitives, and a fixed-depth semantic
search probe. A second search-state authority would duplicate
`GCSemanticPosition`; the Python AlphaBeta path remains a control/diagnostic
route rather than the architectural default.

## Capability boundary

The complete matrix, source/dependency SHA-256 ledger, API inventory, and
route comparison are frozen in
`tests/fixtures/h50a_semantic_native_search_architecture_audit.json`.

The current semantic Native path is not yet an iterative search path. Remaining
F50B2 primitives are semantic TT identity/value/bound handling with evaluator
isolation, deterministic node/time budgets, cancellation, and Core PV replay
verification. F50B1 closes the Western `max_ply`/`subject_ref` and Standard
Shogi declaration, repetition, and exact public-action execution gates.

## Rule coverage

The semantic IR/runtime represents Western pawn single/double steps, pawn
captures, en passant, promotion, castling, castling rights, and en-passant
auxiliary state. Standard Shogi ordinary moves, promotion, drops, hands,
nifu, and uchifuzume are represented, while continuous-check repetition and
declaration adjudication are carried by the semantic Native closure. The H48B
selected generated surface is currently a legacy `CompiledRuleSet` object, so
semantic-Native execution is not certified there; F50B1 instead includes a
deterministic compiler-produced generic RuleSet witness.

## H50B1 execution-closure addendum

H50B1 keeps `CompiledSemanticRuleset.ir + .support` and `GCSemanticPosition`
as the only semantic authorities. Semantic payload version 3 adds an explicit
semantic history capacity of 1024, accepts Western `max_ply=1000` unchanged,
lowers generic `subject_ref`, and carries repetition-policy and automatic
adjudication metadata. Exact public conversion is exposed by
`generic_chess.native.semantic.public_action`; no semantic action is reduced
to legacy `BoardMove` or `DropMove`.

Standard Shogi declarations remain present on the compiled Native wrapper and
are assessed through the generic declaration contract with owner, outcome,
weighted score, failure outcome, and outcome bands. Exact history entries may
carry actor and `gave_check` metadata; Native terminal classification supports
ordinary repetition, continuous-check loss, and the generic automatic
adjudication trigger. These path fields are excluded from public position
identity. F50B1 still does not add iterative search, TT, budgets, cancellation,
or production routing; those remain the F50B2 boundary.

## Scope and consequences

H50A is audit-only: no production `generic_chess/` code, native C/H code,
RuleSet, compiler, F49 runner, S49 corpus, learner, or F50B implementation is
changed. H50B1 uses only the existing semantic IR/compiler/runtime authority;
F50B2 remains the next boundary. The next implementation must reuse the existing
semantic IR/compiler/runtime authority and must never project semantic
special actions through incomplete legacy movement atoms.

## H50B1-R1 corrective closure

R1 closes the declaration and history-contract corrections without changing
the selected Route A architecture. The Native C payload and runtime now own
the complete declaration contract, including outcome bands and weighted
metrics. Fresh history has an explicit sentinel event; imported incomplete or
non-sentinel event streams are marked non-exact for policy paths; and the
500-ply automatic adjudication is evaluated from complete history records.

The Western and Standard Shogi matrices, generic compiler witness, and
historical validation ledger are recorded in
`tests/fixtures/h50b1_r1_semantic_native_execution.json`. F50B2 remains
`NOT_STARTED`; no iterative search, TT, budget, cancellation, learner,
F49/S49, or production routing work is authorized by R1.
