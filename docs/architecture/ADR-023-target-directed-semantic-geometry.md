# ADR-023: Target-directed semantic geometry audit

Status: Accepted as audit-only closure for F6

## Context

F5 closed the position-local `(owner, current_type_id)` source dispatch index.
F6 tested whether semantic attack/check work still paid a material cost to
materialize compiled geometry targets unrelated to one exact queried square.
The authoritative oracle was `geometry_candidates()` in
`generic_chess/rules/ir.py`.

## Decision

Do not authorize an H6B production change. The H6A candidate probe is retained
only in the audit harness. It scans the existing immutable compiled path and
avoids constructing unrelated candidate tuples, but it does not meet the fixed
usefulness gate: the 162-query attack microbenchmark was approximately 1x,
Profile A semantic aggregate improved 1.87%, and Profile B regressed 2.48%.

The exact geometry, attack/check, legal-order, S3, and S4 parity gates passed.
No public IR, fingerprint, board representation, search policy, TT/history
identity, or production semantic executor code was changed in F6.

## Evidence

Machine-readable closure evidence is under
`artifacts/f6_target_directed_semantic/`. The exhaustive geometry matrix is
losslessly grouped by `(geometry, owner, source)` with target-aligned arrays;
the H6A test still checks every target individually against the oracle.

## Deferred

Attack caches, incremental maps, bitboards, Shogi-specific shortcuts, Native
migration, and unrelated search/evaluator changes remain outside F6.
