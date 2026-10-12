"""Rule-only coveredking compositionpilot; no reward/price filtering."""
import chess,random,json
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task155';O.mkdir(exist_ok=True)
def make(seed):
 rng=random.Random(seed)
 for attempt in range(1,1001):
  b=chess.Board(None)
  for square,piece in [('a1','K'),('a2','P'),('b2','P'),('h8','k'),('g7','p'),('h7','p')]:b.set_piece_at(chess.parse_square(square),chess.Piece.from_symbol(piece))
  for color in (True,False):
   for kind in (chess.PAWN,chess.PAWN,chess.KNIGHT,chess.BISHOP,chess.ROOK,chess.QUEEN):
    free=[s for s in chess.SQUARES if b.piece_at(s) is None and (kind!=chess.PAWN or chess.square_rank(s) not in (0,7))]
    b.set_piece_at(rng.choice(free),chess.Piece(kind,color))
  b.castling_rights=0;b.ep_square=None;b.halfmove_clock=0;b.fullmove_number=1
  valid=True
  for color in (True,False):
   b.turn=color
   if not b.is_valid() or b.is_check() or b.is_game_over(claim_draw=False):valid=False
  if valid:
   b.turn=True;white=b.fen();b.turn=False;return dict(seed=seed,attempts=attempt,white_fen=white,black_fen=b.fen())
 raise ValueError('fixedseedconstructionfailure; noresample')
if (O/'declaration.json').exists():raise FileExistsError('frozen')
roots=[make(2026102200+i) for i in range(8)]
profiles=json.loads((R/'results/dev_aux/task127/declaration.json').read_bytes())['profiles']
d=dict(task_id='155',question='Does fixedcheap2plyunit-opponent reduce reward/mate saturation and exposepairedleaf sensitivity?',roots=roots,profiles=profiles,opponents=['random','unit2ply'],agent_colors=[True,False],games=64,cap=16,random_seeds=[2026202200+i for i in range(8)],reward='UnchangedTask104: mate±100+speed, orunitcountdifference/15; componentsreported',royal_shields='Fixedtwo pawnshielda2/b2 andg7/h7, kingsa1/h8; samecounts P4 N1 B1 R1 Q1 onbothsides; randomremaining geometry; valid/nonterminal/notcheckedbothsidesonly; no engine/reward/humanprice filtering.',opponent='Randomsamefixedseed or exactcomplete2plyminimax standardChess unitPNBRQ208/K0, terminal±1000000/draw0, lexicalties; fullhistory/promotion/EP/checkevasionlegal. No secondengine, extraAgent orworker.',deadline_seconds=180,cost='64shortgames estimated<60s plusPythonlegal2ply opponentcost;180sfuse. Configurableagent1thread1024nodes16MiB c378mode3. Differentopponentworkcount isdeclaredtask-distribution intervention, notequalcostsearchstrengthcomparison.',scope='SyntheticinitialFEN/noncastling/EPfullsubsequenthistory; exposedfixed2profiles, nolearning/humanvalue recoveryclaim. Comparepairedtaskfeedback andterminal/cutoff separately.',decision='Non-saturatedmate/cutoffmix plus pairedprofiledifferences supportusefulfeedbackonly. Strongeropponent orchangedchoices alone donotproveidentifiablematerialvalues; retainzero/negativeprofiles andcomputationalcost.')
(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(json.dumps(dict(frozen=True,games=64,root_attempts=[r['attempts'] for r in roots])))
