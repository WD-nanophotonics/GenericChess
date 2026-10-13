import json,sys,time,hashlib,re
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task502';assert not(O/'result.json').exists();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task381'));import adapter as A;import run as G;import audit as V
D=R/'results/dev_aux/task495/declaration.json';d=json.loads(D.read_text(encoding='utf-8'));exes={'handSEE':R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe','fullCapture':R/'.local_agent/yaneura30/yaneura-material1-full-capture-futility.exe'};assert {k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in exes.items()}==d['executable_hashes'];decl=dict(declaration_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),inputs='ALLeligibletrainrootonly fullhistories/BOTH initialprices/BOTHengines/TWOcoldrepetitions',nodes=1024,expected_go=8*sum(f['phase']=='train' for f in d['roots']),expected_cost='under30s with120secondtotalfuse;oneproducer/no newgames/training',scope='finite cold determinism/legal/history/PV/table preflight; old/newSEE responses allowedtodiffer, not arbitraryprice/options qualification');(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8');t0=time.perf_counter();responses={};acks=[];pv=0;entries=0
for arm,exe in exes.items():
 A.EXE=exe;out=[]
 with (O/(arm+'_queries.jsonl')).open('w',encoding='utf-8') as qj:
  for profile in d['initial_profiles']:
   e=A.Engine(profile['weights'],qj);acks.append(dict(engine_arm=arm,weights=e.w,prices=e.prices));seen=[]
   for line in e.prices:
    if not line.startswith('info string auxprice '):continue
    pc,val,sgn,cap,prom=map(int,line.split()[3:]);pt=pc%16;base=pt-8 if pt in range(9,15) else pt;w=e.w;assert val==w[pt] and sgn==(w[pt] if pc<16 else -w[pt]) and cap==(0 if pt in (0,8,15) else w[pt]+w[base]) and prom==(w[base+8]-w[base] if base in range(1,7) else 0);seen.append(pc);entries+=1
   assert sorted(seen)==list(range(32))
   try:
    for root in [f for f in d['roots'] if f['phase']=='train']:
     pair=[]
     for repeat in range(2):
      G.stop();assert time.perf_counter()-t0<120;q=e.search(root['initial_sfen'],root['history'],1024);pv+=V.query(q);pair.append(q)
     out.append(dict(family=profile['name'],root_seed=root['seed'],queries=pair))
   finally:e.close()
 responses[arm]=out
sem=lambda q:{k:([ ' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k!='seconds'}
for out in responses.values():
 for row in out:assert sem(row['queries'][0])==sem(row['queries'][1]),'actual cold determinism failure; preserve evidence anddiagnose'
changed=sum(sem(a['queries'][0])!=sem(b['queries'][0]) for a,b in zip(responses['handSEE'],responses['fullCapture']));r=dict(status='PASS_PREFLIGHT',actual_go=8*sum(f['phase']=='train' for f in d['roots']),new_games=0,new_training=0,PV_move_checks=pv,fulltable_entries=entries,price_acks=acks,changed_cross_engine_response_groups=changed,source_rows=responses,seconds=time.perf_counter()-t0,scope=decl['scope']);(O/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print({k:v for k,v in r.items() if k not in ['source_rows','price_acks']})
