"""Qualify all assessed price-active input trees against public full-history rules."""
from pathlib import Path
from fractions import Fraction
from copy import copy
import json,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from dataclasses import replace
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2155.sample import literal_tree,profile
from scripts.generic_royal_actor import RoyalActor
from results.dev_aux.task2100.campaign import evaluate
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2156')
def audit(cancel=None):
 start=time.perf_counter();deadline=start+180;root=Path('results/dev_aux/task2155');p=json.loads((root/'plan.json').read_text(encoding='utf-8'));inp=json.loads((root/'inputs.json').read_text(encoding='utf-8'));assessed=json.loads((root/'assessed.json').read_text(encoding='utf-8'));base=deserialize_ruleset(Path(p['base_rules']).read_text(encoding='utf-8'));actor=RoyalActor(3);ratios=list(map(Fraction,p['ratios']));nodes=terminals=0;selected={r['candidate']:r for r in inp['roots']};queries=[]
 stop=EvidenceStopReader(Path.cwd())if cancel is None else None
 def halted():
  if stop is not None:stop()
  return (cancel is not None and cancel())or time.perf_counter()>=deadline
 def build(s,depth):
  nonlocal nodes,terminals
  if halted():raise TimeoutError('original180cap')
  nodes+=1;raw=actor_state(s.state);legal={uci(a):a for a in s.legal_actions()};literal=dict(actor.moves(raw));assert set(legal)==set(literal)
  if s.result.status is not SessionStatus.ONGOING:
   terminals+=1;return dict(terminal='DRAW'if s.result.winner is None else'WIN'if s.result.winner==0 else'LOSS'),1
  if depth==0:
   coeff=[0,0]
   for x in s.state.position.board:
    if x is not None and x.current_type_id!='K':coeff[x.current_type_id=='N']+=1 if x.owner==0 else-1
   return dict(coeff=coeff),1
  edges=[];count=1
  for name,a in sorted(legal.items()):
   child=GameSession.replay(s.compiled,s.to_record());child.submit(a);assert actor_state(child.state)==literal[name];tree,n=build(child,depth-1);edges.append((name,tree));count+=n
  return dict(own=s.state.position.side_to_move==0,edges=edges),count
 for row in assessed:
  raw=row['root'];board=tuple(None if ch=='.'else Piece(int(ch.islower()),ch.upper(),ch.upper())for ch in raw[:-1]);rs=replace(base,initial_position=tuple(tuple(board[i:i+3])for i in range(0,9,3)),initial_setup_options=());c=compile_ruleset_for_execution(rs);s=GameSession(c);tree,count=build(s,2);lit,n=literal_tree(actor,tuple(raw),2)
  assert tree==lit and count==n==row['full_depth2_nodes'];assert profile(tree,ratios)==row['profiles'];assert row['accepted']==(len({r['first_action']for r in row['profiles']})>1 and n+1+len(tree['edges'])<=64)
  if row['candidate']in selected:
   r=selected[row['candidate']];assert r['fingerprint']==c.ruleset_fingerprint
   for price,expected in zip(ratios,row['profiles']):
    d=ProofMaterialPlayer(c,evaluate(float(price)),proof_enabled=False,max_depth=2).choose(s.state,max_nodes=64,seconds=1.,_clock=lambda:0.,cancel=halted)
    assert d.completed_depth==2 and d.nodes<=row['iterative_depth1plus2_node_upper']and uci(d.action)==expected['first_action']
    queries.append(dict(family=r['family'],ratio=str(price),choice=uci(d.action),nodes=d.nodes,depth=d.completed_depth,source=d.source))
 out=dict(status='PASS_ALL_ASSESSED_LITERAL_PUBLIC_TREES_AND_SELECTED_NODE_ONLY_NORMAL',assessed=len(assessed),selected=len(selected),all_public_nodes=nodes,actual_terminal_nodes=terminals,normal_queries=len(queries),new_fitness_games=0,seconds=time.perf_counter()-start,scope='All140assessedcandidates, acceptedandfailedpredicate, fullpubliclegal/terminal/materialtrees checked.336normalqueries useconstantinternalclock ONLYnode-algorithmqualification withseparateactual180wall/cancelguard; no timing/fitness/holdoutclaim. Initialside0predicate only, notlaterrole1priceactivity.')
 (OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');(OUT/'queries.json').write_text(json.dumps(queries,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':audit()
