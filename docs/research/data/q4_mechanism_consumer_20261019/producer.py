"""Next-step concrete q4 semantic consumer probe, one continuous bounded run."""
from pathlib import Path
from dataclasses import replace
import sys,json,time,hashlib
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from rule_semantics_ir_fixtures import castling_ruleset,weird_rulesets
from generic_chess.core.pieces import Piece
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from generic_chess.native.compiler import compile_native_semantic_rules,NativeUnsupportedRuleError
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
D=Path(__file__).resolve().parent;start=time.monotonic();P=json.loads((D/'plan.json').read_bytes());counts=dict(Native_queries=0,Native_main=0,Native_q=0,Core_calls=0,Core_main=0,Core_q=0);status='COMPLETE';error=None;parents=[];cases={};native={};comparisons=[]
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def stopped():
 for n in ('rollout','advisor','slack'):
  f=json.loads((Path.cwd()/'.local_agent'/(n+'.json')).read_bytes())
  if f.get('stopped')or f.get('user_paused'):return True
 return False
def poll():assert not stopped()and time.monotonic()-start<360
class Stop:
 def __init__(self):self.next=0;self.value=False
 def is_cancelled(self):
  if time.monotonic()>=self.next:self.next=time.monotonic()+.1;self.value=stopped()
  return self.value or time.monotonic()-start>=360
class Material:
 def __init__(self,b,h):self.b=b;self.h=h
 def evaluate(self,s):
  v=sum((1 if p.owner==0 else -1)*self.b[p.current_type_id]for p in s.position.board if p)+sum((s.position.hands[0].count(t)-s.position.hands[1].count(t))*v for t,v in self.h.items());assert abs(v)<10000000;return v*(1 if s.position.side_to_move==0 else -1)
