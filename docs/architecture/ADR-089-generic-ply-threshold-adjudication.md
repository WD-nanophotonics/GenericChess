# ADR-089: Generic ply-threshold automatic adjudication

Status: Accepted for F28 foundation certification

## Decision

GenericChess represents optional automatic, action-independent adjudication as
an immutable `RuleAutomaticAdjudication` definition.  Its stable id,
completed-move threshold, generic outcome, and continuation policy are part of
the RuleSet JSON and therefore change the gameplay fingerprint when present.
The empty default is omitted from JSON, preserving historical fingerprints and
serialized RuleSets.

The first policy, `threshold_actor_continuous_check`, evaluates the canonical
`HistoryRecord` at `history[trigger_ply]`; index zero is the initial-position
sentinel.  A non-checking threshold move resolves immediately.  A checking
threshold move remains pending through defender replies and subsequent moves
by the threshold actor that continue checking.  The first non-check by that
same actor resolves the configured outcome.  Current-position check state is
not the authority.

The immutable terminal path, semantic executor, and `SearchPathRuntime` use
one shared history evaluator.  Missing or truncated history at or beyond the
threshold fails closed with a deterministic context error.  While a checking
extension is pending, fallback `MAX_PLY` is suppressed.  Existing checkmate,
perpetual-check, and repetition precedence remains ahead of this primitive;
fallback max-ply remains below it.

`TerminalStatus.NO_CONTEST` maps to session `NO_CONTEST`, has no winner, is
rendered as `no-contest/restart`, and receives zero AlphaBeta score.  It is a
terminal result rather than a declaration choice.  No action generation,
declaration formula, repetition algorithm, SearchPathRuntime identity, or
Native implementation is changed.

## Scope and boundary

F28 certifies the generic foundation with an audit-only Standard-Shogi-derived
RuleSet.  The live `build_standard_shogi_ruleset()` remains unconfigured and
its product fingerprint remains unchanged.  Product adoption, replay
administration, side swapping, bilateral agreement, and time control remain
the F29 product-integration boundary; this ADR does not claim tournament-ready
full Shogi support.
