# Promotion association correction before any labels

Original record fails after12 local transitions/9 author pushes/0 probes:
the reused native-only FEN formatter deliberately rejects Pawn-origin promoted
pieces. Its guard is correct for its old native-only trial; do not relax it.
The evaluator already explicitly accepts ordinary Pawn-origin promotions.

V2 changes only this source-control board association to compare each current
piece type/owner directly with the author board, while binding local origin,
promotion and history in the saved full state. The root, policies, complete
choice set, criteria and source-label inventory stay unchanged. No labels or
policy scores were exposed by the failed original. This is adaptive development
repair, not newly restored independent-validation status. Preserve original
producer/raw pins. Charge original12+new12 local transitions and original9+new12
author pushes against the same64 local safety fuse; no hidden reset or repeat
until a favorable label. Board association cannot prove future goal equivalence.
