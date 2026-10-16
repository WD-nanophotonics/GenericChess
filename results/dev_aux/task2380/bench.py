from pathlib import Path
import json,time,hashlib,datetime,statistics
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
from results.dev_aux.task2379.reader import FreshFileIOStopReader
OUT=Path('results/dev_aux/task2380')
def run():
 p=json.loads((OUT/'plan.json').read_text());assert not(OUT/'started.json').exists();assert hashlib.sha256(Path('results/dev_aux/task2379/reader.py').read_bytes()).hexdigest()==p['candidate_sha'];safety=EvidenceStopReader(Path.cwd());safety();began=time.perf_counter();rows=[];classes={'BASE':EvidenceStopReader,'FILEIO':FreshFileIOStopReader};(OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest())))
 with(OUT/'measurements.jsonl').open('x')as f:
  for repeat in range(p['pairs']):
   for arm in(('BASE','FILEIO')if repeat%2==0 else('FILEIO','BASE')):
    safety();r=classes[arm](Path.cwd());r();before=(r.reads,r.bytes_read,r.parses);start=time.perf_counter()
    for i in range(p['polls_per_measurement']):r()
    dt=time.perf_counter()-start;safety();row=dict(repeat=repeat,arm=arm,seconds=dt,reads=r.reads-before[0],bytes_read=r.bytes_read-before[1],parses=r.parses-before[2]);assert row['reads']==6*p['polls_per_measurement'];rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
   if time.perf_counter()-began>p['one_cap_seconds']:raise TimeoutError('registeredactualhostmicrocap')
 ratios=[next(r['seconds']for r in rows if r['repeat']==i and r['arm']=='FILEIO')/next(r['seconds']for r in rows if r['repeat']==i and r['arm']=='BASE')for i in range(p['pairs'])]
 result=dict(status='COMPLETE_FRESH_READ_MICROBENCH',pairs=p['pairs'],polls_per_measurement=p['polls_per_measurement'],median_candidate_over_base=statistics.median(ratios),candidate_over_base_ratios=ratios,total_seconds_by_arm={a:sum(r['seconds']for r in rows if r['arm']==a)for a in classes},candidate_faster_pairs=sum(x<1 for x in ratios),same_bytes_per_pair=all(len({r['bytes_read']for r in rows if r['repeat']==i})==1 for i in range(p['pairs'])),seconds=time.perf_counter()-began,scope=p['scope']);(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
