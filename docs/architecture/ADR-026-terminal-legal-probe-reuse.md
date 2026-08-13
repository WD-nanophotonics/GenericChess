# ADR-026 — Terminal legal-existence probe reuse

## Decision

F9 closes as `AUDIT_ONLY_PASS`. The audit found a real but narrow duplicate:
terminal legal-existence probing and later full legal generation operate on the
same child Position, and the first canonical S3 candidate is repeated when the
child later requests the full legal set. No H9B production optimization is
authorized or retained.

## Findings

Across the four certified semantic prefixes and five measured repetitions:

- Profile A: 590 eligible pushes out of 5,950 semantic pushes (9.92%).
- Profile B: 2,500 eligible pushes out of 25,750 semantic pushes (9.71%).
- The repeated prefix was one canonical candidate/S3 trial; first legal rank
  median, p90, and max were all 1.
- Measured repeated-prefix time was about 116.5 ms in Profile A and 692.2 ms
  in Profile B.

Candidate B requires at least 85% of ongoing children to request full legal
actions; it is not eligible. Candidate A would require retaining a generator
or cursor across the terminal/search API boundary, rebinding the checkpoint,
and guaranteeing frame-local destruction. That is not a local safe change under
the frozen F9 contract, so it is rejected as `CANDIDATE_A_NOT_LOCAL`.

## Consequences

The existing terminal/search behavior, canonical order, S3/S4 semantics,
checkpoint policy, history, and rollback remain unchanged. The measured reuse
is deferred to a separately authorized phase. F4–F8 evidence remains
byte-identical.
