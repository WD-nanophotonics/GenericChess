from pathlib import Path
from collections import defaultdict,Counter
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state
from scripts.generic_win_proof import _same_state
from scripts.generic_session_win_proof import SessionWinCertificate,verify_session_certificate
from results.dev_aux.task2048.portable_certificate import decode
from results.dev_aux.task2068.teacher import CanonicalTeacher
OUT=Path('results/dev_aux/task2151')
def run():
 start=time.perf_counter();root=Path('results/dev_aux/task2147');p=json.loads((root/'plan.json').read_text(encoding='utf-8'));completion=json.loads((root/'completion.json').read_text(encoding='utf-8'));started=json.loads((root/'started.json').read_text(encoding='utf-8'));assert started['source_sha']==hashlib.sha256((root/'run.py').read_bytes()).hexdigest()
 inputs=json.loads(Path('results/dev_aux/task2139/inputs.json').read_text(encoding='utf-8'))['roots'];rows=[json.loads(x)for x in(root/'queries.jsonl').read_text(encoding='utf-8').splitlines()];certs={x['query']:x for x in map(json.loads,(root/'certificates.jsonl').read_text(encoding='utf-8').splitlines())};teacher=CanonicalTeacher('results/dev_aux/task2093','results/dev_aux/task2094','results/dev_aux/task2095');groups=defaultdict(Counter);paired=defaultdict(dict);compiled={};truth={};rankcoverage=defaultdict(Counter);uniqueproof=set();checks=[];expected=[]
 for inp in inputs:
  family=inp['family'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(inp['rules']).read_text(encoding='utf-8')));compiled[family]=c;s=GameSession(c);label=teacher.label(s);assert label.quality=='EXACT_CANONICAL_FRESH_ROOT'
  for target in(0,1):
   value=label.value if s.state.position.side_to_move==target else-label.value;truth[family,target]=(value,label.rank)
   off=(family+target)%3;envelopes=p['envelopes'][off:]+p['envelopes'][:off];arms=p['provers']if(family+target)%2==0 else list(reversed(p['provers']))
   for env in envelopes:expected.extend((family,target,arm,env)for arm in arms)
 assert len(rows)==576==len(expected)==completion['queries']
 for i,(r,exp)in enumerate(zip(rows,expected)):
  assert(r['family'],r['target'],r['arm'],r['envelope'])==exp;assert r['nodes']<=r['envelope']['nodes']and r['peak_depth']<=96
  family,target=r['family'],r['target'];value,rank=truth[family,target];group=r['arm']+'_'+str(r['envelope']['seconds']);g=groups[group];g['queries']+=1;g['proved']+=r['status']=='PROVEN_WIN';g['nodes']+=r['nodes'];g['seconds']+=r['seconds'];g['reason_'+r['reason']]+=1;g['true_WIN_contexts']+=value==1
  rg=rankcoverage[(group,str(rank)if value==1 else'nonWIN')];rg['queries']+=1;rg['proved']+=r['status']=='PROVEN_WIN'
  if r['reason']=='no_forced_win_in_exhausted_tree':assert value!=1
  if r['status']=='PROVEN_WIN':
   assert value==1 and i in certs;cr=certs[i];s=GameSession(compiled[family]);certificate=SessionWinCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,target,decode(cr['tree'],s.compiled.ruleset_fingerprint));vr=verify_session_certificate(s,certificate,max_nodes=131072,seconds=4.);assert vr['verified'];assert r['reference_verification']['verified']or r['prefix_verification']['verified'];assert r['actual_mate']is not None
   record=deserialize_game_record(json.dumps(r['actual_mate']['record']));actual=GameSession.replay(s.compiled,record);assert actual.result.winner==target and len(record.actions)==r['actual_mate']['moves'];checks.append(dict(query=i,verified=vr));uniqueproof.add((family,target))
  else:assert i not in certs and r['actual_mate']is None
  paired[(family,target,r['envelope']['nodes'])][r['arm']]=i
 comparable=0;equal=0;disagreements=[]
 for key,pair in paired.items():
  assert set(pair)==set(p['provers']);a,b=(rows[pair[n]]for n in p['provers'])
  if a['reason']!='time_budget'and b['reason']!='time_budget':
   comparable+=1
   same=all(a[k]==b[k]for k in('status','reason','nodes','frontiers','transitions','eager_board_successors','claims_assessed','peak_depth'))
   if a['status']=='PROVEN_WIN'and b['status']=='PROVEN_WIN':same&=certs[pair['BATCH_PN']]['tree']==certs[pair['RETAINED_THRESHOLD']]['tree']
   equal+=same
   if not same:disagreements.append(dict(case=key,left=a,right=b))
 out=dict(status='PASS_COMPLETE_NO_TABLE_PANEL_ACTUAL_CERTIFICATES_AND_GROUNDTRUTH',queries=len(rows),unique_root_targets=96,true_WIN_root_targets=sum(v==1 for v,r in truth.values()),unique_proved_root_targets=len(uniqueproof),all65_certificates_independently_verified=len(checks),groups={k:dict(v)for k,v in groups.items()},rank_coverage={str(k):dict(v)for k,v in rankcoverage.items()},both_non_time_censored_pairs=comparable,identical_search_prefix_pairs=equal,noncensored_disagreements=disagreements,seconds=time.perf_counter()-start,scope='All96root-targetcontexts nooutcomeselection; initiallabels checkedONLYafterclosedqueries. PuregenericprovershadNOtableinput. Familiarpreviouslyexposedpopulation, no independentlabelholdout. Verification/cursor costs separatefromproofcaps. NonWINqueries UNKNOWN neverDRAW/reward.')
 (OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');(OUT/'certificate-checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items()if k not in('rank_coverage','noncensored_disagreements')}),flush=True)
if __name__=='__main__':run()
