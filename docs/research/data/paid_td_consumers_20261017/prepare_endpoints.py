from pathlib import Path
import json,sys,hashlib
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
D=R/'.local_agent/paid-td-20261017';O=D/'exact/results/dev_aux';train=json.loads((O/'task2539/result.json').read_bytes());arms={(a['generator_seed'],a['method'],a['seed']):a for a in train['arms']};chosen={};channels={}
for line in (O/'task2540/games.jsonl').open():
 g=json.loads(line);channels[g['generator_seed']]=g['channels']
for line in (O/'task2540/queries.jsonl').open():
 q=json.loads(line);g,seed,family,color,method,foe=q['slot']
 if method not in ['TD','WDL']or not q['complete']or len(q['record_before']['actions'])%2!=color:continue
 key=g,method,seed,color,foe
 if key in chosen:continue
 assert q['weights']==arms[g,method,seed]['weights']
 chosen[key]=dict(rule=g,method=method,seed=seed,color=color,foe=foe,family=family,channels=channels[g],query=q)
assert len(chosen)==128
write_json(D/'endpoint-plan.json',dict(question='Can current standard checkpoints/Native serve newly ACTUALLY LEARNED negative-P92 endpoints without pinning or a new API?',changed_premise='All91endpointP werepositive; actual92has4/16TDnegativeP endpoints, WDLsamefree6control. No policy-cone extension to negatives and no Psigncausalbenefitclaim.',source_sha='3792d83068d5d0e61a0a33ebbf6850b414202c6f',selection='First sourcefile-order COMPLETEcandidate-turn EVALquery perALL32endpointmodels*2roles*2fixedfoes; skipnoongoingrootonlyuntilfirstactualquery, no outcome/gradient/marginselection. Candidateactor is fullrecordactionparity fromdeclaredside0initial; sameinput/sourceweightasserted.',limits=dict(global_seconds=120,core_visits=500000),expected_calls=128,decision='If existingconsumer preserves quantized/sourcefloat optima retainstandardAPI/rawsignedP; if actualdeviation recordlimitedprecision/targetcontractandassessdecisionrelevance, no automaticnewAPI/normalizer. Preserve absent sourceEVALPV/gradients, notzeros.',cost='Expected~10secondsNative+CoreunprunedD2, bounded120seconds; nofitness/training/AUXwrite/defaultchange.'))
write_json(D/'endpoint-inputs.json',dict(rows=list(chosen.values()),selected=128,models=32,negativePmodels=[list(k)for k,a in arms.items()if a['weights'][0]<0],source_EVAL_queries_sha256=hashlib.sha256((O/'task2540/queries.jsonl').read_bytes()).hexdigest()))
s=(R/'.local_agent/free-price-20261017/endpoint_consumer.py').read_text(encoding='utf-8-sig').replace('.local_agent/free-price-20261017','.local_agent/paid-td-20261017').replace("source=D/'exact/results/dev_aux/task2534'","source=D/'exact/results/dev_aux/task2525'")
s=s.replace('Actual91','Actual92').replace('actual91','actual92').replace('ACTUAL91','ACTUAL92')
(D/'endpoint_consumer.py').write_bytes(s.encode())
print('Registered first128actual92endpoint inputs,4negativePmodels retained')
