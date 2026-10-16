from pathlib import Path
import json,time,datetime,statistics,hashlib
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2393')
def run():
 assert not(OUT/'benchmark-started.json').exists();p=json.loads((OUT/'benchmark-plan.json').read_text());safety=SharedDeleteStopReader(Path.cwd());safety();t=time.perf_counter();(OUT/'benchmark-started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((OUT/'benchmark-plan.json').read_bytes()).hexdigest())));rows=[]
 with(OUT/'benchmark-measurements.jsonl').open('x')as out:
  for repeat in range(p['pairs']):
   for name in(('BASE','SHARED')if repeat%2==0 else('SHARED','BASE')):
    safety();r=(EvidenceStopReader if name=='BASE'else SharedDeleteStopReader)(Path.cwd());r();before=(r.reads,r.bytes_read);began=time.perf_counter()
    for _ in range(p['polls']):r()
    row=dict(repeat=repeat,arm=name,seconds=time.perf_counter()-began,reads=r.reads-before[0],bytes=r.bytes_read-before[1]);rows.append(row);out.write(json.dumps(row)+'\n');out.flush();safety()
   if time.perf_counter()-t>=p['cap_seconds']:raise TimeoutError('boundedfreshreadbenchmark')
 ratios=[next(r['seconds']for r in rows if r['repeat']==i and r['arm']=='SHARED')/next(r['seconds']for r in rows if r['repeat']==i and r['arm']=='BASE')for i in range(p['pairs'])];result=dict(status='COMPLETE_SAME_POLL_NATIVE_SHARING_COST',pairs=p['pairs'],polls=p['polls'],median_native_over_base=statistics.median(ratios),pair_ratios=ratios,identical_bytes_each_pair=all(len({r['bytes']for r in rows if r['repeat']==i})==1 for i in range(p['pairs'])),all_exact_poll_counts=all(r['reads']==6*p['polls']for r in rows),seconds=time.perf_counter()-t,scope=p['scope']);(OUT/'benchmark-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
