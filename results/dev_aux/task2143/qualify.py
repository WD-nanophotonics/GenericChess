from pathlib import Path
from functools import lru_cache
from copy import copy
from collections.abc import Mapping
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_session_win_proof import verify_session_certificate,SessionStrategyCursor
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2086.rank_certificate import RankCertificateProvider
from results.dev_aux.task2048.portable_certificate import encode
from results.dev_aux.task2131.stop_reader import ParsedStopReader
OUT=Path('results/dev_aux/task2143')
class PolicyRows(Mapping):
 def __init__(self,rows,choices):self.base=rows;self.choices=choices
 def __getitem__(self,key):
  row=self.base[key];choice=self.choices.get(row['index'])
  return row if choice is None else dict(row,winning_action=choice)
 def __iter__(self):return iter(self.base)
 def __len__(self):return len(self.base)
class TeacherPolicyView:
 def __init__(self,teacher,choices):self.reference=teacher.reference;self.key=teacher.key;self.rows=PolicyRows(teacher.rows,choices)
def run():
 if (OUT/'started.json').exists():raise RuntimeError('one240cap neverrestart')
 start=time.perf_counter();deadline=start+240;stop=ParsedStopReader(Path.cwd());stop()
 def cancel():stop();return time.perf_counter()>=deadline
 (OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap_seconds=240)),encoding='utf-8')
 teacher=CanonicalTeacher('results/dev_aux/task2097','results/dev_aux/task2098','results/dev_aux/task2099');load=time.perf_counter()-start;rows={r['index']:r for r in teacher.rows.values()};choices={};counted=0
 @lru_cache(None)
 def cost(i):
  nonlocal counted
  counted+=1
  if counted%256==0 and cancel():raise TimeoutError('original240cap')
  r=rows[i];assert r['rank']is not None and r['label']!='DRAW'
  if r['rank']==0:assert not r['actions'];return 1
  if r['label']=='LOSS':
   assert r['actions']and all(rows[e['child']]['label']=='WIN'and rows[e['child']]['rank']<r['rank']for e in r['actions'])
   return 1+sum(cost(e['child'])for e in r['actions'])
  allowed=[e for e in r['actions']if rows[e['child']]['label']=='LOSS'and rows[e['child']]['rank']<r['rank']]
  assert allowed
  best=min(allowed,key=lambda e:(cost(e['child']),e['action']))
  choices[i]=best['action'];return 1+cost(best['child'])
 inputs=json.loads(Path('results/dev_aux/task2100/inputs.json').read_text(encoding='utf-8'))['roots'];lookup={r['family']:r for r in(json.loads(x)for x in Path('results/dev_aux/task2126/queries-corrected.jsonl').read_text(encoding='utf-8').splitlines())if r['kind']=='INITIAL'and r['depth']==2};cases=[]
 for f in(12,30,11):
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[f]['rules']).read_text(encoding='utf-8')));s=GameSession(c);legal={uci(a):a for a in s.legal_actions()}
  local=[('ROOT_OWN_WIN',s,0)]if f==11 else[(a,copy(s),1)for a in lookup[f]['regions'][0]['top_actions']]
  for name,child,target in local:
   if f!=11:child.submit(legal[name])
   row=teacher.rows[teacher.key(actor_state(child.state))];v={'WIN':1,'DRAW':0,'LOSS':-1}[row['label']];v=v if child.state.position.side_to_move==target else-v
   cases.append((f,name,child,target,v,None if v!=1 else cost(row['index'])))
 dp_seconds=time.perf_counter()-start-load;view=TeacherPolicyView(teacher,choices);provider=RankCertificateProvider(view)
 (OUT/'policy-before-probes.json').write_text(json.dumps(dict(DP_states=counted,choices={str(k):v for k,v in choices.items()},cases=[dict(family=f,action=a,target=t,value=v,min_rank_decreasing_tree_nodes=n)for f,a,s,t,v,n in cases],source_scope='Choices frozen before any budgetedproofqueries; no price/outcomes.',teacher_load_seconds=load,DP_seconds=dp_seconds),indent=2),encoding='utf-8')
 results=[];certs=[]
 for f,name,s,target,v,n in cases:
  if cancel():raise TimeoutError('original240cap')
  r=provider(s,target=target,max_nodes=1024,seconds=1.5,max_depth=64,cancel=cancel)
  out=dict(family=f,action=name,target=target,min_rank_decreasing_tree_nodes=n,status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds)
  if r.status=='PROVEN_WIN':
   vr=verify_session_certificate(s,r.certificate,max_nodes=16384,seconds=3.,cancel=cancel);assert vr['verified'];cursor=SessionStrategyCursor(s,r.certificate,max_nodes=16384,seconds=3.,cancel=cancel);played=copy(s);moves=[]
   while played.result.status is SessionStatus.ONGOING:
    if cancel():raise TimeoutError('original240cap')
    choice=cursor.choose(played)if played.state.position.side_to_move==target else max(cursor.node.edges,key=lambda e:e[1].rank)[0]
    cursor.commit(played,choice);moves.append(uci(choice.action))
   assert played.result.winner==target
   out.update(verified=vr,actual_terminal=dict(status=played.result.status.value,winner=played.result.winner,moves=len(moves)))
   certs.append(dict(family=f,action=name,target=target,rules=inputs[f]['rules'],root_record=json.loads(serialize_game_record(s.to_record())),tree=encode(r.certificate.tree),actual_record=json.loads(serialize_game_record(played.to_record()))))
  results.append(out)
 out=dict(status='COMPLETE_RANK_PRESERVING_SIZE_POLICY_PROBES',queries=results,teacher_load_seconds=load,DP_seconds=dp_seconds,DP_states=counted,seconds=time.perf_counter()-start,verified_actual_mates=len(certs),scope='New price-independent researchpolicy diagnostic, NOT unchanged2139player orfreecost. Min overstrictlyrank-decreasingchoices only; notminimumallstrategies. Actualverifier andfullhistory remainrequired.')
 (OUT/'certificates.json').write_text(json.dumps(certs,indent=2),encoding='utf-8');(OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':run()
