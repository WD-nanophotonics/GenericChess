# Explicit nonpromotable grammar correction

Preserve the failed Chess control unchanged. Its first rejected BOARD pattern
has promotion_mode=none; native N/B/R/Q cannot promote. Listed legacy patterns
are drops, already excluded by the original kernel. Castling was conjectured
in a progress update but is NOT an observed cause of this failure.

Before a separate correction count, admit none ONLY when all requested physical
origins are nonpromotable, native base=current, promoted=false, no explicit
promotion target. Keep every other original grammar/path/effect check. This
does not erase or select patterns; the original full compiled input is used.
Reject Pawn, Shogi promotable sources, forced/explicit/unknown contracts.
Reuse the pinned kernel by subclass, never change it or the failed producer.

New output compares all four counts against prior independent arithmetic and
reports whole compile/count cost within original128/5000/15sec limits. No
engine events, transitions or goal labels. This correction qualifies a named
board virtual task, not native full-game adjudication or castling/drop access.
