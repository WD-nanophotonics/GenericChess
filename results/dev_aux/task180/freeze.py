"""Finite task/search terminal-goal mismatch witness, not a universal price impossibility."""
import json,hashlib,chess
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task180';O.mkdir(exist_ok=True)
if (O/'declaration.json').exists():raise FileExistsError('frozen')
b=chess.Board('k7/8/1QK5/8/8/8/5p2/8 w - - 0 1');assert b.is_valid() and not b.is_game_over(claim_draw=False) and not b.is_check()
for move,expected in [('b6b7','mate'),('b6f2','capture')]:
 c=b.copy(stack=True);c.push_uci(move)
 assert (c.is_checkmate() if expected=='mate' else (not c.is_game_over(claim_draw=False) and len(c.pieces(chess.PAWN,False))==0))
P=json.loads((R/'results/dev_aux/task166/declaration.json').read_bytes())
D=dict(task_id='180',question='Can unchanged mature mate priority disagree with finalquantity proxy even in a simple legal root?',roots=[dict(id='white',fen=b.fen(),agent_color=True),dict(id='black-mirror',fen=b.mirror().fen(),agent_color=False)],profiles=P['profiles'],searches=6,cap=16,node_limit=1024,deadline_seconds=90,binary_sha256=P['binary_sha256'],witness='WhiteQb6/Kc6, BlackKa8/Pf2: Qb7 mate leavescountdifference0; Qxf2 islegal/nonterminal leavesdifference1. Colorsmirrored. Nohumanprices or engine-outputfixture selection.',oracle='Completelegal2ply with finalunitquantity terminalincluded, no matebonus; actualterminal stops tree. All-bestmoves kept, fulllegalchild/reply counts.',decision='If actualmature choosesmate outsideunitquantityargmax, it proves thisfinite task/search goalmismatch, notsourcebug/pricelearningfailurecausality orunitquantitygeneral impossibility. If not, retainfailure.',cost='6boundedactualrootqueries pluscompletelegal2plyoracle, estimated<2s/90sfuse; serialafterotherownedengine. Notgame-strength/wholelearning.',scope='SyntheticStandardChess/noncastlinginitialhistoryempty, allroyal/terminal legality preserved; unchangedbinary mode3 materialpricing. Newgoalonlyobjectiveanalysis; noenginecode modification.')
(O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8');print(json.dumps(dict(frozen=True,searches=6)))
