from pathlib import Path
import json,hashlib,time
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2171')
def run():
 if(OUT/'states.jsonl').exists():raise RuntimeError('newclosurealreadyfixed')
 start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());base=Path('results/dev_aux/task2108');extra=Path('results/dev_aux/task2170');p=json.loads((base/'plan.json').read_text(encoding='utf-8'));assert json.loads((extra/'result.json').read_text(encoding='utf-8'))['complete_inventory_and_all_edges'];p.update(inventories=p['inventories']+['Nn'],syntactic_positions=551520,parent_census=[str(base),str(extra)],scope='CompletecaptureclosureofALLsubsetsBNbn<=2nonroyalactors4x4. Original2108validsubsetreusedexactcanonicalrows; missingNn newCoreexecution2170. Retainparent593.562s+derivation9s+new17.081s, not freebuild/full6graph.');(OUT/'plan.json').write_text(json.dumps(p,indent=2),encoding='utf-8');h=hashlib.sha256();count=edges=0;digests={}
 with(OUT/'states.jsonl').open('xb')as f:
  for src in(base,extra):
   hh=hashlib.sha256();expected=json.loads((src/'result.json').read_text(encoding='utf-8'));assert expected['complete_inventory_and_all_edges']
   for raw in(src/'states.jsonl').open('rb'):
    if count%1024==0:
     stop()
     if time.perf_counter()-start>=60:raise TimeoutError('merge60cap')
    row=json.loads(raw);canonical=raw.rstrip(b'\r\n')+b'\n';hh.update(canonical);h.update(canonical);f.write(canonical);count+=1;edges+=len(row['children'])
   assert hh.hexdigest()==expected['records_sha'];digests[str(src)]=hh.hexdigest()
 result=dict(status='COMPLETE',complete_inventory_and_all_edges=True,processed=count,actual_legal_edges=edges,records_sha=h.hexdigest(),source_digests=digests,seconds=time.perf_counter()-start,scope=p['scope']);(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':run()
