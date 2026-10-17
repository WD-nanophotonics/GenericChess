from pathlib import Path
import json,hashlib,zipfile,time
from fractions import Fraction
from collections import Counter,defaultdict
D=Path('results/dev_aux/task2533')
def run():
 began=time.perf_counter();archive=Path('results/dev_aux/DELTA_REPRO_20261017_90.zip');ash=hashlib.sha256(archive.read_bytes()).hexdigest();assert ash=='c682ab793866421f014c3b81ec730747265ffca26cba78449d1aecee787d55a0';basis=defaultdict(dict);counts=defaultdict(Counter);first={};drifts=defaultdict(list)
 with zipfile.ZipFile(archive)as z:
  manifest=json.loads(z.read('MANIFEST_20261017_90.json'))['files']
  for name in('results/dev_aux/task2527/queries.jsonl','results/dev_aux/task2527/episodes.jsonl'):
   h=hashlib.sha256()
   with z.open(name)as inp:
    for raw in inp:
     h.update(raw);r=json.loads(raw);gs=r['generator_seed']
     if name.endswith('episodes.jsonl'):
      delta=(r['weights'][3]-r['weights'][1])-(r['initial_weights'][3]-r['initial_weights'][1]);drifts[gs].append(delta);continue
     counts[gs]['all_queries']+=1
     if not r['complete']:counts[gs]['incomplete']+=1;continue
     if r['pv_terminal']:counts[gs]['terminal_PV_constants']+=1;continue
     v=r['pv_phi'][1:];assert len(v)==5 and all(int(x)==x for x in v);v=tuple(map(int,v));counts[gs]['ordinary_PV_leaves']+=1;counts[gs]['ordinary_zero_vector']+=not any(v)
     if v[0]!=v[2]:
      counts[gs]['boardA_handA_inequality_leaves']+=1
      if gs not in first:first[gs]=dict(seed=r['seed'],game=r['game'],ply=r['ply'],free_phi=v,source_total_nodes=r['total_nodes'])
     w=list(map(Fraction,v))
     for pivot,b in sorted(basis[gs].items()):
      c=w[pivot];w=[x-c*y for x,y in zip(w,b)]
     pivot=next((i for i,x in enumerate(w)if x),None)
     if pivot is not None:
      c=w[pivot];w=[x/c for x in w]
      for j,b in list(basis[gs].items()):
       c=b[pivot];basis[gs][j]=[x-c*y for x,y in zip(b,w)]
      basis[gs][pivot]=w
   assert h.hexdigest()==manifest[name]['sha256'],name
 rows=[dict(generator_seed=gs,exact_rational_free_PV_rank=len(basis[gs]),counts=dict(counts[gs]),first_old_null_breaking_leaf=first.get(gs),episodes=len(drifts[gs]),episodes_with_null_component_drift_gt_1e_12=sum(abs(x)>1e-12 for x in drifts[gs]),max_abs_episode_null_component_drift=max(map(abs,drifts[gs])))for gs in sorted(counts)]
 out=dict(status='PASS_CLOSED90_EXACT_LEAF_SPAN_AND_OLD_NULL_COUNTERCHECK',input_source_sha='6ab620e7423cfe01b64f28a8b030ab998f635cc1',archive_sha256=ash,old_primary_report_sha='0ca265c711f55514b10ac06638b6934b159a81fc',old_report_bytes_sha256='a08ad5d4ff80eb5637dbb8a26d64d779691585d471f37a4e0c7c1436658944d9',old_evidence='PRIMARYreported89ordinaryPVranks5/4/5/4; boardA=handAon2/4 was DATAcondition, notruleinvariant. ReportREADonlyhere/noPRIMARYNativeexecution.',free_coordinate_order=['boardA','boardX','handA','handP','handX'],rows=rows,scope='Postsource/pre-FINISHclosed-dataSUPPLEMENT, NOTinsideimmutable35thZIP. ReadsONLYpublicarchive withrawmemberhashes, exactFractionrank/noCore/search/newfitness/training. New90differsfrom89 inTRAINstreams/initials/work/H, notpuresamplesizeablation. Breakingoldleaf-null relation/refinedrankdoesNOTprovepriceidentifiability, uniqueoptimum/strength orfullrule-domain; notnewgate. Currentfloatresultsunchanged; NativequantizationconclusionsremainPRIMARYownerreportedonly/old8models/no90deployment/defaultadoption.',seconds=time.perf_counter()-began);(D/'leaf-span.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
