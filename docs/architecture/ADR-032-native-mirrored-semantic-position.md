# ADR-032: Native Mirrored Semantic Position Frame

## Decision

Build and certify an opt-in Native semantic position mirror outside Core, but
do not retain it in production AlphaBeta after the F15 economic gate fails.
Select `NATIVE_POSITION_RUNTIME` as the next separately authorized boundary.

## Ownership

Python `Position`, `GameState`, and `SearchPathRuntime` remain authoritative.
The Native capsule is a synchronized shadow only. It may never overwrite
Python truth or decide legal moves, attack/check, terminal status, evaluation,
TT identity, or search policy in F15.

## Boundary

Core remains Native-unaware. The mirror lives in the AI/Native integration
layer and is exercised by an opt-in audit hook only. The H15B hook was removed
before E15 closure, so default search constructs no Native mirror.

## Contracts

The root pack transports full board state, hands, auxiliary state, side, ply,
fingerprint, and exact four-word SHA-256 history. Opaque history rejects the
mirror and preserves Python fallback. Public semantic actions are packed
losslessly from their explicit pattern/geometry/type/source/target/promotion
identity without enumerating guarded actions in the push path.

Combined push/pop is atomic: Python push failure leaves the mirror unchanged;
Native push failure rolls Python back; body exceptions restore both exactly
once. Parent capsule references are restored on pop, so live capsules are
O(depth) and siblings are not retained.

## Evidence and economics

All Standard Shogi and generic semantic sync oracles passed, as did search
logical parity and F13/F14 regression. However, measured aggregate overhead was
9.28% for Profile A and 6.25% for Profile B, exceeding the required 7% gate;
Profile A projected net routing headroom was 6.85%, below the required 8%.
Therefore this ADR records an audit-only foundation rather than a retained
production optimization.

## Consequence

No F15 production speedup is claimed. Native attack/check routing remains
deferred. A stronger Native position runtime stack is the only selected next
boundary, and it is not implemented by F15.
