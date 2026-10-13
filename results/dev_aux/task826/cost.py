import json,re,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task826';rows=[]
for n in [787,791,797,804,814,819]:
 p=R/f'results/dev_aux/task{n}'
 if not (p/'result.json').exists():continue
 r=json.loads((p/'result.json').read_bytes());queries=declared=reported=no_counter=above=0;searchwall=max_ratio=0
 for line in (p/'queries.jsonl').open(encoding='utf-8'):
  q=json.loads(line);queries+=1;lim=q['nodes_limit'];declared+=lim;vals=[int(x) for s in q['lines'] for x in re.findall(r'\bnodes (\d+)',s)];searchwall+=q['seconds']
  if not vals:no_counter+=1;continue
  v=max(vals);reported+=v;above+=v>lim;max_ratio=max(max_ratio,v/lim)
 assert queries==r['actual_go'];rows.append(dict(task=n,actual_closed_games=r['actual_games'],actual_go=queries,declared_node_allowance_sum=declared,reported_info_node_sum=reported,queries_missing_info_node_counter=no_counter,queries_reported_over_limit=above,maximum_reported_to_requested_ratio=max_ratio,recorded_query_search_seconds_sum=searchwall,recorded_producer_seconds=r['seconds'],cached_cells=r.get('cached_cells',r.get('cached_physical_cells',0)),source_queries_sha256=hashlib.sha256((p/'queries.jsonl').read_bytes()).hexdigest()))
out=dict(status='ACTUAL_INFO_NODE_AND_COST_COMPONENTS',rows=rows,scope='Eachphysicalquery once. Summaxreportedinfo nodes pergo isreportedwork, notprimitive/exactallnodes ifmissingcounter. Requestedallowances distinct. Queryseconds excludescontroller/setup/PVvalidation/audit/communication; wallsinclude thempartly. Cachedcells notphysical. Ordinaryconcurrency,noexclusivity/equaltime/noisefree speedup claim. Finaltable afterALLclosed.');name='result.json' if len(rows)==6 else 'partial_before_G_or_probe.json';(O/name).write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(rows))
