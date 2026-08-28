# ADR-024: Semantic attack query reuse

Status: Accepted as audit-only closure for F7

## Context

F7 measured exact repeated semantic attack/check queries after F5 and F6.
Duplicate identity included the complete immutable `Position`, ruleset
fingerprint, target square, and attacking owner. Hashes were diagnostic only.

## Decision

Do not retain production memoization. Exact reuse was material: Profile A had
25.19% aggregate duplicates and Profile B had 54.72%. The bounded exact probe
passed attack/check, legal-order, S3, S4, and search parity, and improved
Profile B substantially. However Profile A regressed 4.70%, below the H7B
Route B floor of -2%, so H7B was not authorized.

The probe remains harness-only, bounded to one isolated worker operation with
an exact Position key and checkpoint observation on hits. No production cache,
TT change, history change, attack map, bitboard, or F6 geometry promotion was
made.

## Evidence

Closure evidence is preserved in the historical F7 commit indexed by
`docs/archive/HISTORY.md`.
Previous F4/F5/F6 evidence is hash-bound before and after F7.
