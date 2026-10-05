# Active pinned-Queen mechanism: certified winning candidate branch

New single root/full public history: own K e6/P f7/R h8/N a5, enemy K d8/Q g8/
N e5. All21 root actions and children remain, with canonical selections frozen
before new goal observations. The unchanged old contact family selects
f7xg8=Q under BOTH declared laws; unit chooses Kxe5, zero Kf6.

After contact's move, the COMPLETE enemy set has exactly Kc7. Own Qd8 gives
authoritative checkmate, with R support and Knight escape coverage. Thus the
candidate branch and root have full minimax value1; candidate regret is0.
For both actual baseline choices, legal Qxh8 removes the R and checks the moved
King. Every legal own response is saved and none mates. Their two-own-action
mate-window values are0, versus candidate1. Eventual baseline goals remain
[-1,1] and full regret[0,2]; no strict full-WDL improvement is certified.

Actual successful evidence:21 root child edges+1 enemy edge in saved first
phase, then12 previously unobserved edges from saved states. Total34 transitions,
622 explicit action entries,0.219sec,0 external source queries. Full plies0/1/2/3
and consistent histories preserved. The first phase's tuple/Square comparison
failed after saving all31 own replies; continuation corrects only coordinate
binding and reuses exact states/choices, never replaying22 completed edges.

## Canonical ties and scientific scope

Unit's best-score tie contains contact's winning move; zero ties all21 actions.
The actual canonical baselines fail the bounded mate window, but both can select
the candidate under another tie. Mate-window advantage over FULL ties is[0,1],
not strictly positive throughout. This is synthetic changed-premise mechanism
evidence, not natural-play frequency, untouched validation or five-mode prior
completion. No root replacement, source/holdout fitting or duration tuning.

Together with CHESS_KNIGHT_INTERPOSITION_RESULTS, the same independently frozen
material family can select a forced mate or an immediate loss depending on
interaction. This supports use beneath tactical search, not standalone policy.
The appropriate next validation fixes search depth/terminal handling/action-order
cost independently, and reports paired goal intervals over a predeclared family;
do not enlarge current batches or retrofit a passing outcome population.
