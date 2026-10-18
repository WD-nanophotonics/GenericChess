"""Two-toggle branching fixture under the existing history budget."""
from pathlib import Path
import sys,json,time
sys.path.insert(0,str(Path.cwd()))
sys.path.insert(0,str(Path(__file__).resolve().parent))
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
import importlib.util
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cycle_producer',D/'cycle-producer.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
P=json.loads((D/'branch-plan.json').read_bytes());start=time.perf_counter()
k=PieceType('K','K',(),is_anchor=True);f=PieceType('F','F',(LeapAtom((0,1)),LeapAtom((0,-1))));g=PieceType('G','G',f.movement_atoms);z=PieceType('Z','Z',())
rows=[[None]*6 for _ in range(6)]
for x,y,o,t in [(0,0,0,'K'),(5,5,1,'K'),(0,1,0,'F'),(1,1,0,'F'),(4,4,1,'G'),(5,4,1,'G'),(0,3,0,'Z'),(1,3,0,'Z'),(1,0,0,'Z'),(4,2,1,'Z'),(5,2,1,'Z'),(4,5,1,'Z')]:rows[y][x]=Piece(o,t,t,False)
rs=RuleSet(schema_version=1,board_size=6,piece_types=(k,f,g,z),initial_position=tuple(map(tuple,rows)),drop_allowed={t:((False,)*36,)*2 for t in ('F','G','Z')},repetition_limit=3,max_ply=512,stalemate_result='draw')
c=compile_legacy_ruleset_for_semantic_execution(rs);s=GameSession(c);assert len(s.legal_actions())==2
cp=LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,board_weights={'K':0.,'F':2.,'G':1.,'Z':0.},hand_weights={'K':0.,'F':2.,'G':1.,'Z':0.})
nr=compile_native_semantic_rules(c);write_json(D/'branch-input.json',dict(rule=ruleset_to_dict(rs),checkpoint=cp.to_dict(),record=record_value(s.to_record()),state=record_value(s.state),parent_sha256=m.digest(s.state),scope='Twoindependent ordinary reversible toggles perplayer; no coordinate-free actions or modifiedhistory.'))
n=0;nodes=0;status='COMPLETE';error=None
try:
 with(D/'branch-queries.jsonl').open('x',encoding='utf8',newline='\n')as log:
  for mode in P['modes']:
   assert time.perf_counter()-start+P['prior_seconds']<120 and P['prior_queries']+n<32
   for name in ('rollout','advisor','slack'):
    v=json.loads((Path.cwd()/'.local_agent'/(name+'.json')).read_bytes());assert not(v.get('stopped')or v.get('user_paused'))
   before=(s.state,s.history,s.to_record(),s._search_witnesses);e=SemanticSearchEngine(c,nr,checkpoint=cp,tt_megabytes=0);tick=time.perf_counter();r=e.search(s,SearchLimits(max_depth=P['depth'],max_nodes=P['max_nodes'],max_time_seconds=P['max_time_seconds'],quiescence_max_depth=0),root_window_pruning=mode,trace_enabled=True)
   q=dict(mode=mode,parent_sha256=m.digest(s.state),parent_unchanged=before==(s.state,s.history,s.to_record(),s._search_witnesses),result=record_value(r),caller_seconds=time.perf_counter()-tick);log.write(json.dumps(q,separators=(',',':'))+'\n');log.flush();n+=1;nodes+=r.nodes;del e
   assert q['parent_unchanged']and r.completed_depth==P['depth']and not r.used_fallback
except BaseException as exc:status='ERROR';error=repr(exc)
write_json(D/'branch-result.json',dict(status=status,error=error,queries=n,nodes=nodes,seconds=time.perf_counter()-start,total_history_queries=18+n))
print(status,error,n,nodes,time.perf_counter()-start)
