# ADR-088: Standard Shogi declaration product integration

## Status

Accepted for F27 on `sandbox`.

## Decision

The production Standard Shogi `RuleSet` owns two generic, owner-bound
declarations (`claim_owner_0` and `claim_owner_1`).  They use the certified
three-rank enemy-camp zone, king and eleven-piece guards, not-in-check and
`ply_count < 500` guards, base-identity scoring (K=0, R/B=5, all other listed
unpromoted bases=1), and the exact 31 WIN / 24 RESTART / otherwise LOSS bands.

Declarations are session decisions, not `Action` values.  `GameSession` keeps
the authoritative `GameState` and board history unchanged while recording a
terminal declaration result.  GameRecord keeps ordinary games on schema v1;
declaration-bearing games use schema v2 with one final `DeclarationRecord`.
Replay recomputes the declaration through the current ruleset and rejects
tampered actor, outcome, or score fields.

AlphaBeta assesses declarations at every ongoing search node after Core
terminal precedence.  WIN uses the existing mate-distance scale; RESTART is
an optional zero floor; LOSS is never a search choice.  The search runtime
does not create declaration transitions, and TT identity remains unchanged.

## Consequences

Nyugyoku is product-supported, so the Standard Shogi fingerprint changes from
the historical F25 pre-declaration identity.  The separate official 500-move
impasse/no-contest procedure remains unsupported, and full-rule product
readiness therefore remains false.  Native semantic execution continues to
fail closed for declaration-bearing payloads, with Python as the authority
fallback for this boundary.
