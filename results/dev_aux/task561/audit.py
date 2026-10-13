import json,re,time
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task561';start=time.perf_counter();F=R/'results/dev_aux/task529';gs=[json.loads(x) for x in (F/'games.jsonl').open()]
semq=lambda q:{k:([' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k not in ['seconds','transport','transport_costs']}
semg=lambda g:{k:([semq(q) for q in v] if k=='queries' else v) for k,v in g.items() if k not in ['seconds','transport']}
pairs=[]
for i in range(0,len(gs),2):
 assert semg(gs[i])==semg(gs[i+1]);pairs.append(dict(case=i//2,non_time_equal=True,game_seconds={g['transport']:g['seconds'] for g in gs[i:i+2]},go=len(gs[i]['queries'])))
out=dict(status='PASS_RETAINED_FIRST8',actual_new_go=0,first_attempt_complete_games=len(gs),pairs=pairs,orphan_queries_retained=10,scope='Supplementfirst4transportpairs whoseouterstartup/ACK arrays were lostbeforeoriginalNameError; allretainednon-time rawgame/query outputs equal. Per-game timerretained; no fabricatedstartup/table/normalwholebatchsuccess. Final28pairsremainoriginal529 result.',seconds=time.perf_counter()-start);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
