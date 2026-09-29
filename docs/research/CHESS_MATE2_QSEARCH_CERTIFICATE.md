# Exact short-mate certificate at a non-shortcut Chess root

**Unknown.** Can a frozen real Chess root avoid the searcher's immediate-win shortcut, have independent distinct action evidence, and expose a quiescence-dependent choice under fixed material control?

**Smallest observation.** Move the white king of the previously certified root from c1 to d1; freeze FEN `8/8/8/1R6/8/8/5R2/k2K4 w - - 0 1`. `scripts/audit_chess_mate2_qsearch.py` enumerates every root successor, opponent reply, and attacker continuation through ply 3, with 8,192-successor and 10-second certificate caps. An action is labelled forced mate in two only when *every* legal Black reply permits a White checkmate continuation. It compares the unchanged F156 indexed material profile in Python depth 1/2 with quiescence limits 0/4 and native no-quiescence depth 1/2. Each Python search has 2,000-total-node and five-second limits, no TT or ordering.

The root is ongoing, with 33 legal actions and no immediate winning action. The 612 generated certificate successors establish 6 forced mates in two and 14 immediate stalemate draws. The other 13 root actions are **unresolved at this three-ply bound**, meaning only that the short certificate does not prove a win. In particular, it does not prove an eventual draw or loss for any of them.

| Search | Selected action | Independent label | Score | Completed depth | Q nodes |
| --- | --- | --- | ---: | ---: | ---: |
| Python d1 q0 | Kd1e2 | Mate by ply 5; none by ply 3 | 12 | 1 | 0 |
| Python d1 q4 | Kd1e2 | Mate by ply 5; none by ply 3 | 12 | 1 | 22 |
| Python d2 q0 | Kd1e2 | Mate by ply 5; none by ply 3 | 12 | 2 | 0 |
| Python d2 q4 | Kd1c2 | Forced mate in two | 999999997 | 2 | 750 |
| Native d1/d2 q0 | Kd1e2 | Mate by ply 5; none by ply 3 | 12 | 1/2 | No qsearch |

For Kd1c2, native legal transitions independently confirm the sole Black reply Ka1a2, followed by a White checkmate continuation (Rb5a5). Both Python depth-2 searches completed under their limits. The evidence therefore shows that the quiescence setting changes whether this search chooses an action with a proven short forced mate.

**Additional bounded proof.** Independently of search scores, an attacker-OR/defender-AND legal-successor check for the q0-selected Kd1e2 proves no forced mate within three plies of the root, but a forced mate within five plies. It generated 406 successors under the 8,192-successor and 10-second caps. One explicit branch strategy is Kd1e2, Ka1a2, Rf2f3, Ka2a1, Rf3a3 checkmate; each Black turn on that line has exactly one legal reply. Native legal transitions separately confirm both single-reply counts and the final checkmate. Thus **both selected actions are certified wins**, with different proven mate horizons. There is no demonstrated W/D/L regret. The indexed profile remains an arbitrary parity control, not a material prior.

**Material identifiability limit.** Both certified selected lines use only king and rook quiet moves. The inventory is constant: White has two rooks and a king; Black has a king. The indexed material-only evaluator has no changing material signal on those lines; their search difference comes from terminal propagation and the quiescence boundary. This is a search-contract control, not evidence for any relative piece value. More roots with this same invariant-inventory structure would repeat the diagnostic without advancing the material-prior objective.

**Decision.** Keep this root as a bounded search-contract witness for mate-distance sensitivity, not as evidence of a material prior or a W/D/L improvement. A genuine material-prior decision-loss comparison needs material-changing legal alternatives and independently certified outcomes for compared actions. This witness does not select coefficients or a context distribution; Standard Shogi remains a control and Xiangqi stays sealed.
