# Frozen constructed Shogi support argument

Test one specified full-inventory Shogi mate layout, not more random proposals.
It retains the existing physical law, source (3,3), shadow-Pawn file condition,
empty hands, common thirteen-current-type quiet screen and global custody task.
Owner0 focal R replaces one initial Pawn at scoring; the physical frame keeps P.

Own K=(1,6), B=(2,7), R=(4,0), L=(0,0),(8,0), N=(5,0),(6,0),
G=(1,0),(2,0), S=(3,0),(7,0). Own physical Pawns: focal(3,3),
(0,2) and (files1,2,4,5,6,7,8 at rank4).
Enemy K=(0,8), L=(0,1),(8,1), R=(4,1), B=(7,1), G=(1,1),(2,1),
S=(3,1),(5,1), N=(4,3),(6,3), Pawns=(0,3) and(files1..8 at rank2).
No other squares, repair search or hands. All 40 physical initial tokens remain.

Pre-execution prediction: neither King starts in check under any queried type.
The unpromoted R capture (3,3)->(0,3) checks file0 to enemy K=(0,8).
Own K covers(0,7),(1,7), B covers(1,8). Enemy sliders are blocked or cannot
reach the checking segment; backward-pointing enemy Knights cannot reach it.
Thus the legal board capture should immediately checkmate, with no Pawn-drop
mate ambiguity. Capture transfers the Pawn into the acting side's hand.

Verify exact initial inventory, both Pawn owners' unique files/allowed ranks,
all nonfocal L/N mobility, and the unchanged all-current-type common screen.
Exhaust every focal action/reply, replay the unique unpromoted capture, then
independently enumerate replies from the raw postcapture Position, check enemy
King and Core winner, and confirm hand Pawn custody. One scored root, 2,000
materializations, ten seconds, external15-second timeout. Failed premises reject
this stated witness; no layout repairs in this experiment.

A pass proves positive Shogi R support under this unchanged synthetic law;
it does not establish frequency, nonterminal exchange support, useful ratios,
additivity or reachable play. Keep earlier negative/incomplete records intact.
No source averaging, engine changes, human references or extra workers.
