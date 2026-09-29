# Shogi pawn-drop mate is a forbidden terminal threat

The [Japan Shogi Association match rules](https://www.shogi.or.jp/match/taikyoku_rules/)
Article 10 explicitly lists a pawn drop that delivers unanswerable
check (`打ち歩詰め`) as an immediate rule violation. The compiled Standard
Shogi `standard_drop_contract` records this as an action-delivers-check
and no-legal-reply postcondition. The coarse held-drop ledger excludes
that postcondition.

`scripts/audit_shogi_pawn_drop_mate_boundary.py` compares two small
diagnostic states with owner 0 holding one Pawn and an empty target at
index 67 (file 4, rank 7), immediately in front of the opponent King.
The only difference is whether an owner-0 Gold at (4,6) protects the
drop target. Reproduce with
`.venv/Scripts/python.exe scripts/audit_shogi_pawn_drop_mate_boundary.py`.

| Gold protects target | Coarse target | Public legal drop | Hypothetical opponent replies | Hypothetical terminal |
| --- | :---: | :---: | ---: | --- |
| no | yes | yes | 1 | ongoing |
| yes | yes | no | 0 | checkmate |

The hypothetical post-drop states are checked directly with executable
RuleSet semantics; the forbidden move is never submitted through the
public transition API. In the protected state the move would satisfy
the game's main mating goal, yet its pawn-drop form makes it illegal.
The paired state proves that neither coarse drop eligibility nor a
generic positive bonus for immediate goal proximity is sufficient:
the *kind of action* and rule-specific terminal exception matter.
This is a semantic boundary, not a material value or a frequency
estimate over real games.
