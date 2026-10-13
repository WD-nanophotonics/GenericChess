import json,re,time,itertools,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task603';O.mkdir(exist_ok=True);start=time.perf_counter();semq=lambda q:{k:([' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k!='seconds'};semg=lambda g:{k:([semq(q) for q in v] if k=='queries' else v) for k,v in g.items() if k!='seconds'};n=0;go=0
with (R/'results/dev_aux/task597/games.jsonl').open() as a,(R/'results/dev_aux/task598/games.jsonl').open() as b:
 for x,y in itertools.zip_longest(a,b):
  assert x is not None and y is not None;g=json.loads(x);h=json.loads(y);assert semg(g)==semg(h),n;n+=1;go+=len(g['queries'])
ea=json.loads((R/'results/dev_aux/task597/endpoints.json').read_bytes());eb=json.loads((R/'results/dev_aux/task598/endpoints.json').read_bytes());assert ea['endpoints']==eb['endpoints'];assert len(ea['updates'])==len(eb['updates'])==24
for a,b in zip(ea['updates'],eb['updates']):
 for k in ['family','iteration','direction','start_weights','selected_index','after_weights','changed_integer_axes']:assert a[k]==b[k]
 assert [c['weights'] for c in a['candidates']]==[c['weights'] for c in b['candidates']]
assert n==5200 and go==25373
out=dict(status='PASS_ALL_ACTUAL_OBJECTIVE_PAIRING',physical_game_pairs=n,go_pairs=go,all_non_time_queries_actions_material_history_identical=True,bothinitials12roundpaths_and_endpoints_equal=True,logical_models=4,distinct_endpoints=2,new_go=0,seconds=time.perf_counter()-start,scope='SAMEterminalrich12plytraining distribution andrandomdraws: addingquantitywhenunfinished produced identical24objective-pairedselectedupdates/twoendpoints/5200physicalpathpairs. Rewards differ but ALLchoices hereequal. Notuniversalobjectiveequivalence, newtraining or5200independentfamilies;8seedfamilies andbiasedgenerator. Timers excludedonlyseconds/time/nps; fullnodes/PV/warm/queryrole/readback retained.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))