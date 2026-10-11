"""Exact tiny fast-mate expectimax/leaf-feature audit, not mature search or training."""
import hashlib,json,time
from fractions import Fraction
from pathlib import Path
import chess
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent
cfg=json.loads((OUT/'declaration.json').read_bytes());start=time.perf_counter();deadline=start+cfg['fuse_seconds']
counts={'nodes':0,'nonterminal_leaves':0,'terminal_leaves':0};rows=[];types_seen=set()
def guard():
 if time.perf_counter()>=deadline:raise TimeoutError('120s finite audit fuse')
 for r in [ROOT,ROOT.parent/'GenericChess 2']:
  for name,key in [('rollout.json','user_paused'),('slack.json','stopped')]:
   if json.loads((r/'.local_agent'/name).read_bytes()).get(key):raise RuntimeError('persistent user stop')
def val(b,left,agent,weights):
 counts['nodes']+=1
 if counts['nodes']%128==0:guard()
 types_seen.update(p.symbol().upper() for p in b.piece_map().values())
 outcome=b.outcome(claim_draw=False)
 if outcome is not None:
  counts['terminal_leaves']+=1
  return Fraction(0 if outcome.winner is None else (1 if outcome.winner==agent else -1)*(cfg['terminal_value']+left))
 if left==0:
  counts['nonterminal_leaves']+=1
  return Fraction(sum((1 if p.color==agent else -1)*weights[p.symbol().upper()] for p in b.piece_map().values()))
 values=[]
 for m in sorted(b.legal_moves,key=lambda x:x.uci()):
  child=b.copy(stack=True);child.push(m);values.append(val(child,left-1,agent,weights))
 return max(values) if b.turn==agent else sum(values,Fraction(0))/len(values)
def encode(v):return {'numerator':v.numerator,'denominator':v.denominator}
for fen in cfg['roots']:
 for mirror in [False,True]:
  guard();b=chess.Board(fen)
  if mirror:b=b.mirror()
  assert b.is_valid() and not b.is_game_over(claim_draw=False)
  agent=b.turn;profile_rows=[]
  for i,weights in enumerate(cfg['profiles']):
   actions=[]
   for m in sorted(b.legal_moves,key=lambda x:x.uci()):
    child=b.copy(stack=True);child.push(m)
    v=val(child,cfg['horizon_plies']-1,agent,weights)
    actions.append({'uci':m.uci(),'expectation':encode(v),'child_checkmate':child.is_checkmate(),'child_termination':None if child.outcome(claim_draw=False) is None else child.outcome(claim_draw=False).termination.name})
   values=[Fraction(a['expectation']['numerator'],a['expectation']['denominator']) for a in actions];best=max(values)
   chosen=next(a for a,v in zip(actions,values) if v==best)
   assert chosen['child_checkmate']
   profile_rows.append({'profile':i,'chosen_action':chosen['uci'],'best_expectation':encode(best),'actions':actions})
  assert len({p['chosen_action'] for p in profile_rows})==1
  rows.append({'source_fen':fen,'mirror':mirror,'fen':b.fen(),'agent_color':agent,'profiles':profile_rows})
assert types_seen=={'K','Q','R'}
result={'complete':True,'backend':'FINITE_PYTHON_CHESS_EXPECTIMAX_NOT_MATURE','python_chess_version':chess.__version__,'declaration_sha256':hashlib.sha256((OUT/'declaration.json').read_bytes()).hexdigest(),'horizon_plies':3,'rows':rows,'counts':counts,'types_seen':sorted(types_seen),'absent_material_features':['P','N','B'],'wall_seconds':time.perf_counter()-start,'mature_games_executed':0,'learned_updates':0,'finding':'All three synthetic price profiles choose the same immediate mate on four scoped roots. P/N/B features are absent at every visited position; these tasks cannot identify their relative prices through this material evaluator.','limits':['Finite exact random-opponent tree is a diagnostic oracle, not a replacement for the intended mature-engine experiment.','Selective mature search may react to numerical leaf scales through pruning/order/caches; that is conditional search behavior, not proof these rewards uniquely identify values.','This does not refute fast-mate objectives on full-army positions or broader distributions involving all types and exchanges.','Roots are declared constructed witnesses, not random games, independent human holdout or estimates of prevalence.']}
(OUT/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps({k:result[k] for k in ['counts','types_seen','wall_seconds','mature_games_executed','finding']}))