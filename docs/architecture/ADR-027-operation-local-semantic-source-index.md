# ADR-027 — Operation-local semantic source index

## Decision

Reuse the semantic source index only within one legality operation. Build it once at
the beginning of the first board-pattern traversal, pass it through subsequent board
patterns, and discard it when the operation returns or is interrupted. Drop-only
operations do not build a board index. Attack queries remain independently scoped.

## Evidence

The F10 audit found repeated same-position construction caused by rebuilding
`_sources_by_owner_type(position)` for every board-move pattern. H10A measured roughly
75.0% redundant builds in Profile A and 71.6% in Profile B. Exact index equivalence
failures were zero.

The no-trace formal probe improved the four semantic cases by 9.79% in Profile A and
17.76% in Profile B, with every semantic case improving by at least 3%. Stable semantic
outputs, legal actions, search counters, history, terminal state, and TT behavior matched.

## Consequences

The optimization is local, interruptible, and rollback-safe. It does not introduce a
global cache, cross-position lifetime, or attack-query memoization. The optional parameter
keeps the lower-level iterator self-contained for callers that do not supply an index.

## Rejected alternatives

Cross-operation or cross-query caching was rejected because it would require an eviction
policy and stronger position-identity ownership than this audit authorizes. The F10 scope
ends at operation-local reuse.
