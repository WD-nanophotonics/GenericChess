"""Offline consumers for closed75 data; never rerun study producers or fit."""
from pathlib import Path
from dataclasses import replace
from collections import Counter,defaultdict
import json,time,hashlib
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus,SessionResult
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.generic_session_win_proof import SessionChoice,SessionWinCertificate,verify_session_certificate
from results.dev_aux.task2048.portable_certificate import decode as decode_tree
from results.dev_aux.task2187.trace import root_session
from results.dev_aux.task2179.graph import GraphCertificate,GraphNode,verify_graph
from results.dev_aux.task2191.semantic_graph import canonical as core_canonical
from results.dev_aux.task2199.semantic_graph import canonical as full_canonical
from scripts.generic_win_proof import _same_state
OUT=Path('.replay_output75')

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def record(s):return json.loads(serialize_game_record(s.to_record()))
def replay(c,value):return GameSession.replay(c,deserialize_game_record(json.dumps(value)))
def action(value,fp):return deserialize_game_record(json.dumps(dict(schema_version=1,ruleset_fingerprint=fp,actions=[value],resigned_by=None))).actions[0]
def decode_graph(s,data):
 return GraphCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,data['target'],tuple(GraphNode(n['rank'],tuple((SessionChoice('ACTION',action=action(e['action'],s.compiled.ruleset_fingerprint)),e['child'])for e in n['edges']),None if n['terminal']is None else SessionResult(SessionStatus(n['terminal']['status']),n['terminal']['winner']))for n in data['nodes']))

