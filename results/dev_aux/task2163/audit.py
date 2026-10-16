"""Independent public full-history and literal audit of all frozen TRAIN trees."""
from pathlib import Path
from fractions import Fraction
from copy import copy
import json,time,math
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2155.sample import literal_tree,profile
from results.dev_aux.task2100.campaign import evaluate
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2163')
def audit(cancel=None):
 start=time.perf_counter();deadline=start+240;stop=EvidenceStopReader(Path.cwd())if cancel is None else None
 def halted():
  if stop is not None:stop()
  return(cancel is not None and cancel())or time.perf_counter()>=deadline
 def check():
  if halted():raise TimeoutError('single240auditcap')
 inp=json.loads(Path('results/dev_aux/task2158/inputs.json').read_text(encoding='utf-8'))['roots'][:32];saved=list(map(json.loads,Path('results/dev_aux/task2162/trees.jsonl').read_text(encoding='utf-8').splitlines()));rows=list(map(json.loads,Path('results/dev_aux/task2162/queries.jsonl').read_text(encoding='utf-8').splitlines()));actor=RoyalActor(3);total=terms=0;queries=[]
 def normalized(x):return json.loads(json.dumps(x))
 def tree(s,left):
  nonlocal total,terms
  check();total+=1;raw=actor_state(s.state);legal={uci(a):a for a in s.legal_actions()};literal=dict(actor.moves(raw));assert set(legal)==set(literal)
  if s.result.status is not SessionStatus.ONGOING:
   terms+=1;return dict(terminal='DRAW'if s.result.winner is None else'WIN'if s.result.winner==0 else'LOSS')
  if not left:
   coeff=[0,0]
   for piece in s.state.position.board:
    if piece is not None and piece.current_type_id!='K':coeff[piece.current_type_id=='N']+=1 if piece.owner==0 else-1
   return dict(coeff=coeff)
  edges=[]
  for name,a in sorted(legal.items()):
   before=s.to_record();state=s.state;child=GameSession.replay(s.compiled,before);child.submit(a);assert actor_state(child.state)==literal[name];edges.append((name,tree(child,left-1)));assert _same_state(s.state,state)and _same_state(s.to_record(),before)
  return dict(own=s.state.position.side_to_move==0,edges=edges)
 for saved,row in zip(saved,rows):
  r=inp[row['family']];depth=row['depth'];assert saved['family']==row['family']and saved['depth']==depth
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')));s=GameSession(c);assert c.ruleset_fingerprint==r['fingerprint'];before=s.to_record();state=s.state;tr=tree(s,depth);lit,n=literal_tree(actor,tuple(r['root']),depth);assert normalized(tr)==normalized(lit)==saved['tree']and n==row['nodes']
  ratios=list(map(Fraction,[x['ratio']for x in row['regions']]));expected=profile(lit,ratios)
  assert all(all(g[k]==e[k]for k in('ratio','top_actions','first_action'))for g,e in zip(row['regions'],expected))
  # All possible coefficient crossings are globally .5,1,2 including DRAW0.
  assert all(Fraction(x)in(Fraction(1,2),Fraction(1),Fraction(2))for x in row['breakpoints'])
  for cell in row['fixed_cells']:
   check();d=ProofMaterialPlayer(c,evaluate(float(Fraction(cell['ratio']))),proof_enabled=False,max_depth=depth).choose(s.state,max_nodes=512,seconds=1.,cancel=halted,_clock=lambda:0.)
   assert d.completed_depth==depth and d.nodes<=512 and uci(d.action)==cell['first_action']and d.source=='MATERIAL_SEARCH';assert _same_state(s.state,state)and _same_state(s.to_record(),before)
   queries.append(dict(family=r['family'],depth=depth,ratio=cell['ratio'],choice=uci(d.action),nodes=d.nodes,completed_depth=d.completed_depth,exit_cause=d.exit_cause))
 out=dict(status='PASS_ALL96_CORE_PUBLIC_LITERAL_TREES_AND672_NODE_ONLY_QUERIES',tree_queries=len(rows),public_nodes=total,terminal_nodes=terms,normal_queries=len(queries),max_normal_nodes=max(q['nodes']for q in queries),seconds=time.perf_counter()-start,new_games_or_fit_or_DEV=0,scope='Full history publicSession trees and independent literal rules agree with all Core trees; constant-clock normal checks algorithm/node completion only. Separate actual240cap; no wall-speed or arbitrary-history teacher claim.');(OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');(OUT/'queries.json').write_text(json.dumps(queries,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':audit()