rs=weird_rulesets()
temporary=rs[2];rows=[list(r)for r in temporary.initial_position];rows[1][0]=Piece(0,'R','R');temporary=replace(temporary,initial_position=tuple(map(tuple,rows)))
compound=rs[3];rows=[list(r)for r in compound.initial_position];rows[1][1]=Piece(0,'R','R');rows[2][1]=Piece(0,'R','R');compound=replace(compound,initial_position=tuple(map(tuple,rows)))
definitions=[('persistent',castling_ruleset(),(4,0,6,0)),('temporary',temporary,(0,1,1,2)),('compound',compound,(1,1,2,2))]
try:
 for label,rule,coords in definitions:
  poll();c=compile_semantic_ruleset(rule);s=GameSession(c);types={t.type_id:t for t in rule.piece_types};b={t:0 if types[t].is_anchor else 100+100*i for i,t in enumerate(sorted(types))};h={t:int(v*.8)for t,v in b.items()};case=dict(name=label,rule=ruleset_to_dict(rule),board_values=b,hand_values=h)
  try:native[label]=compile_native_semantic_rules(c);case['Native_admission']='SUPPORTED'
  except NativeUnsupportedRuleError as exc:case.update(Native_admission='REFUSED',reason=str(exc))
  cases[label]=(case,c)
  for phase in range(3):
   parents.append(dict(case=label,phase=phase,record=json.loads(serialize_game_record(s.to_record())),state=record_value(s.state),state_sha256=digest(s.state),witness_sha256=digest(s._search_witnesses)))
   if phase==0:
    fx,fy,tx,ty=coords;aa=[a for a in s.legal_actions()if a.from_square is not None and(a.from_square.file,a.from_square.rank,a.to_square.file,a.to_square.rank)==coords];assert len(aa)==1,(label,len(aa));s.submit(aa[0])
   elif phase==1:
    aa=sorted(s.legal_actions(),key=repr);assert aa;s.submit(aa[0])
 write_json(D/'inputs.json',dict(cases=[x[0]for x in cases.values()],parents=parents,scope='ThreeexistingcompleteIRfixtures withdeclaredinitialsetup, actualtrigger/nextreply Sessionrecords, nohistoryediting.'))
 with(D/'native-queries.jsonl').open('x',encoding='utf8',newline='\n')as nl,(D/'core-queries.jsonl').open('x',encoding='utf8',newline='\n')as cl:
  for p in parents:
   poll();case,c=cases[p['case']];s=GameSession.replay(c,deserialize_game_record(json.dumps(p['record'])));assert record_value(s.state)==p['state'];before=(s.state,s.to_record(),s.history,s._search_witnesses);got={}
   if p['case']in native:
    for mode in (False,True):
     poll();assert counts['Native_queries']<18;e=SemanticSearchEngine(c,native[p['case']],board_values=case['board_values'],hand_values=case['hand_values'],tt_megabytes=0);tick=time.perf_counter();r=e.search(s,SearchLimits(max_depth=2,max_nodes=131072,max_time_seconds=2,quiescence_max_depth=4),root_window_pruning=mode);q=dict(case=p['case'],phase=p['phase'],mode=mode,parent_sha256=digest(s.state),parent_unchanged=before==(s.state,s.to_record(),s.history,s._search_witnesses),result=record_value(r),seconds=time.perf_counter()-tick);nl.write(json.dumps(q,separators=(',',':'))+'\n');nl.flush();got[mode]=q;counts['Native_queries']+=1;counts['Native_main']+=r.nodes;counts['Native_q']+=r.qnodes;assert q['parent_unchanged'];leaf=GameSession.replay(c,s.to_record())
     for a in r.decision_line:leaf.declare(a)if isinstance(a,str)else leaf.submit(a)
     del e
   remaining=360-(time.monotonic()-start)
   if remaining<.5:raise TimeoutError('GLOBAL_CAP')
   stats=SearchStatistics();tick=time.perf_counter();action,score,pv,cause=run_root_search(s.state,c,Material(case['board_values'],case['hand_values']),TranspositionTable(max_entries=1),SearchLimits(max_depth=2,max_nodes=200000,max_time_seconds=min(30,remaining-.1),quiescence_max_depth=4),Stop(),stats,use_tt=False,use_ordering=False,tuning=SearchTuning(),_history_witnesses=s._search_witnesses)
   q=dict(case=p['case'],phase=p['phase'],action=record_value(action),score=score,pv=record_value(pv),cause=cause,statistics=record_value(stats),parent_unchanged=before==(s.state,s.to_record(),s.history,s._search_witnesses),seconds=time.perf_counter()-tick);cl.write(json.dumps(q,separators=(',',':'))+'\n');cl.flush();counts['Core_calls']+=1;counts['Core_main']+=stats.nodes;counts['Core_q']+=stats.qnodes;assert q['parent_unchanged']
   mapped=score-900000000 if score>=900000000 else score+900000000 if score<=-900000000 else score
   for mode,n in got.items():
    z=n['result'];ok=stats.completed_depth==2 and stats.result_ordinary_qdepth==4 and z['completed_depth']==2 and z['result_ordinary_qdepth']==4
    comparisons.append(dict(case=p['case'],phase=p['phase'],mode=mode,comparable_complete_q4=ok,value_equal=z['score']==mapped if ok else None,action_equal=z['action']==record_value(action)if ok else None,Core_depth=stats.completed_depth,Core_q=stats.result_ordinary_qdepth,Native_depth=z['completed_depth'],Native_q=z['result_ordinary_qdepth']))
   print('MECHANISM_CONSUMER',p['case'],p['phase'],stats.completed_depth,stats.result_ordinary_qdepth,cause,round(time.monotonic()-start,3),flush=True)
except BaseException as exc:status='INCOMPLETE';error=repr(exc)
write_json(D/'result.json',dict(status=status,error=error,counts=counts,comparisons=comparisons,seconds=time.monotonic()-start,scope='Next-stepfinitecomplete-mechanismconsumer only. Supported/refused states andincompleteq4targets retained; selectedactiondifferences notautomaticallybad. No independentfreshsourcequalification,fitness/WDL/all-domain/learner/defaultclaim.'))
print('MECHANISM_CLOSED',status,error,counts,time.monotonic()-start,flush=True)
