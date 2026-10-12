"""Rule-valid syntheticcomposition roots frozen without engine/reward/price filtering."""
import chess,random,json,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task135';O.mkdir(exist_ok=True)
def make(seed,index):
 rng=random.Random(seed);tries=0
 while True:
  tries+=1
  if tries>1000:raise RuntimeError('construction failure, do not change fixedseed')
  b=chess.Board(None);b.set_piece_at(chess.A1,chess.Piece(chess.KING,True));b.set_piece_at(chess.H8,chess.Piece(chess.KING,False))
  multiplicity=1+index%2
  for color in (True,False):
   pieces=[chess.PAWN]*(2+multiplicity)+[t for t in (chess.KNIGHT,chess.BISHOP,chess.ROOK,chess.QUEEN) for _ in range(multiplicity)]
   for t in pieces:
    free=[s for s in chess.SQUARES if b.piece_at(s) is None and (t!=chess.PAWN or chess.square_rank(s) not in (0,7))]
    sq=rng.choice(free);b.set_piece_at(sq,chess.Piece(t,color))
  b.castling_rights=0;b.ep_square=None;b.halfmove_clock=0;b.fullmove_number=1
  acceptable=True
  for color in (True,False):
   b.turn=color
   if not b.is_valid() or b.is_check() or b.is_game_over(claim_draw=False):acceptable=False
  if acceptable:break
 return dict(seed=seed,index=index,tries=tries,white_fen=chess.Board(b.fen().replace(' b ',' w ')).fen(),black_fen=b.fen(),multiplicity=multiplicity,counts={chess.piece_symbol(t).upper():len(b.pieces(t,True)) for t in range(1,6)})
def freeze():
 if (O/'declaration.json').exists():raise FileExistsError('frozen')
 train=[make(2026101200+i,i) for i in range(8)]
 heldout=[make(2026101300+i,i) for i in range(4)]
 data=dict(task_id='135',question='Does predeclared balanced mixedmaterial composition supply diverse cheap exchange signal absent earlyinitial openings?',train=train,heldout=heldout,construction='fixedkingsa1/h8; samecounts/colors; randomdistinctsquares; no pawnsedge; accept valid/nonterminal/bothkingsnotchecked; never filter byreward orhumanprices',semantics='StandardChess syntheticinitialFEN, no prehistory/castling/ep. Fullsubsequenthistory retained. Scopedcompositiondistribution, not orthodoxstart selfplay.',profiles=dict(unit=dict(P=208,K=0,N=208,B=208,R=208,Q=208),learned=dict(P=208,K=0,N=232,B=328,R=396,Q=510)),pilot='first4trainingboards bothturns,2profiles,16ply sameoriginalTask104reward;32games. QualifyFENleaf andmovehistory. Independentheldoutboards reservedunplayed.',training_permission='Only if actualpilot rewards distinguishprofiles and currentroot featurevariation has rank4 afterPfixed, choose a bounded declaredlearning run; no automaticextension',cost='32games预计<15seconds,120sfuse; source/engineeringcostseparate',human_reference=dict(P=1,N=3,B=3,R=5,Q=9),human_reference_use='Samealreadyexposed descriptive reference; nohumanfit/selection/construction; originalsourceChess.com piecevalue fixedprevioussegment',human_reference_source='https://www.chess.com/terms/chess-piece-value')
 (O/'declaration.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
 print(json.dumps(dict(train=len(train),heldout=len(heldout),tries=[x['tries'] for x in train+heldout],counts=[x['counts'] for x in train])))
if __name__=='__main__':freeze()
