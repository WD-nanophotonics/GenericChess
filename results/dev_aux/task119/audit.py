"""Equal material, different exact short mate return; diagnostic only."""
import hashlib,json,time
from fractions import Fraction
from pathlib import Path
import chess
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent
cfg=json.loads((OUT/'declaration.json').read_bytes());start=time.perf_counter();counts={'nodes':0,'terminal':0,'nonterminal_cutoff':0}
TYPES=[chess.PAWN,chess.KNIGHT,chess.BISHOP,chess.ROOK,chess.QUEEN]
def guard():
 if time.perf_counter()-start>=120:raise TimeoutError('120s finite tree cap')
 for root in [ROOT,ROOT.parent/'GenericChess 2']:
  for name,key in [('rollout.json','user_paused'),('slack.json','stopped')]:
   if json.loads((root/'.local_agent'/name).read_bytes()).get(key):raise RuntimeError('persistent stop')
def encode(v):return {'numerator':v.numerator,'denominator':v.denominator}
def feature(b,agent):return [len(b.pieces(t,agent))-len(b.pieces(t,not agent)) for t in TYPES]
def value(b,left,agent):
 counts['nodes']+=1
 if counts['nodes']%128==0:guard()
 outcome=b.outcome(claim_draw=False)
 if outcome is not None:
  counts['terminal']+=1
  return Fraction(0 if outcome.winner is None else (1 if outcome.winner==agent else -1)*(100+left))
 if left==0:counts['nonterminal_cutoff']+=1;return Fraction(0)
 values=[]
 for move in sorted(b.legal_moves,key=lambda m:m.uci()):
  child=b.copy(stack=True);child.push(move);values.append(value(child,left-1,agent))
 return max(values) if b.turn==agent else sum(values,Fraction(0))/len(values)
rows=[]
for fen in cfg['roots']:
 for mirror in [False,True]:
  guard();b=chess.Board(fen)
  if mirror:b=b.mirror()
  assert b.is_valid() and not b.is_game_over(claim_draw=False)
  agent=b.turn;actions=[]
  for move in sorted(b.legal_moves,key=lambda m:m.uci()):
   child=b.copy(stack=True);child.push(move);v=value(child,2,agent)
   actions.append({'uci':move.uci(),'value':encode(v)})
  values=[Fraction(a['value']['numerator'],a['value']['denominator']) for a in actions];best=max(values)
  rows.append({'fen':b.fen(),'source_fen':fen,'mirror':mirror,'material_features':feature(b,agent),'exact_expected_mate_return':encode(best),'selected_lexical_action':next(a['uci'] for a,v in zip(actions,values) if v==best),'actions':actions})
assert all(r['material_features']==[0,0,0,0,1] for r in rows)
assert rows[0]['exact_expected_mate_return']==rows[1]['exact_expected_mate_return']==encode(Fraction(102))
assert rows[2]['exact_expected_mate_return']==rows[3]['exact_expected_mate_return']==encode(Fraction(0))
result={'complete':True,'backend':'FINITE_PYTHON_CHESS_EXACT_RANDOM_OPPONENT_NOT_MATURE','declaration_sha256':hashlib.sha256((OUT/'declaration.json').read_bytes()).hexdigest(),'rows':rows,'counts':counts,'wall_seconds':time.perf_counter()-start,'mature_games_executed':0,'learned_updates':0,'finding':'Equal P/N/B/R/Q counts cannot exactly represent both102 and0 conditional3ply mate returns; geometry matters even with a fixed finite policy/opponent.','limits':['This is exact finite expectation, not single-rollout noise or a mature-engine measurement.','A material-leaf searcher still receives the full board/legal tree and terminal authority; this does not refute its ability to act correctly using material leaves.','Count-only averaged return estimates under an explicit distribution remain valid approximations; this witness refutes exact statewise representation only.','No human prices, parameter fitting, new random-game cohort or holdout claim.']}
(OUT/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps({k:result[k] for k in ['counts','wall_seconds','finding','mature_games_executed']}))