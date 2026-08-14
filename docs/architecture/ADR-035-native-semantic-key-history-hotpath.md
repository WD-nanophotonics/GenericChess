# ADR-035: Native Semantic Key/History Hot-Path Optimization

## Status

Rejected for retention in F18; H18A audit-only candidate recorded.

## Context

F17 identified the exact Native semantic position-key/history append path as the remaining cost center after the bounded delta prototype failed its lifecycle gate. F18 authorized only exact canonical streaming SHA-256 and direct raw-digest history append, without changing external identity.

## Evidence

The old Native path sorted public type IDs and auxiliary slots on every call, grew a heap JSON buffer, hashed the completed canonical bytes, hex-encoded the digest, and then reparsed the hex for history words. H18A froze 196 key rows and found zero old-Native/Python mismatches.

The test-only candidate precomputed immutable canonical ordering metadata, streamed exact canonical bytes through a bounded chunk buffer, emitted raw SHA-256 bytes, and compared raw/direct history append against hex/reparse history append. Candidate parity was exact, but the best public-key result was 1.19× versus the required 1.67×, and raw/direct history was 1.19× versus the required 1.20×.

## Decision

Do not retain H18B. Restore the F17-closed production Native source. Preserve the candidate, oracle, benchmarks, and rejection evidence only for audit traceability. Select `NATIVE_POSITION_KEY_ARCHITECTURE_REASSESSMENT`; do not implement it in F18.

## Consequences

```text
F18_RESULT = AUDIT_ONLY_PASS
H18B_CREATED = false
EXTERNAL_POSITION_KEY_PARITY = PASS
CANONICAL_BYTE_PARITY = PASS
KEY_PERFORMANCE_GATE = FAIL
RAW_DIGEST_HISTORY_APPEND = FAIL
DELTA_RUNTIME_REQUALIFIED = false
SELECTED_NEXT_BOUNDARY = NATIVE_POSITION_KEY_ARCHITECTURE_REASSESSMENT
```

F4–F17 evidence and ADR-022 through ADR-034 remain unchanged. No F19 work is started.
