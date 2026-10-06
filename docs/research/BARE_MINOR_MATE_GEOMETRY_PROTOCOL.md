# Bare-minor local goal closure

Adaptive followup, no new source/holdout labels or coefficient choice. Unknown:
are promotion-to-B/N source draws also local draws despite absent automatic
insufficient-material adjudication? Enumerate all64-square placements of two
distinct nonadjacent Kings and one distinct White N or B. For every checking
Black-to-move placement, require a legal King escape or capture witness under
the exact Knight/Bishop/King geometry; Bishop rays account for White King
blocking and removal of Black King's old square. Hash all ordered witnesses.
Unspecified/nonchecking states do not imply mate. Bare opposing King cannot
legally check the owning King: adjacency violates the own-anchor safety rule.
After minor capture only bare Kings remain. Current B/N cannot promote/drop or
create another piece; native/Pawn-origin promoted current types dispatch the
same relevant ordinary moves. Pin the Western rule/executor and inspect these
conditions. No castling rights, hands, declarations or extra win adjudications.

Expected under450000 geometry worlds and a few seconds/small constant memory;
30sec finite safety fuse, no engine/tree search/workers/downloads. Counts are
reported rather than stopped at universal5000. Failure saves the first actual
counterexample. Pass is a geometric no-mate proof conditional on inspected
movement/rule correspondence, not exhaustive semantic-executor replay of all
worlds. Local finite max_ply1000 and draw-only stalemate/repetition then imply
eventual utility0 for these captured/uncaptured minor-only children. Do not
extend to two minors, opposing blocking pieces, variants or actual Chess clocks.
