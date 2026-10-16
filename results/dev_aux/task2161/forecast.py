"""Next-panel input/work forecast only; no normal/WDL/fitness queries."""
from pathlib import Path
import json,time,hashlib
from scripts.generic_royal_actor import RoyalActor
from results.dev_aux.task2155.sample import literal_tree
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2161')
def run():
 if(OUT/'forecast.json').exists():raise RuntimeError('forecastalreadyfixed')
 start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());source=Path('results/dev_aux/task2158/inputs.json');roots=json.loads(source.read_text(encoding='utf-8'))['roots'][:32];actor=RoyalActor(3);rows=[]
 for r in roots:
  stop()
  if time.perf_counter()-start>=30:raise TimeoutError('one30countcap')
  nodes={}
  for depth in(1,2,3,4):t,n=literal_tree(actor,tuple(r['root']),depth);nodes[depth]=n
  rows.append(dict(family=r['family'],root=r['root'],rules=r['rules'],fingerprint=r['fingerprint'],fulltree_nodes={str(d):n for d,n in nodes.items()},iterative_upper={str(d):sum(nodes[k]for k in range(1,d+1))for d in(2,3,4)}))
 out=dict(status='INPUT_AND_WORK_FORECAST_ONLY_NEXT_CAPACITY_PANEL',question='Can completing deepermaterialsearch alter TRAIN rootchoicecapacity acrossallpricecells withoutanotherlearningbatch?',inputs_sha=hashlib.sha256(source.read_bytes()).hexdigest(),families=32,rows=rows,max_iterative_depth4=max(r['iterative_upper']['4']for r in rows),new_normal_or_proof_or_fitness_queries=0,seconds=time.perf_counter()-start,first_action='Nextsession freezeALL32TRAIN roots depths2/3/4, allpositivepricecells andindependentactualruletrees, noDEVrootchoice. ForecastdoesnotestablishWDLquality orsearchtiming.',publication='DirectGitnext-inputaddendumAFTERbothimmutable73capsules; notinside11archive67testreceipt.')
 (OUT/'forecast.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items()if k!='rows'}))
if __name__=='__main__':run()
