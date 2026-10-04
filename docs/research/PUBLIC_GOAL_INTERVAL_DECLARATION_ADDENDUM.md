# Declaration coverage addendum before extension runs

The first six tests covered board-action intervals only. Source inspection
found Session supports optional declarations outside legal_actions. Therefore
that adapter cannot claim full Shogi choice coverage. This is observed scope
friction, not a reason to rerun mate scoring or broaden the material corpus.

Extend only PublicGame's choice stream: include Core available_declarations
along with board actions. Reassess a declaration on the exact parent state;
an immutable virtual outcome leaf preserves parent GameState without mutation.
WIN has actor's +/-1 goal value. DRAW has0; RESTART has no specified W/D/L and
retains [-1,1]. Never equate replay/restart with draw. Invalid/stale assessments
fail. Available declarations omit LOSS choices; those and resignation are
dominated by any ordinary choice within [-1,1] on an ongoing state. They cannot
change minimax bounds; Core-terminal states forbid Session declarations.

Count total observed choice transitions separately from actual public board
materializations. Depth frontiers remain unknown even if an unqueried claim
would win; no automatic deeper search. Do not modify Core, Session, game rules,
declaration point weights, or the old frozen board-only protocol bytes.

Tests use the EXISTING Standard Shogi declaration-boundary fixture for each
owner: score31 WIN and score24 RESTART. These are declaration-rule controls,
not independent material labels or fitted priors. Frozen limits: depth1,
<=2 choices, <=3 visits per claim control; no larger Shogi search. Check Session
assessment agreement and unchanged parent history. Keep official stalemate
qualification and other full-game assumptions explicit.
