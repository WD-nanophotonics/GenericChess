# Historical reference declaration-domain correction

Pinned auxiliary pre-fix source SHA256:
`cdbac7b7053144cfe36938ba46a669b902b0f381452976594c1f040694ff03e7`.
`reference_declaration_scope.json` preserves the actual pre-fix32768node/D8/
no-TT result: strong=true, root_value=LOSS for player1, about.497s.

The complete public session is reached by a real legal rook move from its
initial board. Player1 can immediately declare RESTART: actual SessionResult
is declaration/RESTART with winner=None; Core GameState stays ongoing/unchanged.
Thus a complete-session LOSS label is false, without needing an oracle for
any subsequent board game. The historical reference enumerates only runtime
board actions, so it cannot model this choice. Its source had no declaration
scope guard. Current PRIMARY source was not inspected/executed by this check;
this finding is pinned to the auxiliary source above, not an account-wide claim.

Correction: reject any nonempty declaration domain before search and return
`REFERENCE_SOLVE_UNRESOLVED:declarations` (strong=false/no values,0expanded).
A new session-aware reference is a separate future capability; the guard does
not implement one. TT/non-TT WIN/RESTART regressions physically declare the
actual result. The same no-declaration board control still proves LOSS.
Tests are standalone public-rule/session fixtures, requiring no auxiliary
session proof prototype or new Native game/training. Old scientific labels,
caps and frozen inputs are preserved; no retrospective relabeling is asserted.
