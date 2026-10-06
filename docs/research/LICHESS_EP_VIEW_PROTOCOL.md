# Fixed-source EP representation correction, not another puzzle

Freeze2026-10-06 after the original preflight failed, with its bytes/source
and52 author pushes/3836 charged legal entries preserved. Observed failure
is EP representation: complete PGN gives root a6 after a7-a5, API FEN omits
it. Same board/actor/rights; do not change ply, sample, formula or answer.

Pinned source Board reconstructed from the LAST ALREADY SAVED author FEN,
no source push/PGN replay. Check is_valid, advertised board/actor/rights,
actual saved lastMove, and source has_legal_en_passant=False. Board.fen()'s
legal-EP convention must equal API first4 fields; Board.fen(en_passant='fen')
retains a6. API half/full counters0/1 are display serialization, NOT imported
into local history; actual PGN0/27 remains evidence. Preserve all52 ancestors
and note snapshot Board has no move stack: it is a legal-action/EP view only,
not a new full-history terminal certificate. Original error remains CLOSED.

Return ALL root moves/branch count and declared full-history+child+three-
actual-search event lower bound L+4b. At most128 legal entries/15sec, zero
push/game/table query. Source cumulative counts include prior3836 entries.
Also report L+b for pure complete-child-table arithmetic, with existing
runtime integration used separately rather than blindly repeating three
actual searches. This is a cost alternative, not permission to skip legal
history or future independent terminal checks. No local events launched.
