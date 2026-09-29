# Standard Shogi pawn-drop state boundary

The coarse held-token ledger applies the compiled destination mask and
empty-target condition but records same-file pawn and drop-mate guards
as exclusions. To test a direct consequence, `scripts/audit_shogi_pawn_drop_boundary.py`
compares its owner-0 pawn-drop targets with executable `legal_actions`
in two synthetic Standard Shogi states. Both have two Kings, one held
Pawn, and a same-file board Pawn at index 40 (file 4, rank 4). The only
change is whether that board Pawn is unpromoted `P` or promoted `TP`.
Reproduce with `.venv/Scripts/python.exe scripts/audit_shogi_pawn_drop_boundary.py`.

| Board Pawn type | Coarse empty targets | Executable legal drops | Coarse only |
| --- | ---: | ---: | ---: |
| P | 70 | 64 | 6 |
| TP | 70 | 70 | 0 |

For `P`, the six coarse-only empty targets are indices 13, 22, 31, 49,
58, and 67, all on file 4; index 40 is occupied. For `TP`, those same
targets are legal because the same-file restriction concerns an
*unpromoted* Pawn. The two states isolate a state guard with no change
to the compiled static drop mask. They are diagnostic states, not a
distribution of game play, and do not test the separate drop-mate
postcondition. No human material values enter this check.

Therefore a coarse drop count cannot be read as the number of fully
legal drops or converted into a hand-value premium without a declared
state measure. The exact difference depends on the board's current
unpromoted-pawn files and other legality conditions. Do not assign a
constant pawn correction from this witness.

## Projection-identifiability consequence

The `P` and `TP` states have exactly the same empty/own/enemy label at
every square and the same held Pawn. Yet their legal-drop sets differ by
six. V2C's occupancy event measure sees precisely that three-label
projection; its token ledger lists possible promotion targets but has
no distribution over their current states on a file. Therefore no
postweighting that depends only on the old three-label V2C occupancy
input can recover the nifu-conditioned drop probability. A future
model would need typed, promotion-aware state information and an
explicit measure over those states. This is a loss-of-information
statement, not a claim that exact nifu probability is intrinsically
uncomputable.
