# Chess historical capture outside the intrinsic ledger

The Xiangqi safety and Shogi nifu checks show coarse local event
ledgers *overcounting* executable moves in specific states. Are the
ledgers always a legal-action upper bound? A Western Chess en-passant
position gives a direct counterexample.

`scripts/audit_chess_en_passant_ledger_boundary.py` starts from the
perft-tested Chess position
`7k/8/8/8/4p3/8/3P4/K7 w - - 0 1`, legally advances White's Pawn from
index 11 to 27 by a double step, and compares the resulting Black
Pawn's executable actions with the existing intrinsic occupancy ledger.
The history/auxiliary en-passant patterns are explicitly excluded by
that ledger. No material values or search outcomes are used.
Reproduce with `.venv/Scripts/python.exe scripts/audit_chess_en_passant_ledger_boundary.py`.

| After White's double step | Source → destination |
| --- | --- |
| Intrinsic Black Pawn action | 28 → 20 (ordinary advance) |
| Additional executable legal action | 28 → 19 (en-passant capture) |

The legal-only action captures the White Pawn at index 27 while moving
to empty index 19. Its eligibility depends on the immediately preceding
double step. The static ledger's empty-target and local occupancy
conditions cannot infer that history, and it reports both en-passant
patterns as excluded.

A paired diagnostic clears only the en-passant auxiliary slot while
keeping the board, hands, and side to move identical. Black's legal
Pawn actions then contain only `28 → 20`; `28 → 19` disappears. This
isolates history/auxiliary state as the missing information. The
cleared-slot state is a semantic control, not a separately certified
reachable game history.

Together with the Xiangqi and Shogi witnesses, this establishes that
the intrinsic ledger is **neither a global upper nor a global lower
bound** on executable legal actions. It can overcount when dynamic
safety or state guards reject an event and undercount when a legal
history-dependent action is outside its scope. A future material prior
must report both directions of this approximation or model the
conditions under a declared context distribution.
