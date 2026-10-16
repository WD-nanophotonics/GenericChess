from pathlib import Path
from copy import copy
from collections import Counter
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_session_win_proof import verify_session_certificate
from results.dev_aux.task2048.portable_certificate import encode
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2086.rank_certificate import RankCertificateProvider
from results.dev_aux.task2091.history_rank import HistoryCheckedRankProvider
OUT=Path('results/dev_aux/task2091')
def write(n,obj):(OUT/n).write_text(json.dumps(obj,indent=2),encoding='utf-8')
def main():
 if (OUT/'started.json').exists():raise RuntimeError('no restart')
 start=time.perf_counter();deadline=start+120;write('started.json',dict(cap_seconds=120,one_clock=True,started_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()));actor=RoyalActor(4);roots=json.loads(Path('results/dev_aux/task2087/inputs.json').read_text(encoding='utf-8'))['roots'];cases=[];sessions={}
 for root in roots:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text(encoding='utf-8')));s=GameSession(c);raw=actor_state(s.state)
  def cycle(current,path):
   if time.perf_counter()>=deadline:raise TimeoutError('original120cap')
   if len(path)==4:return path if current==raw else None
   for name,child in actor.moves(current):
    found=cycle(child,path+[name])
    if found:return found
  path=cycle(raw,[])
  if path:
   for name in path:s.submit({uci(a):a for a in s.legal_actions()}[name])
   assert actor_state(s.state)==raw and max(n for _,n in s.state.repetition_counts)==2 and s.result.status is SessionStatus.ONGOING;sessions[root['family']]=s
  cases.append(dict(family=root['family'],rules=root['rules'],cycle=path,root_record=None if not path else json.loads(serialize_game_record(s.to_record()))))
 write('inputs.json',cases)
 teacher=CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2073','results/dev_aux/task2074');providers={'old':RankCertificateProvider(teacher),'history_checked':HistoryCheckedRankProvider(teacher)};rows=[];certs=[]
 with (OUT/'queries.jsonl').open('x',encoding='utf-8')as f:
  for case in cases:
   if not case['cycle']:continue
   for target in(0,1):
    for name in('old','history_checked'):
     if time.perf_counter()>=deadline:break
     s=sessions[case['family']];before=s.to_record();r=providers[name](s,target=target,max_nodes=1024,seconds=min(1.5,max(0.,deadline-time.perf_counter())),max_depth=64,cancel=lambda:time.perf_counter()>=deadline);row=dict(family=case['family'],target=target,provider=name,status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,verified=None)
     if r.certificate:
      row['verified']=verify_session_certificate(s,r.certificate,max_nodes=16384,seconds=min(.5,max(0.,deadline-time.perf_counter())));assert row['verified']['verified'];certs.append(dict(query=len(rows),rules=case['rules'],root_record=case['root_record'],target=target,tree=encode(r.certificate.tree)))
     assert s.to_record()==before;rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
 write('certificates.json',certs)
 write('result.json',dict(status='COMPLETE'if time.perf_counter()<deadline else'GLOBAL_CAP',roots=len(cases),cycles=sum(bool(c['cycle'])for c in cases),queries=len(rows),expected_queries=sum(bool(c['cycle'])for c in cases)*4,providers={n:dict(status=dict(Counter(r['status']for r in rows if r['provider']==n)),reasons=dict(Counter(r['reason']for r in rows if r['provider']==n)),nodes=sum(r['nodes']for r in rows if r['provider']==n))for n in providers},verified=len(certs),seconds=time.perf_counter()-start,scope='Oldcoarseguardvsactualfullhistorytree, noactualpolicyadoption orarbitraryhistoryWDLclaim. Allactualdrawdefenses abortUNKNOWN.'))
 print((OUT/'result.json').read_text(encoding='utf-8'))
if __name__=='__main__':main()
