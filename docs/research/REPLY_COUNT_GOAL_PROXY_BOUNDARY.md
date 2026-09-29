# Reply count alone is not a game-independent goal proxy

**Unknown.** Could a rule-derived static prior value actions by how many
legal replies they remove from the opponent, with zero replies as the
best terminal-progress event? This would supply a goal-linked
alternative to the rejected first-action service count.

**Smallest direct check.** Reuse two independently certified executable
RuleSet witnesses; no new formula or material reference is needed.

| RuleSet and action | Opponent legal replies | Result or eligibility |
| --- | ---: | --- |
| Chess `Rb5a5` on the frozen mate root | 0 | Legal; White checkmates and wins |
| Chess stalemating action on the same root | 0 | Legal; draw |
| Shogi unpromoted board-Pawn advance in the paired control | 0 | Legal; checkmate |
| Shogi held-Pawn drop to that **same resulting `Position`** | 0 hypothetically | Forbidden pawn-drop mate |

The Chess root has [two immediate mates and nineteen immediate
stalemates](CHESS_ROOT_TERMINAL_LABELS.md), certified by both Python and
native transitions. Checkmate and stalemate are each no-legal-reply
terminal statuses, but their payoffs differ. The Shogi pair is checked
in [the action-form control](SHOGI_PAWN_DROP_MATE_BOUNDARY.md); the
[Japan Shogi Association rules](https://www.shogi.or.jp/match/taikyoku_rules/)
explicitly prohibit pawn-drop mate in Article 10.

Thus a scalar based only on the *count* of opponent replies cannot
distinguish Chess win from draw, and it would assign a desirable zero
to an illegal Shogi action if legality were not checked first. A
terminal-status-aware, action-legal objective could distinguish these
cases; this check does not reject every response-based model. Such a
model would still need an independently specified context measure,
search horizon, and tradeoff between nonterminal reply changes and
terminal outcomes before it could justify relative material values.
Xiangqi material values remain sealed.
