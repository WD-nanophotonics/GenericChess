# GenericChess F9 evidence

## Status

`F9_RESULT = AUDIT_ONLY_PASS`  
`H9B_CREATED = false`  
`reason = CANDIDATE_A_NOT_LOCAL_AND_CANDIDATE_B_ELIGIBILITY_FAIL`

## Gmail / inbox provenance

The complete authoritative Gmail body for
`GenericChess — F9: Semantic Terminal Legal-Existence Probe Reuse Audit + Evidence-Gated Continuation`
was saved to `inbox/2026-08-14_GenericChess-F9_Semantic_Terminal_Legal-Existence_Probe_Reuse_Audit.md`
before execution.

## H9A diagnosis

`terminal_from_search_runtime()` performs an early-exit semantic
`has_legal_action()` probe. If the pushed child later enters search,
`SearchPathRuntime.legal_actions()` restarts the canonical full legality
traversal. On exact same-position eligible pushes, the first legal candidate
has rank 1 in both profiles and its S3 trial is repeated.

The opportunity is uncommon: 9.92% of Profile A semantic pushes and 9.71% of
Profile B semantic pushes later request full legal actions before pop. Measured
repeated-prefix time is approximately 116.5 ms and 692.2 ms respectively.

## Candidate route

Candidate B is disqualified by the frozen 85% eligibility rule. Candidate A is
not local: it would need a retained generator/cursor and checkpoint rebinding
across separate APIs, with explicit frame-local rollback destruction. Therefore
no H9B candidate was created, and no candidate performance or production
forwarding was attempted.

## Validation

Focused F9/H8/runtime suites passed. Full pytest passed 100%, and the fresh
supported Zig build passed. F4–F8 evidence and ADRs were verified unchanged by
before/after SHA-256 manifests. No F10 work was started.
