"""Selected-action Core q4 controls for the next-step semantic consumers."""
from pathlib import Path
import sys,json,time,os
sys.path.insert(0,str(Path.cwd()))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.search import negamax,_Context,_Budget,INF,SearchAborted
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
D=Path(__file__).resolve().parent;start=time.monotonic();i=json.loads((D/'inputs.json').read_bytes());cases={c['name']:c for c in i['cases']};parents={(p['case'],p['phase']):p for p in i['parents']};cores={(c['case'],c['phase']):c for c in map(json.loads,(D/'core-queries.jsonl').read_bytes().splitlines())};chosen={}
for n in map(json.loads,(D/'native-queries.jsonl').read_bytes().splitlines()):
 c=cores[n['case'],n['phase']]
 if n['result']['action']==c['action']:continue
 key=(n['case'],n['phase'],json.dumps(n['result']['action'],sort_keys=True));chosen.setdefault(key,dict(case=n['case'],phase=n['phase'],action=n['result']['action'],expected=c['score'],modes=[]))['modes'].append(n['mode'])
assert len(chosen)==4
write_json(D/'selected-action-plan.json',dict(selection='All4unique Nativeactions differing fromCorebest among18completedq4 modeobservations; chooseonlybyactiondifference, notfitness.',question='Are observed choices genuinely equivalent underexistingCoreq4 ratherthanonlyequalreportedrootscore?',max_calls=4,seconds_per_call=60,global_seconds=300,no_Native_or_training=True))
class Material:
 def __init__(self,b,h):self.b=b;self.h=h
 def evaluate(self,s):
  v=sum((1 if p.owner==0 else-1)*self.b[p.current_type_id]for p in s.position.board if p)+sum((s.position.hands[0].count(t)-s.position.hands[1].count(t))*v for t,v in self.h.items());return v*(1 if s.position.side_to_move==0 else-1)
class Stop:
 def is_cancelled(self):
  for n in ('rollout','advisor','slack'):
   f=json.loads((Path(os.environ.get('GC_REPLAY_STOP_ROOT',Path.cwd()))/'.local_agent'/(n+'.json')).read_bytes())
   if f.get('stopped')or f.get('user_paused'):return True
  return time.monotonic()-start>=300
rows=[]
for v in chosen.values():
 case=cases[v['case']];c=compile_semantic_ruleset(ruleset_from_dict(case['rule']));s=GameSession.replay(c,deserialize_game_record(json.dumps(parents[v['case'],v['phase']]['record'])));raw=dict(v['action']);raw['to_square']=Square(**raw['to_square'])
 if 'from_square'in raw:raw['from_square']=Square(**raw['from_square']);a=SemanticBoardMove(**raw)
 else:a=SemanticDropMove(**raw)
 s.submit(a);before=(s.state,s.to_record(),s.history,s._search_witnesses);rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses);st=SearchStatistics();rt.attach_stats(st);lim=SearchLimits(max_depth=1,max_nodes=200000,max_time_seconds=60,quiescence_max_depth=4);ctx=_Context(c,Material(case['board_values'],case['hand_values']),TranspositionTable(max_entries=1),st,_Budget(lim,Stop()),SearchTuning(),False,False,4,8,None,runtime=rt,first_main_iteration_complete=True);tick=time.perf_counter()
 try:z=negamax(s.state,1,-INF,INF,1,ctx);r=dict(status='COMPLETE',child_score=z.score,backed_up=-z.score,equal_root_target=-z.score==v['expected'])
 except SearchAborted as exc:r=dict(status='UNKNOWN',cause=str(exc))
 rt.assert_balanced();assert before==(s.state,s.to_record(),s.history,s._search_witnesses);rows.append(dict(**v,**r,seconds=time.perf_counter()-tick,statistics=record_value(st)))
write_json(D/'selected-action-result.json',dict(status='CLOSED',rows=rows,seconds=time.monotonic()-start,scope='Fourpreviousdifferentactions; actualfullhistory childCoreq4. Notallactions/all-domain/fitness/freshsourceproof.'))
print('MECHANISM_SELECTED_CHILDREN',[(r['case'],r['phase'],r.get('equal_root_target'))for r in rows],time.monotonic()-start)
