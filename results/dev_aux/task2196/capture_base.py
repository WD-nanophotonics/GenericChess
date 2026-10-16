from pathlib import Path
from dataclasses import replace
from copy import copy
import json,sys,time,hashlib
sys.path.insert(0,str(Path('tests').resolve()))
from conftest import T,king_type,make_ruleset
from generic_chess.core.pieces import Piece
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.core.actions import DropMove,action_to_dict
from generic_chess.rules.schema import RuleInitialSetupOption
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2179.graph import prove_graph,verify_graph,GraphStrategyCursor,position_token
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2196')

def run():
 if(OUT/'started.json').exists():raise RuntimeError('single30cap neverrestart')
 began=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap=30)),encoding='utf-8')
 rook=T('R',*(RayAtom(d)for d in((1,0),(-1,0),(0,1),(0,-1))));pawn=T('P',LeapAtom((0,1)),is_promotable=True,targets=('R',))
 boards=[]
 for base,promoted in(('R',False),('P',True)):
  b=[None]*16
  for i,p in((1,Piece(0,'K','K')),(3,Piece(1,'K','K')),(4,Piece(0,'R','R')),(8,Piece(1,base,'R',promoted)),(14,Piece(1,'P'if base=='R'else'R','R',not promoted))):b[i]=p
  boards.append(tuple(tuple(b[i:i+4])for i in range(0,16,4)))
 rs=make_ruleset(4,[king_type(),rook,pawn],lines=['....']*4);rs=replace(rs,initial_position=boards[0],initial_setup_options=(RuleInitialSetupOption('swapped_bases',boards[1]),),drop_allowed={tid:((True,)*16,)*2 for tid in('R','P')},capture_disposition='capture_to_hand')
 c=compile_ruleset_for_execution(rs);sessions=[GameSession(c),GameSession(c,initial_setup_key='swapped_bases')];assert actor_state(sessions[0].state)==actor_state(sessions[1].state)and position_token(sessions[0].state.position)!=position_token(sessions[1].state.position)
 (OUT/'rules.json').write_text(serialize_ruleset(rs),encoding='utf-8');roots=[]
 for s in sessions:
  roots.append(dict(record=json.loads(serialize_game_record(s.to_record())),state_repr=repr(s.state)))
  for move in('a2a3','d1d2'):
   stop();assert time.perf_counter()-began<30;s.submit(next(a for a in s.legal_actions()if not isinstance(a,DropMove)and uci(a)==move))
  assert _same_state(GameSession.replay(c,s.to_record()).state,s.state)
 rsession,psession=sessions
 assert rsession.state.position.hands[0].count('R')==1 and psession.state.position.hands[0].count('P')==1
 assert actor_state(rsession.state)==actor_state(psession.state)
 drops=[[action_to_dict(a)for a in s.legal_actions()if isinstance(a,DropMove)]for s in sessions]
 def cancel():stop();return time.perf_counter()-began>=30
 proof=prove_graph(rsession,max_nodes=512,seconds=2.,max_depth=4,cancel=cancel);assert proof.certificate is not None
 v=verify_graph(rsession,proof.certificate,seconds=2.,cancel=cancel);assert v['verified'];cur=GraphStrategyCursor(rsession,proof.certificate,seconds=2.,cancel=cancel);choice=cur.choose(rsession);assert isinstance(choice.action,DropMove)and choice.action.base_type_id=='R'
 actual=copy(rsession);cur.commit(actual,choice);assert actual.result.winner==0
 # Root-binding is deliberately rebound only to test independent legality.
 forged=replace(proof.certificate,root_state=psession.state,root_record=psession.to_record())
 bad=verify_graph(psession,forged,seconds=2.,cancel=cancel);assert not bad['verified']
 result=dict(status='PASS_SAME_CURRENT_DIFFERENT_BASE_REAL_CAPTURE_DROP',ruleset_fingerprint=c.ruleset_fingerprint,roots=roots,after=[dict(record=json.loads(serialize_game_record(s.to_record())),state_repr=repr(s.state),drops=d)for s,d in zip(sessions,drops)],proof_verification=v,R_drop_actual_winner=actual.result.winner,P_rebound_rejection=bad,scope='Same fingerprint/currentmovement board beforecapture; fullbase/promoted keys distinguish. Aftercapture samecurrentboard has differenthands/drop legality. P context notprovenloss; no price/qualityclaim.',seconds=time.perf_counter()-began)
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:result[k]for k in('status','P_rebound_rejection','seconds')}))
if __name__=='__main__':run()
