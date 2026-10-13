import json,re,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task711';rows=[]
for task in [686,687,695,696,701,709]:
 p=R/f'results/dev_aux/task{task}';assert (p/'result.json').exists();games=go=nodes=late_go=late_nodes=0;game_seconds=0;overshoot=0;max_nodes=0
 for text in (p/'games.jsonl').open(encoding='utf-8'):
  g=json.loads(text);games+=1;game_seconds+=g['seconds']
  for q in g['queries']:
   lines=[l for l in q['lines'] if re.search(r'\bnodes \d+',l)];assert lines;actual=int(re.search(r'\bnodes (\d+)',lines[-1])[1]);nodes+=actual;go+=1;max_nodes=max(max_nodes,actual);overshoot+=actual>1024
   if q['ply']>=12:late_go+=1;late_nodes+=actual
 result=json.loads((p/'result.json').read_bytes());assert games==result.get('actual_games') and go==result.get('actual_go');rows.append(dict(task=task,actual_games=games,actual_go=go,reported_nodes=nodes,queries_over1024=overshoot,max_reported_query_nodes=max_nodes,recorded_game_seconds=game_seconds,H12_or_absorbing_prefix_go=go-late_go,H12_prefix_reported_nodes=nodes-late_nodes,after12_go=late_go,after12_reported_nodes=late_nodes,source_sha256=hashlib.sha256((p/'games.jsonl').read_bytes()).hexdigest()))
producer=[dict(stage=n,whole_batch_seconds=json.loads((R/f'results/dev_aux/task{n}/result.json').read_bytes())['seconds']) for n in [687,696,701,709]]
out=dict(status='ALL_CURRENT_PHYSICAL_WORK_COSTS_COUNTED',rows=rows,producer_walls=producer,total_games=sum(r['actual_games'] for r in rows),total_go=sum(r['actual_go'] for r in rows),total_reported_nodes=sum(r['reported_nodes'] for r in rows),producer_component_seconds=sum(x['whole_batch_seconds'] for x in producer),cached686_cells_Bfit=json.loads((R/'results/dev_aux/task695/result.json').read_bytes())['cached_cells'],new_go=0,scope='Onlyactuallynewphysicalgames686687695696701709; cachedB686notdoublecounted. Perquerylastreportednodes includes1024overshoot, node countsnotprimitivecost. Wholeproducerwall includessetup/ACK/gamecalls/durablejournal overhead; no duplicatedfitwall+devcumwall. Audit/engineering/token/archive overhead additional, notexcludedinclaimedendtoendtime. After12 workload givespotentialB-H12-onlytruncation saving, NOTA-goal equivalence oractualoptimizedfitwall;128709realcap12controls qualified710, notalltrainingcaller proof. Ordinaryconcurrentload/descriptive timers, noexclusive speedup/equal-time methodcausalclaim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
