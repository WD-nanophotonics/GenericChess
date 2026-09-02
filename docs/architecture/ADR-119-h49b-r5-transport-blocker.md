# ADR-119: H49B-R5 semantic-to-legacy transport blocker

Status: Accepted blocker record

## Context

The F49 S49 corpus is authored by `semantic_execution`, while the Native
diagnostic path uses the existing `legacy_transport`. R5 was authorized to
bridge only lossless semantic public actions to ordinary `BoardMove` and
`DropMove` actions, with full lockstep position/action validation.

## Decision

Fail closed and preserve the R5 result as an architectural blocker. The
canonical Western initial semantic legal set contains 20 actions, but its
legacy transport exposes only 4. All 16 initial pawn actions, including
`sem_11_pawn_double_step:g34:e2-e4`, are absent from the legacy legal set after
the permitted physical projection. Shogi and the selected generated RuleSet
remain 30/30 and 14/14 respectively.

No production code, RuleSet, corpus seed, or Native search behavior is changed.
The existing R4 authoritative root remains permanently quarantined. The
machine-readable evidence is frozen in
`tests/fixtures/h49b_r5_blocker_evidence.json`.

## Consequences

R5 cannot be published as an accepted measurement runner under the current
transport contract. A future work order must either provide a transport that
represents semantic special actions or select a measurement route that keeps
full-state and action parity. S49 regeneration and Native/Python search remain
forbidden until that boundary is resolved.
