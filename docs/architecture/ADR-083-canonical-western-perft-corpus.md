# ADR-083: Canonical Western Chess perft corpus correction

## Status

F24G passed and established Western move-legality certification.

## Context

F24F correctly stopped at the first supplied Kiwipete mismatch, but the
controller work order paired canonical totals with three mistyped FENs. The
F24F artifacts are preserved byte-for-byte and remain historical evidence of
that benchmark-manifest error.

## Decision

F24G freezes the corrected six-position manifest in
`scripts/audit_f24g_canonical_western_perft.py` and reruns the exact F24F
RuleSet, FEN loader, and perft implementation without production changes.
The manifest digest and performance rows are retained in
`tests/fixtures/f24g_canonical_western_perft.json`.

The canonical totals all match: initial 20/400/8902/197281; Kiwipete
48/2039/97862; position 3 14/191/2812/43238; position 4 6/264/9467;
position 5 44/1486/62379; and position 6 46/2079/89890. Therefore
`WESTERN_CHESS_MOVE_LEGALITY_CERTIFIED = true`.

The F24F 45-versus-48 observation is classified solely as
`BENCHMARK_CORPUS_FEN_EXPECTED_PAIR_MISMATCH`, not as a move-generation,
castling, pawn, or perft-harness defect.

## Consequences

- Production diff remains zero; `master` is locked and no promotion occurs.
- Native unavailability remains expected because the frozen RuleSet uses the
  F24E `subject_ref` primitive.
- The next boundary is
  `F24H_WESTERN_CHESS_RULESET_PRODUCTIZATION_AND_REFERENCE_SEARCH_BASELINE`.
