import json,sys,time,hashlib,os
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task838';O.mkdir(exist_ok=False)
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
from warm_adapter import ControlledEngine
examples=json.loads((R/'results/dev_aux/task830/counterexample_inputs.json').read_bytes())['examples'];cases=[];seen=set()
for ex in examples:
 p=R/f"results/dev_aux/task{ex['source']['task']}/games.jsonl"
 with p.open(encoding='utf-8') as f:
  for i,l in enumerate(f,1):
   if i==ex['source']['line']:g=json.loads(l);break
 q=g['queries'][ex['query']];key=(q['initial_sfen'],tuple(q['history']),tuple(q['weights']))
 if key not in seen:seen.add(key);cases.append(dict(name='observed_'+str(len(cases)),initial_sfen=q['initial_sfen'],history=q['history'],weights=q['weights'],source=ex))
assert len(cases)==2
profiles=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes())['initial_profiles'];roots=json.loads((R/'results/dev_aux/task784/roots_frozen.json').read_bytes())['roots']
for pi,p in enumerate(profiles):
 for f in roots[:6 if pi==0 else 8]:cases.append(dict(name=p['name']+'_'+str(f['source_family']),initial_sfen=f['initial_sfen'],history=f['history'],weights=p['weights'],source_family=f['source_family']))
assert len(cases)==16
plan=dict(status='FROZEN_BEFORE_ANY_QUERY',cases=cases,budgets=[256,1024],query_count_per_executable=32,executables=['original','trace'],reset_policy='cold_per_query',scope='16fixedpositions eightunit/eightrandom, historicaltwoqueries plus firstsix/eightinitialroots; bothbudgets. Original/trace paired once each. Notoldwarmreproduction, no pricefit, no leafgradient guarantee; max300seconds.')
(O/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');t=time.monotonic();records=[]
with (O/'queries.jsonl').open('w',encoding='utf-8') as journal:
 for ci,c in enumerate(cases):
  for budget in plan['budgets']:
   for mode,exe in [('original',R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe'),('trace',R/'.local_agent/provenance38/trace.exe')]:
    assert time.monotonic()-t<300;A.EXE=exe;e=ControlledEngine(c['weights'],None,'cold_per_query')
    try:q=e.search(c['initial_sfen'],c['history'],budget);A.validate_search(q);q.update(case_index=ci,mode=mode,executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),price_ack=e.prices);journal.write(json.dumps(q)+'\n');journal.flush();os.fsync(journal.fileno());records.append(q)
    finally:e.close()
 print('CLOSED',len(records),'queries',round(time.monotonic()-t,3),flush=True)
(O/'result.json').write_text(json.dumps(dict(status='ALL64_DIAGNOSTIC_QUERIES_CLOSED',actual_go=len(records),seconds=time.monotonic()-t,scope=plan['scope']),indent=2),encoding='utf-8')
