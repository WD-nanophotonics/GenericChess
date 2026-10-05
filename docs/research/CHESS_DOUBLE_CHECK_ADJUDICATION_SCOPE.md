# Source conversion failure and narrowly changed qualification

The first source phase stopped BEFORE any outer tablebase query: complete=false,
outer_probe_calls0, cumulative active time0.141sec. Keep its producer/raw bytes;
do not overwrite or rerun it. The prelabel freeze remains valid and immutable.

Cause: using pinned python-chess Board.is_game_over() as an ongoing conversion
guard imports its automatic insufficient-material adjudication. Its outcome()
checks insufficient material,75-move/fivefold rules as well as mate/stalemate.
F24F has no such automatic insufficient-material terminal condition. The two
K/K/B children are valid, not checkmate/stalemate, and freshly local ongoing;
their complete histories have2 entries at ply1. The two K/K/R children also
pass these explicit checks. Source code evidence is the installed pinned
chess/__init__.py outcome() lines2041ff, already manifest-qualified.

Changed premise: for THIS zero-rights pawn-free F24F stratum, reject invalid,
checkmate or stalemate converted boards, and separately RECORD insufficient
material without importing it as local terminal. Always retain fresh local
terminal-first handling from prelabel requests. No rule/source data is changed.
An unlimited-game draw certificate can still imply finite-horizon draw under
the existing bridge; a package's automatic adjudication is not that proof.

A separately named single source-scope producer may answer exactly the SAME
four frozen child requests, with no new root/transition or replacement. It
requires the failed phase to have0 probes, pins that failure, and counts its
active time PLUS prelabel and new-phase time against the SAME15sec cap. Max20
outer calls remains. No automatic retry, additional tables or outcome fishing.
Any subsequent failure stays incomplete. Conditional source semantics remain
explicit even after full move-set and checksum qualification.
