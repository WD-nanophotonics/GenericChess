# GenericChess F7 evidence

## Status

`F7_RESULT = AUDIT_ONLY_PASS` and `H7B_CREATED = false`.

## Diagnosis

Exact duplicate attack queries were material after F6. Semantic aggregate
duplicate rates were 25.19% in Profile A and 54.72% in Profile B. Diagnostic
call-site attribution showed repeated work primarily through S3 invariant and
runtime gave-check paths, with additional uncategorized semantic callers.

## Candidate and gate

The opt-in candidate used a bounded 4096-entry cache keyed by exact immutable
Position semantics, ruleset fingerprint, queried square, and attacking owner.
Cache hits still invoked the caller checkpoint. Differential parity passed on
the four certified prefixes and curated S4 fixtures.

Performance did not authorize H7B:

```text
Profile A: 1474.436 ms -> 1543.808 ms (-4.70%)
Profile B: 4899.751 ms -> 3728.512 ms (+23.90%)
```

Profile A breached the H7B Route B floor of -2%, and the final F7 gate also
requires both profiles to improve by at least 8%. No production cache was
retained.

## Validation

F7 harness, F6/F5 regressions, full pytest, and fresh Zig build are recorded in
the closure artifacts. F4/F5/F6 evidence is preserved byte-identically by
before/after SHA-256 manifests.
