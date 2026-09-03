# H50B2C corrective: root ply score parity

## Decision

Root-parallel semantic search preserves the original root's ply origin when
scoring winner terminals. The ordinary iterative entrypoint uses an internal
root offset of zero; each isolated root-child search uses an offset of one.
Terminal scoring therefore uses `root_offset + local_recursive_ply` rather
than the local recursive ply alone.

The offset is an internal search contract and is restricted to the two
supported entry conditions. It is not part of the public semantic position
ABI or position identity.

## Evidence

- Western mate-in-one now has exact score, action, and principal-variation
  parity between single-thread and root-parallel search.
- A deeper terminal line has exact score and principal-variation parity.
- Root-parallel results are identical at 1, 2, and 4 workers, and the root
  position remains unchanged.
- Focused and normal regression suites pass: 100 tests total.

## Scope

This correction does not reopen live-history copying, performance-report
formatting, provenance, or full architecture certification. The next search
boundary remains the semantic transposition table work order.
