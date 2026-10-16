from pathlib import Path
from dataclasses import replace
from copy import copy
import json,sys,time
sys.path.insert(0,str(Path('tests').resolve()))
from rule_semantics_ir_fixtures import weird_rulesets
from generic_chess.core.pieces import Piece
from generic_chess.core.actions import action_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_win_proof import _same_state,_ordered
from results.dev_aux.task2199.semantic_graph import canonical
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2206')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('single30cap neverrestart')
 began=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(cap=30)),encoding='utf-8');rs=weird_rulesets()[2];board=[list(row)for row in rs.initial_position];board[1][0]=Piece(0,'R','R');board[2][2]=Piece(1,'R','R');rs=replace(rs,initial_position=tuple(map(tuple,board)),drop_allowed={**rs.drop_allowed,'R':((True,)*64,)*2});c=compile_ruleset_for_execution(rs);s=GameSession(c);rows=[];edges=0
 for step in range(4):
  stop();assert time.perf_counter()-began<30;canon=canonical(s.state.position,c);assert _same_state(canon.state.position,s.state.position)and canon.legal_actions()==s.legal_actions()
  for a in s.legal_actions():
   stop();assert time.perf_counter()-began<30;after=copy(s);after.submit(a);other=copy(canon);other.submit(a);assert _same_state(after.state.position,other.state.position)and after.result==other.result;assert _same_state(GameSession.replay(c,after.to_record()).state,after.state);edges+=1
  if step==1:assert(s.state.position.board[17].base_type_id,s.state.position.board[17].current_type_id,s.state.position.board[17].promoted)==('R','TP',True)
  if step>=2:assert s.state.position.hands[1].count('R')==1 and s.state.position.hands[1].count('TP')==0
  drops=[a for a in s.legal_actions()if hasattr(a,'base_type_id')]
  if step==3:assert drops and all(a.base_type_id=='R'for a in drops)
  rows.append(dict(step=step,record=json.loads(serialize_game_record(s.to_record())),state_repr=repr(s.state),legal_actions=[action_to_dict(a)for a in s.legal_actions()],drops=[action_to_dict(a)for a in drops]))
  if step==3:break
  if step==0:a=next(a for a in s.legal_actions()if a.pattern_id.startswith('sem_')and(a.to_square.file,a.to_square.rank)==(1,2))
  elif step==1:a=next(a for a in s.legal_actions()if hasattr(a,'from_square')and(a.from_square.file,a.from_square.rank)==(2,2)and(a.to_square.file,a.to_square.rank)==(1,2))
  else:a=next(a for a in _ordered(s.legal_actions())if a.actor_type_id=='K')
  s.submit(a)
 (OUT/'rules.json').write_text(serialize_ruleset(rs),encoding='utf-8');result=dict(status='PASS_SEMANTIC_TRANSFORMED_CAPTURE_BASE_DROP',rows=rows,all_public_edges=edges,seconds=time.perf_counter()-began,new_proof_or_fit_or_statistical_games=0,scope='Actualsemantic-only R->TP baseidentity survives capture/drops; allfullpositions/results and recordreplays agree withCorecanonical. No P/R price orWDLclaim.');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:result[k]for k in('status','all_public_edges','seconds')}))
if __name__=='__main__':run()
