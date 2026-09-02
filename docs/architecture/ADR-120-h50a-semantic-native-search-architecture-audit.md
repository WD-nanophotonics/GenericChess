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

The current semantic Native path is not yet an iterative search path. Missing
primitives are semantic TT identity/value/bound handling with evaluator
isolation, deterministic node/time budgets, cancellation, complete
continuous-check adjudication or an explicit gate, public exact action/PV
conversion, and Core PV replay verification. The Native semantic compiler
also rejects the complete Western fixture at its current `max_ply` and
`subject_ref` lowering boundary, and rejects Standard Shogi declarations;
these are explicit F50B certification gates, not legacy fallbacks.

## Rule coverage

The semantic IR/runtime represents Western pawn single/double steps, pawn
captures, en passant, promotion, castling, castling rights, and en-passant
auxiliary state. Standard Shogi ordinary moves, promotion, drops, hands,
nifu, and uchifuzume are represented, while continuous-check repetition and
declaration adjudication remain Native gaps. The H48B selected generated
surface is currently a legacy `CompiledRuleSet` object, so semantic-Native
execution is not certified there; future F50B certification must include a
compiler-produced generated RuleSet.

## Scope and consequences

H50A is audit-only: no production `generic_chess/` code, native C/H code,
RuleSet, compiler, F49 runner, S49 corpus, learner, or F50B implementation is
changed. F50B is not started. The next implementation must reuse the existing
semantic IR/compiler/runtime authority and must never project semantic
special actions through incomplete legacy movement atoms.
