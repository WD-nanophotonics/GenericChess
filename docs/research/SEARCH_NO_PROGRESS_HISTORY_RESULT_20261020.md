# AlphaBeta honors generated no-progress history at searched children — 2026-10-20

## Question

Do two generated-rule roots with the same current board and repetition counts
but different recent action histories produce the correct history-dependent
child adjudication through the public AlphaBeta caller?

## Existing fixture and added assertion

Reuse `tests/product/test_no_progress_search_context.py::pair`. The two
semantic sessions share the same board and repetition-count map but have
different no-progress contexts. At the tested depth, one history makes the
selected quiet child a `NO_PROGRESS_DRAW`; the other leaves its selected child
ongoing. The existing warm-player test already compared reused and fresh
searches, but only asserted their mutual parity. It now also checks the exact
selected-child status and expected score in each context, with and without
forced history-digest collisions, while preserving the input root.

## Result and consequence

Both public searches retain their historical context: the first selects a
no-progress draw at score 0, the second selects an ongoing child at score -77.
The updated module plus adjacent no-progress fact/draw, SearchPathRuntime, and
AlphaBeta suites pass. This makes one generated history-sensitive caller
contract explicit; no search code or state representation changed. It does
not establish all possible history rules or a general evaluation-quality claim.
