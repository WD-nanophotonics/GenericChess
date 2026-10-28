"""AUX independent saved-game reader; Core only, no Player/search/producer import."""
from __future__ import annotations
import argparse, gzip, hashlib, json, math, sys, time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value,write_record
from scripts.verify_published_boolean_returns import diagnostic_action
SOURCE="c42f006664e028cc9792a5bea40c711005ef23c9"
def load(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def digest(b):return hashlib.sha256(b).hexdigest()
def record_hash(s):return digest(json.dumps(record_value(s.to_record()),sort_keys=True,separators=(',',':')).encode())
def finite(x):return type(x) in (int,float) and math.isfinite(x) and x>=0

def verify_game(g,root,returns,compiled,*,check_pv=True):
 assert type(g['game_id']) is int and type(g['on_seat']) is int and g['on_seat'] in (0,1)
 assert g['case_id']==root['id'] and g['family']==root['family'] and g['layout']==root['layout']
 assert g['initial_record']==root['record'] and g['fingerprint']==root['fingerprint']
 s=GameSession.replay(compiled,deserialize_game_record(json.dumps(root['record'])))
 nodes={};edges=[]
 def node(session):
  key=record_hash(session)
  if key not in nodes:
   nodes[key]=dict(actor=session.state.position.side_to_move,legal=len(session.legal_actions()),terminal=record_value(session.state.terminal_status),ply=session.state.ply_count)
  return key
 def edge(session,act):
  parent=node(session);token=json.dumps(record_value(act),sort_keys=True,separators=(',',':'));session.submit(act);child=node(session);edges.append(dict(parent=parent,action=token,child=child));return child
 rows=[];pv_plies=0;pv_endings=Counter();ids=set();wall=Counter();began=time.perf_counter()
 for q in g['queries']:
  qid=q['query_id'];assert qid not in ids;ids.add(qid)
  raw=returns[qid];text=raw['original_utf8'];assert digest(text.encode())==raw['sha256'];original=json.loads(text);assert set(q)-set(original)=={'record_after_sha256','pv_legal','root_unchanged'};assert all(q[k]==v for k,v in original.items())
  assert type(q['seat']) is int and type(q['ply_before']) is int and type(q['on']) is bool
  assert type(q['actual_tuning']['use_pvs']) is bool
  before=record_hash(s);assert q['record_before_sha256']==before
  assert q['seat']==s.state.position.side_to_move and q['ply_before']==s.state.ply_count
  assert q['on']==(q['seat']==g['on_seat']) and q['actual_tuning']['use_pvs']==q['on']
  assert q['status']=='RETURNED' and s.result.status.value=='ongoing'
  assert q['root_unchanged'] is True and q['pv_legal'] is True and q['provider_present'] is True
  d=q['decision'];assert d['runtime_depth_balanced'] is True and d['runtime_pushes']==d['runtime_pops']
  assert d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
  assert q['evaluation_profile']['ruleset_fingerprint']==root['fingerprint']
  lim=q['limits'];assert (lim['max_depth'],lim['max_nodes'],lim['quiescence_max_depth'],lim['quiescence_hard_max_depth'])==(64,500000,4,8)
  assert q['requested_service_seconds']==1 and finite(lim['max_time_seconds']) and 0<lim['max_time_seconds']<=1
  for k in ['service_wall_seconds','cpu_seconds','construction_packing_seconds']:assert finite(q[k])
  assert lim['max_time_seconds']+q['construction_packing_seconds']<=1.000000001
  assert q['timing_eligible']==(q['service_wall_seconds']<=1.1)
  legal=s.legal_actions();a=diagnostic_action(d['action'],root['fingerprint']);assert a in legal
  pv=d['principal_variation'];assert not pv or pv[0]==d['action']
  if check_pv:
   branch=GameSession.replay(compiled,s.to_record())
   for x in pv:
    assert branch.result.status.value=='ongoing';edge(branch,diagnostic_action(x,root['fingerprint']));pv_plies+=1
   pv_endings[branch.result.status.value]+=1
  anchor_actions=sum(x.actor_type_id=='K' for x in legal)
  rows.append(dict(qid=qid,ply=q['ply_before'],actor=q['seat'],on=q['on'],before_sha256=before,legal_count=len(legal),anchor_legal_count=anchor_actions,forced=len(legal)==1,action=d['action'],depth=d['completed_depth'],reason=d['termination_reason'],source=d['result_source'],score=d['score'],pv_length=len(pv),wall=q['service_wall_seconds'],cpu=q['cpu_seconds']))
  edge(s,a);assert record_hash(s)==q['record_after_sha256']
  wall[str(q['on'])]+=q['service_wall_seconds']
 assert g['Core_terminal']['winner'] is None or type(g['Core_terminal']['winner']) is int
 assert record_value(s.to_record())==g['final_record']
 assert record_value(s.state.terminal_status)==g['Core_terminal'] and record_value(s.result)==g['Session_result']
 assert g['status']=='TERMINAL' and s.state.terminal_status.is_terminal
 assert g['timing_eligible']==all(q['timing_eligible'] for q in g['queries'])
 return dict(game_id=g['game_id'],case=g['case_id'],family=g['family'],layout=g['layout'],on_seat=g['on_seat'],terminal=record_value(s.state.terminal_status),nodes=nodes,edges=edges,queries=rows,pv_plies=pv_plies,pv_endings=dict(pv_endings),actual_replay_wall=time.perf_counter()-began,points=None if not s.state.terminal_status.is_terminal else .5 if s.result.winner is None else int(s.result.winner==g['on_seat']))

def verify_qualifications(source):
 roots={r['id']:r for r in load(source/'inputs.json.gz')['rows']};returns=load(source/'results/returns.json.gz');quals=load(source/'results/qualification.json.gz');frozen=load(source/'results/frozen.json.gz');old=load(source/'results/original-frozen.json.gz')
 assert len(quals)==24 and [q['slot'] for q in quals]==list(range(24))
 assert frozen['input_sha256']==old['input_sha256']==digest(gzip.decompress((source/'inputs.json.gz').read_bytes()))
 assert frozen['plan']['whole_deadline_utc']==old['plan']['whole_deadline_utc']
 assert load(source/'results/loaded-binary.json.gz')==load(source/'results/original-loaded-binary.json.gz')
 changed=[name for name,h in old['plan']['sources'].items() if frozen['plan']['sources'].get(name)!=h];assert changed==['scripts/leaper_new_family_pvs.py']
 pvcount=0;goals=Counter();ids=set();reused=0;proofs=[]
 for q in quals:
  root=roots[q['case_id']];rule=ruleset_from_dict(root['RuleSet']);c=compile_legacy_ruleset_for_semantic_execution(rule);session=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
  raw=returns[q['query_id']];text=raw['original_utf8'];assert digest(text.encode())==raw['sha256'];r=json.loads(text);assert r['decision']==q['decision'] and r['on']==q['on'];assert r['record_before_sha256']==record_hash(session);assert r['actual_tuning']['use_pvs']==r['on']
  assert r['query_id']==q['query_id'] and q['query_id'] not in ids;ids.add(q['query_id'])
  if q['status']=='RETURNED_REUSED':assert digest(text.encode())==frozen['plan']['prior_return_hashes'][q['query_id']+'.json'];reused+=1
  else:assert q['status']=='RETURNED'
  d=r['decision'];a=diagnostic_action(d['action'],root['fingerprint']);assert a in session.legal_actions();pv=GameSession.replay(c,session.to_record())
  assert d['runtime_depth_balanced'] is True and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
  assert r['provider_present'] and r['limits']['max_depth']==2 and r['limits']['quiescence_max_depth']==4 and r['limits']['quiescence_hard_max_depth']==8
  for x in d['principal_variation']:pv.submit(diagnostic_action(x,root['fingerprint']));pvcount+=1
  goal=q['accepted_goal'];goals[goal]+=1
  if goal=='completed_D2':assert d['completed_depth']==2
  else:
   assert goal=='Core_verified_immediate_WIN' and d['completed_depth']==0 and d['result_source']=='root_immediate_win';actor=session.state.position.side_to_move;session.submit(a);assert session.state.terminal_status.is_terminal and session.result.winner==actor
   proofs.append(dict(slot=q['slot'],case=root['id'],qid=q['query_id'],terminal=record_value(session.state.terminal_status)))
 assert reused==19
 return dict(count=len(quals),reused=reused,new=24-reused,pv_plies=pvcount,accepted_goals=dict(goals),immediate_proofs=proofs,changed_caller=changed,ids=sorted(ids),original_registration='FAILED_preserved_not_relabelled')

def verify_cohort_contract(source):
 from generic_chess.ai.alphabeta.tuning import SearchTuning
 from generic_chess.ai.evaluation.profile import build_ruleset_profile
 from generic_chess.ai.evaluation.config import EvaluationConfig
 roots=load(source/'inputs.json.gz')['rows'];returns=load(source/'results/returns.json.gz');frozen=load(source/'results/frozen.json.gz');games=load(source/'results/games.json.gz')
 profiles={};tunings={on:record_value(SearchTuning(use_pvs=on)) for on in (False,True)}
 for r in roots:
  c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(r['RuleSet']));profiles[r['fingerprint']]=record_value(build_ruleset_profile(c,EvaluationConfig()))
 for qid,row in returns.items():
  text=row['original_utf8'];assert digest(text.encode())==row['sha256'];q=json.loads(text);assert q['query_id']==qid
  assert type(q['on']) is bool and q['actual_tuning']==tunings[q['on']]
  profile=q['evaluation_profile'];assert profile==profiles[profile['ruleset_fingerprint']]
 observed=[q['query_id'] for g in games for q in g['queries']]+[q['query_id'] for q in load(source/'results/qualification.json.gz')]
 assert len(observed)==len(set(observed))==1787 and set(observed)==set(returns)
 for p,text in frozen['sources'].items():assert digest(text.encode())==frozen['plan']['sources'][p]
 counts=Counter();cpu=Counter();wall=Counter();depth=Counter();source_counts=Counter();cancel=Counter()
 for g in games:
  for q in g['queries']:
   d=q['decision'];on=q['on'];counts['ON' if on else 'OFF']+=1
   if not on:assert d['pvs_null_window_searches']==d['pvs_researches']==0
   counts['null' if on else 'off_null']+=d['pvs_null_window_searches'];counts['research' if on else 'off_research']+=d['pvs_researches'];cpu[str(on)]+=q['cpu_seconds'];wall[str(on)]+=q['service_wall_seconds'];depth[str(d['completed_depth'])]+=1;source_counts[d['result_source']]+=1;cancel[d['termination_reason']]+=1
 return dict(exact_declared_source_hashes=len(frozen['sources']),profile_rules=len(profiles),literal_return_contracts=len(returns),game_calls=1763,qualification_calls=24,unique_ids_and_no_orphans=True,only_changed_SearchTuning_field='use_pvs',counts=dict(counts),saved_wall=dict(wall),saved_cpu=dict(cpu),completed_depths=dict(depth),returned_sources=dict(source_counts),termination_reasons=dict(cancel),scope='Fresh independently recomputed rule profiles and literal saved contracts; not historical process observation, TT reconstruction, matched-state timing or new strength experiment.')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int,default=24);args=ap.parse_args()
 roots={x['id']:x for x in load(args.source/'inputs.json.gz')['rows']};games=load(args.source/'results/games.json.gz');returns=load(args.source/'results/returns.json.gz');args.output.mkdir(parents=True,exist_ok=True)
 assert len(games)==24 and {g['game_id'] for g in games}==set(range(24))
 for g in games[args.start:args.stop]:
  r=roots[g['case_id']];rule=ruleset_from_dict(r['RuleSet']);assert compute_fingerprint(rule)==r['fingerprint'];assert rule.max_ply==128 and rule.repetition_limit==4
  compiled=compile_legacy_ruleset_for_semantic_execution(rule);result=verify_game(g,r,returns,compiled);write_record(args.output/('game-%02d.json'%g['game_id']),result);print(json.dumps({k:v for k,v in result.items() if k not in ('queries','nodes','edges')}),flush=True)
if __name__=='__main__':main()