def run(tasks=(2190,2204,2202)):
 began=time.perf_counter();deadline=began+600;OUT.mkdir(exist_ok=True);roots={r['family']:r for r in read('results/dev_aux/task2177/inputs.json')['roots']};summary={};certificates=actual_paths=actual_moves=0;proofcontexts=set()
 def cancel():return time.perf_counter()>=deadline
 # No live Slack/accounts/stop state: this is a copied private replay tree.
 for task in tasks:
  folder=Path(f'results/dev_aux/task{task}');p=read(folder/'plan.json');done=read(folder/'completion.json');rows=[json.loads(x)for x in(folder/'queries.jsonl').read_text().splitlines()];saved=[json.loads(x)for x in(folder/'certificates.jsonl').read_text().splitlines()]
  assert len(rows)==done['queries']and done['missing']==p['expected_queries']-len(rows)
  assert [r['query']for r in rows]==list(range(len(rows)))
  unique=set()
  for r in rows:
   if task==2202:key=(r['family'],r['arm'],r['style'],r['wall'])
   else:key=(r['family'],r['arm'],r['envelope']['seconds'])
   assert key not in unique;unique.add(key)
   assert r['family']in roots
   if r['arm']!='PN':
    assert r['positions']<=8192 and r['expanded']<=8192 and r['transitions']<=65536
   if r['arm']=='BOUNDED_INCREMENTAL':assert r['updates']<=128*(r['expanded']+1)and r['visits']<=128*(r['expanded']+1)
  byquery={x['query']:x for x in saved};assert len(byquery)==len(saved)
  for i,x in byquery.items():
   assert cancel()is False;r=rows[i];assert r['family']==x['family']and r['arm']==x['arm'];s=root_session(roots[r['family']]);target=roots[r['family']]['target']
   if r['arm']=='PN':
    cert=SessionWinCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,target,decode_tree(x['certificate'],s.compiled.ruleset_fingerprint));vr=verify_session_certificate(s,cert,max_nodes=131072,seconds=1.,cancel=cancel,_clock=lambda:0.)
   else:
    assert x['root_record']==record(s)if'root_record'in x else True
    cert=decode_graph(s,x['certificate']);vr=verify_graph(s,cert,max_nodes=131072,seconds=1.,cancel=cancel,_clock=lambda:0.)
   assert vr['verified'];certificates+=1;proofcontexts.add((r['family'],target))
   # Recorded played path is exact trajectory evidence, not a new sample.
   if r['actual_mate']is not None:
    actual=replay(s.compiled,r['actual_mate']['record']);assert actual.result.winner==target and actual.result.status is not SessionStatus.ONGOING;assert len(actual.to_record().actions)==r['actual_mate']['moves'];actual_paths+=1;actual_moves+=r['actual_mate']['moves']
  groups={}
  for r in rows:
   key=r['arm']+'/'+str(r.get('wall',r.get('envelope',{}).get('seconds')))+('/'+r['style']if'style'in r else'')
   g=groups.setdefault(key,dict(queries=0,verified=0,actual_mates=0,positive_roots=set(),expanded=0,selector_visits=0,selector_updates=0,seconds=0.,reasons=Counter()))
   g['queries']+=1;g['verified']+=bool(r['verification']and r['verification']['verified']);g['actual_mates']+=r['actual_mate']is not None;g['expanded']+=r.get('expanded',0);g['selector_visits']+=r.get('visits',0);g['selector_updates']+=r.get('updates',0);g['seconds']+=r.get('outer_seconds',r.get('outer_query_seconds',0.));g['reasons'][r['reason']]+=1
   if r['verification']and r['verification']['verified']:
    assert roots[r['family']]['label']!='DRAW';g['positive_roots'].add(r['family'])
  for g in groups.values():g['positive_roots']=sorted(g['positive_roots']);g['reasons']=dict(g['reasons'])
  summary[str(task)]=dict(status=done['status'],queries=len(rows),missing=done['missing'],saved_certificates=len(saved),groups=groups,whole_project_seconds=done['seconds'])
 # The four trace-query witnesses and all saved full frontier records.
 trace_rows=read('results/dev_aux/task2187/queries.json')
 for item in read('results/dev_aux/task2187/certificates.json'):
  r=next(r for r in trace_rows if r['family']==item['family']and r['arm']==item['arm']);s=root_session(roots[item['family']])
  if item['arm']=='PN':
   cert=SessionWinCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,roots[item['family']]['target'],decode_tree(item['certificate'],s.compiled.ruleset_fingerprint));v=verify_session_certificate(s,cert,max_nodes=131072,seconds=1.,cancel=cancel,_clock=lambda:0.)
  else:cert=decode_graph(s,item['certificate']);v=verify_graph(s,cert,max_nodes=131072,seconds=1.,cancel=cancel,_clock=lambda:0.)
  assert v['verified'];certificates+=1;proofcontexts.add((item['family'],roots[item['family']]['target']))
  if r['actual_mate']is not None:
   actual=replay(s.compiled,r['actual_mate']['record']);assert actual.result.winner==roots[item['family']]['target'];actual_paths+=1;actual_moves+=r['actual_mate']['moves']
 import results.dev_aux.task2187.audit as trace_audit
 trace_audit.OUT=OUT/'trace_audit';trace_audit.run();summary['2187']=dict(queries=4,all_frontier_records=1356)
 # Baseline adapter node-only identity and certificate equality.
 rr=read('results/dev_aux/task2197/queries.json');group=defaultdict(list)
 for r in rr:group[r['family']].append(r['result'])
 assert len(group)==62 and all(len(v)==2 and v[0]==v[1]for v in group.values());summary['2197']=dict(pairs_exact=62,queries=len(rr))
 for r in rr:
  if r['result']['certificate']is not None:
   session=root_session(roots[r['family']]);cert=decode_graph(session,r['result']['certificate']);v=verify_graph(session,cert,max_nodes=131072,seconds=1.,cancel=cancel,_clock=lambda:0.);assert v['verified'];certificates+=1

 # Full saved lifecycle prefix/edge state replay, all typed fields retained.
 folder=Path('results/dev_aux/task2194');c=compile_ruleset_for_execution(deserialize_ruleset((folder/'rules.json').read_text()));prefixes=read(folder/'prefixes.json');edges=read(folder/'edges.json')
 for r in prefixes:
  s=replay(c,r['record']);assert repr(s.state)==r['state_repr'];canon=core_canonical(s.state.position,c);assert _same_state(canon.state.position,s.state.position)and repr(canon.state)==r['canonical_state_repr'];assert[action_to_dict(a)for a in s.legal_actions()]==r['legal_actions']
 for e in edges:
  s=replay(c,e['record']);assert hashlib.sha256(repr(s.state).encode()).hexdigest()==e['state_sha']and repr(s.state.position)==e['position_repr']and repr(s.result)==e['result']
 summary['2194']=dict(prefixes=len(prefixes),edges=len(edges))
 # Same-fingerprint current R, different base identity and capture/drop fronts.
 folder=Path('results/dev_aux/task2196');c=compile_ruleset_for_execution(deserialize_ruleset((folder/'rules.json').read_text()));r=read(folder/'result.json');ss=[]
 for row in r['after']:
  s=replay(c,row['record']);assert repr(s.state)==row['state_repr'];assert[action_to_dict(a)for a in s.legal_actions()if hasattr(a,'base_type_id')]==row['drops'];ss.append(s)
 assert ss[0].state.position.hands[0].count('R')==1 and ss[1].state.position.hands[0].count('P')==1
 summary['2196']=dict(actual_prefix_records=2,drop_fronts_preserved=True,limitation='Originalselectedwinningdrop certificate/action wasnotserialized; itsownerassertionnot upgraded to independentoriginal-proof replay.')
 # Exact actual NONTERMINAL future repetition boundary; both executors.
 r=read('results/dev_aux/task2198/result.json')
 for row in r['rows']:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2198',row['arm'].lower()+'-rules.json').read_text()));s=replay(c,row['root_record']);future=replay(c,row['future_record']);key=repetition_identity_key(future.state.position,c)
  assert s.result.status is SessionStatus.ONGOING and future.result.status is SessionStatus.REPETITION and core_canonical(future.state.position,c).result.status is SessionStatus.ONGOING
  assert dict(s.state.repetition_counts)[key]==row['limit']-1
 summary['2198']=dict(actual_history_boundaries=2,zero_count_injection=True)
 # S4 actual mate and trigger rights/frontiers; original proof not serialized.
 r=read('results/dev_aux/task2200/result.json');c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2200/mate-rules.json').read_text()));s=replay(c,r['actual_proved_record']);assert s.result.winner==0
 c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2200/trigger-rules.json').read_text()));n=0
 for row in r['trigger_branches']:
  s=replay(c,row['record']);assert repr(s.state)==row['state_repr']and[action_to_dict(a)for a in s.legal_actions()]==row['legal_actions'];canon=full_canonical(s.state.position,c)
  for a in s.legal_actions():
   actual=__import__('copy').copy(s);actual.submit(a);forward=__import__('copy').copy(canon);forward.submit(a);assert _same_state(actual.state.position,forward.state.position)and actual.result==forward.result;n+=1
 assert n==45;summary['2200']=dict(actual_mate_record=1,trigger_frontier_edges=n,limitation='S4originalproofsummaryownerreported; fresh tinyfixtureproofs separatelyqualified byregression tests, not identicaloriginalproofreplay.')
 # Semantic-only transformed actor captured back to its base hand identity.
 r=read('results/dev_aux/task2206/result.json');c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2206/rules.json').read_text()));edges=0
 for row in r['rows']:
  s=replay(c,row['record']);assert repr(s.state)==row['state_repr']and[action_to_dict(a)for a in s.legal_actions()]==row['legal_actions'];forward=full_canonical(s.state.position,c)
  if row['step']>=2:assert s.state.position.hands[1].count('R')==1 and s.state.position.hands[1].count('TP')==0
  for a in s.legal_actions():
   child=__import__('copy').copy(s);child.submit(a);other=__import__('copy').copy(forward);other.submit(a);assert _same_state(child.state.position,other.state.position)and child.result==other.result;edges+=1
 assert edges==112;summary['2206']=dict(actual_prefixes=4,full_frontier_children=edges)
 # Exact failed execution-source versions are available, not rewritten.
 source_map=read('results/dev_aux/task2191/executed-source-map.json')
 for row in source_map.values():
  name=row.get('file',row.get('exact_source',row.get('exact_reconstructed_source')));assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==row['sha']
 for row in read('results/dev_aux/task2207/inventory.json')['sources']:assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
 for task in(2192,2193,2195):assert read(f'results/dev_aux/task{task}/failure.json')['status'].startswith('FAILED')
 assert read('results/dev_aux/task2199/harness-failure.json')['prover_calls']==1
 result=dict(status=('PASS_CLOSED75_SOURCE_ONLY_CONSUMERS'if tasks==(2190,2204,2202)else'PASS_SELECTED75_SOURCE_ONLY_CONSUMERS'),selected_studies=list(tasks),studies=summary,independently_verified_saved_certificates=certificates,distinct_canonical_proof_contexts=len(proofcontexts),actual_recorded_mate_paths=actual_paths,actual_recorded_mate_moves=actual_moves,seconds=time.perf_counter()-began,new_study_provers_or_fit_or_games=0,scope='ExistingpublicCore/Session sharedruleauthority. Full savedproofs/records verified; unsavedfixtureproofs explicitlyownerreported, freshregressionproofs separate. No oldcapreset or hidden production entry.')
 (OUT/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(dict(status=result['status'],certificates=certificates,paths=actual_paths,seconds=result['seconds'])),flush=True)
if __name__=='__main__':run()
