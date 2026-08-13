# ADR-025 — Runtime push / terminal check deduplication

## Decision

F8 is closed as `AUDIT_ONLY_PASS`. The audit proved an exact duplicate check on
semantic runtime pushes, but the single-push checked-state forwarding candidate
did not pass the frozen final performance gate and was cleanly reverted.

## Evidence

`_push_impl()` computes `gave_check` for the exact child Position, then terminal
evaluation recomputes `in_check` for the same child and side. The bounded trace
found 100% exact duplication and zero boolean mismatches on the certified
semantic corpus. The opt-in candidate preserved terminal, history, continuous
check, search, and interruptibility parity.

The H8B candidate commit was `6a3b852` and its revert is `990fd4f`. Final
comparative semantic aggregates were approximately Profile A `+1.81%` and
Profile B `+8.76%`; neither frozen Route A nor Route B passed. No production
forwarding change is retained.

## Consequences

The duplicate is documented for a future separately authorized phase. No attack
cache, terminal cache, general memoization, bitboard, native, TT, or evaluator
change is introduced. F4–F7 evidence remains byte-identical.
