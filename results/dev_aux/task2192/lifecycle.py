"""Actual existing lifecycle route; full frontier and history replay controls."""
from pathlib import Path
from dataclasses import replace
from copy import copy
import json,hashlib,time,sys
sys.path.insert(0,str(Path('tests').resolve()))
from rule_semantics_ir_fixtures import weird_rulesets
from generic_chess.core.pieces import Piece
from generic_chess.core.actions import action_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2191.semantic_graph import canonical,scope_reason
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2192')

def fixture():
 fixtures=weird_rulesets();guard=fixtures[1].semantic_actions[0];promotion=fixtures[2].semantic_actions[0];board=[[None]*8 for _ in range(8)]
 for owner,tid,file,rank in((0,'K',4,0),(1,'K',7,7),(0,'R',0,0),(0,'R',0,1),(0,'R',0,2),(0,'R',1,1),(1,'R',1,3),(1,'R',1,4)):board[rank][file]=Piece(owner,tid,tid)
 definition=replace(fixtures[2],initial_position=tuple(map(tuple,board)),semantic_actions=(guard,promotion),drop_allowed={'R':((True,)*64,(True,)*64),'TP':((False,)*64,(False,)*64)})
 route=(((1,1),(1,3),False),((7,7),(6,7),False),((1,3),(1,4),False),((6,7),(5,7),False),((0,0),(1,1),True),((5,7),(4,7),False),(None,(0,0),False),((4,7),(3,7),False))
 return definition,route

def run():
 if(OUT/'started.json').exists():raise RuntimeError('single180cap neverrestart')
 p=json.loads((OUT/'plan.json').read_text());
 for name,h in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
 began=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap=180)),encoding='utf-8')
 definition,route=fixture();s=GameSession(compile_ruleset_for_execution(definition));assert scope_reason(s.compiled)is None
 (OUT/'rules.json').write_text(serialize_ruleset(definition),encoding='utf-8');rows=[];edges=[]
 for ply in range(9):
  stop();assert time.perf_counter()-began<180
  c=canonical(s.state.position,s.compiled);assert _same_state(c.state.position,s.state.position)and c.result==s.result
  actual=s.legal_actions();assert _same_state(c.legal_actions(),actual)
  drops=[a for a in actual if hasattr(a,'base_type_id')]
  if ply in(2,4,8):assert s.state.position.hands[0].count('R')>0 and not drops
  if ply==5:assert (s.state.position.board[9].base_type_id,s.state.position.board[9].current_type_id,s.state.position.board[9].promoted)==('R','TP',True)and dict(s.state.position.aux_state)[(0,-1)]==1
  if ply==6:assert dict(s.state.position.aux_state)[(0,-1)]==0 and len(drops)==58
  for a in actual:
   stop();assert len(edges)<p['max_prefix_edges']and time.perf_counter()-began<180
   child=copy(s);child.submit(a);forward=copy(c);forward.submit(a)
   assert _same_state(child.state.position,forward.state.position)and child.result==forward.result
   replay=GameSession.replay(s.compiled,child.to_record());assert _same_state(child.state,replay.state)and child.result==replay.result
   edges.append(dict(parent_ply=ply,action=action_to_dict(a),position_repr=repr(child.state.position),record=json.loads(serialize_game_record(child.to_record())),state_sha=hashlib.sha256(repr(child.state).encode()).hexdigest(),result=repr(child.result)))
  rows.append(dict(ply=ply,record=json.loads(serialize_game_record(s.to_record())),state_repr=repr(s.state),legal_actions=[action_to_dict(a)for a in actual],canonical_state_repr=repr(c.state),drop_count=len(drops)))
  if ply==8:break
  source,target,semantic=route[ply];candidates=[]
  for a in actual:
   if(a.to_square.file,a.to_square.rank)!=target:continue
   if source is None:
    if hasattr(a,'base_type_id'):candidates.append(a)
   elif hasattr(a,'from_square')and(a.from_square.file,a.from_square.rank)==source and a.pattern_id.startswith('sem_')==semantic:candidates.append(a)
  a,=candidates;s.submit(a)
 (OUT/'prefixes.json').write_text(json.dumps(rows),encoding='utf-8');(OUT/'edges.json').write_text(json.dumps(edges),encoding='utf-8')
 result=dict(status='PASS_NINE_ACTUAL_LIFECYCLE_PREFIXES_FULL_FRONTIERS',prefixes=len(rows),edges=len(edges),seconds=time.perf_counter()-began,new_proof_queries=0,scope='Actual public capture/hand/transformation/aux-expiry/guarded-drop route; all child fullpositions+results agree and fullrecords replay. Not arbitrary generated-domain proof or WDL/price result.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
