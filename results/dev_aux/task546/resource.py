from pathlib import Path
import json,re,hashlib,time
R=Path.cwd();O=R/'results/dev_aux/task546';O.mkdir(exist_ok=True);tasks=[int(x) for x in __import__('sys').argv[1:]];outputs=[]
for task in tasks:
 dest=O/f'result_{task}.json';assert not dest.exists();folder=R/f'results/dev_aux/task{task}';ep=json.loads((folder/'endpoints.json').read_bytes());totals=dict(candidate_go=0,unit_go=0,reported_nodes=0,returned_depth_sum=0,query_seconds=0.,game_seconds=0.,plies=0,games=0);condition=json.loads((R/'results/dev_aux/task532/declaration.json').read_bytes());info=next(a for a in condition['fit_conditions'] if a['task']==task);hist={};f=folder/'games.jsonl';t0=time.perf_counter()
 for line in f.open(encoding='utf-8'):
  g=json.loads(line);totals['games']+=1;totals['game_seconds']+=g['seconds'];totals['plies']+=len(g['actions']);hist[g['termination']['kind']]=hist.get(g['termination']['kind'],0)+1
  for q in g['queries']:
   totals[q['player']+'_go']+=1;totals['query_seconds']+=q['seconds'];assert q['nodes_limit']==info['nodes'];lines=[s for s in q['lines'] if s.startswith('info ') and re.search(r'\bnodes \d+',s)];assert lines
   last=lines[-1];nodes=int(re.search(r'\bnodes (\d+)',last)[1]);depth=int(re.search(r'\bdepth (\d+)',last)[1]);totals['reported_nodes']+=nodes;totals['returned_depth_sum']+=depth
 out=dict(status='PASS_ACTUAL_RESOURCE_COUNTERS',task=task,condition=ep['arm'],nodes_perquery_limit=info['nodes'],opponent=info['opponent'],source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),totals=totals,fit_wall_seconds=ep['fit_seconds'],logical_games=ep['fit_logical_games'],exact_cache_hits=ep['fit_cache_hits'],terminations=hist,new_go=0,seconds=time.perf_counter()-t0,scope='ALLcompletedfit games/queryroles; reportedlastinfo nodes/depth areactualenginecounters, notconfiguredlimit multipliedbycount oruniformhorizon/warmbound proofs. Game/querysum differsbatch/startup/phase/native/serialization costs; noexclusiveCPU/causalpercent attribution.')
 dest.write_text(json.dumps(out,indent=2),encoding='utf-8');outputs.append({k:v for k,v in out.items() if k not in ['source_sha256']})
print(json.dumps(outputs))
