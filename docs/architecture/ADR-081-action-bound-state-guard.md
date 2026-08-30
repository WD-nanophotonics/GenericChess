# ADR-081: Action-bound subjects for generic state guards

## Status

Accepted and implemented in F24E.

## Context

F24D found that a state guard could scan all matching pieces and apply a rank
selector, but could not bind that selector to the piece at the candidate
action's source. Combining an `exact(source)` guard with a `same_rank` guard
did not make the two predicates refer to the same piece. This made an
otherwise generic pawn double-step preflight unsound.

## Decision

Add the optional definition-layer field
`RuleStateGuard.subject_ref: RuleSquareRef | None = None` and lower it to the
matching optional `CompiledStatePredicate.subject_ref`.

When absent, guard behavior is unchanged: the executor scans the board and
performs the existing owner/type/promotion/spatial aggregation. When present,
the executor resolves the reference once against the immutable pre-action
binding and inspects only the piece at that index. An unresolved or empty
subject is zero matches. Existing owner/type/promotion/spatial filters and
comparison operators remain common to both paths. All existing square
references are valid; no new square-reference or game-specific primitive is
introduced.

The same compiled predicate path is used by legal generation, pseudo-attack,
S3 reply probes, and Python semantic execution. The Native payload currently
has no subject field, so a non-null subject is rejected explicitly during
Native lowering and the Python route remains available. Rulesets with only
the default `None` field retain their prior Native eligibility behavior.

## Consequences

- Western source-bound preflight can distinguish starting-rank and
  non-starting pawns for both owners without chess-specific code.
- RuleSet JSON emits `subject_ref: null` for old/default guards and accepts
  omitted, null, or valid square-reference forms on input.
- Subject-bearing rulesets have distinct gameplay fingerprints; metadata-only
  changes remain fingerprint-neutral.
- Full Western perft certification is deferred to F24F after F24E regression
  and preservation gates pass.
