"""Reachable deterministic repetition fixture; no generated games or learning."""
from pathlib import Path
import sys,json,time,hashlib
sys.path.insert(0,str(Path.cwd()))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import RuleSet,ruleset_to_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.ai.limits import SearchLimits
D=Path(__file__).resolve().parent
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def fixture():
 k=PieceType("K","K",(),is_anchor=True)
 f=PieceType("F","F",(LeapAtom((0,1)),LeapAtom((0,-1))))
 g=PieceType("G","G",(LeapAtom((0,1)),LeapAtom((0,-1))))
 z=PieceType("Z","Z",())
 rows=[[None]*4 for _ in range(4)]
 for x,y,p in [(0,0,Piece(0,"K","K",False)),(3,3,Piece(1,"K","K",False)),(0,3,Piece(0,"Z","Z",False)),(3,0,Piece(1,"Z","Z",False)),(0,1,Piece(0,"F","F",False)),(3,2,Piece(1,"G","G",False))]:rows[y][x]=p
 return RuleSet(schema_version=1,board_size=4,piece_types=(k,f,g,z),initial_position=tuple(map(tuple,rows)),drop_allowed={t:((False,)*16,)*2 for t in ("F","G","Z")},promotion_allowed={},promotion_forced={},repetition_limit=4,max_ply=512,stalemate_result="draw")
def run():
 start=time.perf_counter();n=0;nodes=0;error=None;status="COMPLETE";rs=fixture();c=compile_legacy_ruleset_for_semantic_execution(rs)
 cp=LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,board_weights={"K":0.,"F":2.,"G":1.,"Z":0.},hand_weights={"K":0.,"F":2.,"G":1.,"Z":0.})
 s=GameSession(c);parents=[]
 for ply in range(12):
  if ply in (3,7,11):parents.append(dict(ply=ply,record=record_value(s.to_record()),state=record_value(s.state),state_sha256=digest(s.state),history=record_value(s.history),witness_sha256=digest(s._search_witnesses)))
  aa=s.legal_actions();assert len(aa)==1
  s.submit(aa[0])
 write_json(D/'cycle-inputs.json',dict(rule=ruleset_to_dict(rs),checkpoint=cp.to_dict(),parents=parents,last_state=record_value(s.state),source="Existing test_native_history.py deterministic cycle, unchanged complete RuleSet, real Session submissions."))
 nr=compile_native_semantic_rules(c)
 assert not(D/'cycle-queries.jsonl').exists()
 try:
  with(D/'cycle-queries.jsonl').open('x',encoding='utf8',newline='\n')as log:
   for p in parents:
    session=GameSession(c)
    for _ in range(p['ply']):session.submit(session.legal_actions()[0])
    for dep in (1,2,4):
     for mode in (False,True):
      assert n<32 and time.perf_counter()-start<120
      for name in ('rollout','advisor','slack'):
       flags=json.loads((Path.cwd()/'.local_agent'/(name+'.json')).read_bytes());assert not(flags.get('stopped')or flags.get('user_paused'))
      before=(session.state,session.to_record(),session.history,session._search_witnesses)
      engine=SemanticSearchEngine(c,nr,checkpoint=cp,tt_megabytes=0);tick=time.perf_counter()
      result=engine.search(session,SearchLimits(max_depth=dep,max_nodes=8192,max_time_seconds=2.,quiescence_max_depth=0),root_window_pruning=mode,trace_enabled=True)
      row=dict(parent_ply=p['ply'],requested_depth=dep,mode=mode,record=p['record'],parent_sha256=digest(session.state),parent_witness_sha256=digest(session._search_witnesses),parent_unchanged=before==(session.state,session.to_record(),session.history,session._search_witnesses),result=record_value(result),caller_seconds=time.perf_counter()-tick)
      log.write(json.dumps(row,separators=(',',':'))+'\n');log.flush();n+=1;nodes+=result.nodes;del engine
      assert row['parent_unchanged']and result.completed_depth==dep and not result.used_fallback
      assert log.tell()<64*1024*1024
 except BaseException as e:status="ERROR";error=repr(e)
 write_json(D/'cycle-result.json',dict(status=status,error=error,queries=n,nodes=nodes,seconds=time.perf_counter()-start,limit_queries=32,remaining_queries=32-n,all_parents_unchanged=True if status=="COMPLETE"else None))
 print(status,error,n,nodes,time.perf_counter()-start)
if __name__=="__main__":run()
