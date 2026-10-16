"""Bounded actual-rule two-N capability witnesses, not training or validation."""
from pathlib import Path
from dataclasses import replace
from copy import copy
import json,random,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from results.dev_aux.task2148.normal import SessionCompleteMaterialSearch
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2244')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):
 with(OUT/n).open('x')as f:json.dump(v,f,indent=2)
def freeze():
 assert not(OUT/'plan.json').exists();rng=random.Random(202610167744);rs=deserialize_ruleset(Path('results/dev_aux/task2214/rules.json').read_text());roots=[];seen=set();attempts=0;start=time.perf_counter();stop=EvidenceStopReader(Path.cwd())
 while len(roots)<32 and attempts<4096:
  stop();assert time.perf_counter()-start<180;attempts+=1;places=rng.sample(range(16),6);board=[None]*16
  for square,(owner,kind)in zip(places,[(0,'K'),(1,'K'),(0,'R'),(1,'R'),(1,'N'),(1,'N')]):board[square]=Piece(owner,kind,kind)
  ident=tuple('.'if pc is None else pc.current_type_id.lower()if pc.owner else pc.current_type_id for pc in board)
  if ident in seen:continue
  try:c=compile_ruleset_for_execution(replace(rs,initial_position=tuple(tuple(board[i:i+4])for i in range(0,16,4)),initial_setup_options=()));s=GameSession(c)
  except ValueError:continue
  if s.result.status is not SessionStatus.ONGOING:continue
  terminal=False
  for action in s.legal_actions():
   child=copy(s);child.submit(action)
   if child.result.status is not SessionStatus.ONGOING:terminal=True;break
  if terminal:continue
  seen.add(ident);family=len(roots);name=OUT/f'root-{family}.json';name.write_text(serialize_ruleset(c.ruleset)if hasattr(c,'ruleset')else serialize_ruleset(replace(rs,initial_position=tuple(tuple(board[i:i+4])for i in range(0,16,4)),initial_setup_options=())))
  roots.append(dict(family=family,rules=str(name),rules_sha=sha(name),board=ident))
 assert len(roots)==32
 save('plan.json',dict(roots=roots,seed=202610167744,attempts=attempts,prices=[1.25,2.,4.],depth=3,nodes=20000,seconds=3.,one_cap_seconds=300,source_sha=sha(OUT/'counterexample.py'),selection='First32compiler-validnonterminal/nooneplyterminal randomsixactorK+RvsK+R+2N roots beforeANYpricequery. This is exposedmechanismwitness search, notWDLtraining/holdout. Keepallfailed/partialslots.',question='Can a secondN realize anactualprice-sensitiveD3choiceinsideformerlyequivalentx>1class? No newteacherneeded; changedinventorypurecapabilityquestion.',scope='Onlyactualnormalfinite-depthdecisions, notactualW-L/usefulness/priceoptimality. Missing/full-depthfailures retained; neverpickwitnessasvalidation. No source/default/PRIMARYchanges.'))
 print('FROZEN32TWO_N_CAPABILITY_ROOTS',attempts)
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());assert sha(OUT/'counterexample.py')==p['source_sha'];save('started.json',dict(plan_sha=sha(OUT/'plan.json')));start=time.perf_counter();deadline=start+p['one_cap_seconds'];stop=EvidenceStopReader(Path.cwd());rows=[];status='COMPLETE'
 def cancel():stop();return time.perf_counter()>=deadline
 for root in p['roots']:
  for ratio in p['prices']:
   if cancel():status='PARTIAL_GLOBAL_CAP';break
   assert sha(root['rules'])==root['rules_sha'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession(c)
   def ev(pos,target):return sum((1 if pc.owner==target else-1)*(ratio if pc.current_type_id=='R'else 1.)for pc in pos.board if pc is not None and pc.current_type_id!='K')
   r=SessionCompleteMaterialSearch(c,ev,max_depth=p['depth']).choose(s,max_nodes=p['nodes'],seconds=min(p['seconds'],max(0.,deadline-time.perf_counter())),cancel=cancel);row=dict(family=root['family'],ratio=ratio,choice=choice_value(r.choice),score=str(r.score),completed_depth=r.completed_depth,nodes=r.nodes,exit_cause=r.exit_cause,seconds=r.seconds);rows.append(row)
   with(OUT/'queries.jsonl').open('a')as f:f.write(json.dumps(row)+'\n')
  if status!='COMPLETE':break
 pairs=[]
 for root in p['roots']:
  rr={r['ratio']:r for r in rows if r['family']==root['family']}
  if all(x in rr and rr[x]['completed_depth']==3 for x in(1.25,4.)):pairs.append(dict(family=root['family'],different_choice=rr[1.25]['choice']!=rr[4.]['choice'],low=rr[1.25],high=rr[4.]))
 save('result.json',dict(status=status,queries=len(rows),expected=96,missing=96-len(rows),fully_completed_1p25_vs4_pairs=len(pairs),different_choice_witnesses=sum(r['different_choice']for r in pairs),pairs=pairs,seconds=time.perf_counter()-start,scope=p['scope']));print(json.dumps(dict(status=status,queries=len(rows),fullpairs=len(pairs),different=sum(r['different_choice']for r in pairs),seconds=time.perf_counter()-start)))
if __name__=='__main__':import sys;{'freeze':freeze,'run':run}[sys.argv[1]]()
