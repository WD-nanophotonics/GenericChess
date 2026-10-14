from pathlib import Path
import json,importlib.util,copy,types
R=Path.cwd();O=R/'results/dev_aux/task1371';O.mkdir()
spec=importlib.util.spec_from_file_location('runner45',R/'results/dev_aux/task1368/runner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
d=json.loads((R/'results/dev_aux/task1368/smoke.json').read_bytes());checks=[]
for field,value in [('max_train_seconds',360),('max_dev_seconds',360),('prices_by_arm',{'L':[720]}),('expected_games',17),('root_count',3),('binary_sha256','0'*64),('root_sha256','0'*64)]:
 q=copy.deepcopy(d);q[field]=value
 try:m.validate(q)
 except ValueError as e:checks.append(dict(field=field,rejected=str(e)))
 else:raise AssertionError('observed manifest boundary not rejected:'+field)
# Observed cleanup placement error: first closer failing must not skip the teacher.
class Bad:
 def close(self):raise RuntimeError('controlled close fault')
class Good:
 closed=False
 def close(self):self.closed=True
g=Good()
try:m.close_all([Bad(),g])
except RuntimeError:pass
assert g.closed;checks.append(dict(check='teacher closed even first closer fails'))
# Exercise a producer search fault after both owned engines were constructed.
engines=[]
class Engine:
 def __init__(self):self.closed=False;self.backend='controlled_fake_transport';self.last='';self.p=types.SimpleNamespace(poll=lambda:0 if self.closed else None);engines.append(self)
 def send(self,s):self.last=s
 def ready(self):
  if self.last.startswith('devauxleafr '):return ['info string DEV_AUX leafR 720 nativeR 720 captureR 720']
  if self.last=='eval':return ['Final evaluation 3.46']
  return []
 def close(self):self.closed=True
m.runtime=lambda:types.SimpleNamespace(M=types.SimpleNamespace(start=lambda *a:Engine()),A=types.SimpleNamespace(guard=lambda *a:None),stop=lambda:None)
m.config5=lambda *a:dict(controlled_fake=True)
def fail(*args):raise RuntimeError('controlled search fault after teacher start')
m.search=fail
test=copy.deepcopy(d);test['profiles']={'B':dict(nativeR=720,leafR=720)};test['expected_games']=8
(O/'fault-plan.json').write_text(json.dumps(test))
out=m.execute('results/dev_aux/task1371/fault-plan.json','results/dev_aux/task1371/fault-output')
assert not out['complete'] and out['closed_games']==0 and len(engines)==2 and all(e.closed for e in engines) and out['all_owned_engines_closed']
checks.append(dict(check='producer failure closes candidate and teacher',closed=len(engines),new_actual_go=0))
# Actual 16 smoke trajectories must be exactly the existing source cases.
old=[json.loads(s) for s in (R/'results/dev_aux/task1346/games.jsonl').read_text().splitlines()];new=[json.loads(s) for s in (R/'results/dev_aux/task1367/games.jsonl').read_text().splitlines()]
lookup={g['game']:g for g in old}
for g in new:
 x=lookup[g['game']]
 for k in ['root','actions','weights','termination','final_fen','label','nativeR','leafR','price','color','opponent']:assert g[k]==x[k]
 for q,z in zip(g['queries'],x['queries']):
  assert {k:v for k,v in q.items() if k!='metadata'}=={k:v for k,v in z.items() if k!='metadata'}
  for k in ['root_fen5','root_fen8','full_history','command']:assert q['metadata'][k]==z['metadata'][k]
assert len(new)==16 and json.loads((R/'results/dev_aux/task1367/result.json').read_bytes())['all_owned_engines_closed']
checks.append(dict(check='actual16 manifest smoke reproduces full source trajectories',physical_go=249,not_new_science=True))
(O/'result.json').write_text(json.dumps(dict(status='PASS_OBSERVED_BUDGET_INPUT_AND_CLEANUP_REGRESSIONS_PLUS_ACTUAL16_CONTROLS',checks=checks,scope='Fake transport is explicit failure-path regression only; science comes from actual152..? separate producers; no mock substitutes learning'),indent=2));print('REGRESSION',len(checks),'PASS')
