import json,math,statistics,time,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task466';t=time.perf_counter();specs=[(431,432,'budget1024'),(431,433,'budget8192'),(438,439,'mixed'),(438,440,'terminal_only'),(445,449,'terminal_only_fresh'),(445,450,'fast_terminal'),(456,457,'few4'),(456,458,'wide16')];axes=[2,3,4,5,6,7,9,10,11,12,13,14];ref=[0,90,315,405,495,855,990,540,0,540,540,540,540,945,1395,0];rows=[];freeze=[]
for prep in [431,438,445,456]:
 f=R/f'results/dev_aux/task{prep}/all_endpoints_frozen.json';freeze.append(dict(path=f.relative_to(R).as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),record=json.loads(f.read_text(encoding='utf-8'))))
for prep,task,arm in specs:
 p=R/f'results/dev_aux/task{task}/endpoints.json';e=json.loads(p.read_text(encoding='utf-8'));assert e['frozen_before_development']
 for x in e['endpoints']:
  out=dict(task=task,arm=arm,family=x['family'],initial=x['initial'],endpoint=x['endpoint'],source_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
  for phase in ['initial','endpoint']:
   w=x[phase];out[phase+'_log_ratio_MSE_to_source_prior']=statistics.mean(math.log(w[i]/ref[i])**2 for i in axes);out[phase+'_strict_reference_order_reversals']=sum(w[a]>w[b] for a in axes for b in axes if ref[a]<ref[b]);out[phase+'_strict_reference_order_concordant']=sum(w[a]<w[b] for a in axes for b in axes if ref[a]<ref[b]);out[phase+'_candidate_ties_on_strict_reference_pairs']=sum(w[a]==w[b] for a in axes for b in axes if ref[a]<ref[b])
  rows.append(out)
out=dict(status='PASS_DESCRIPTIVE',reference=dict(prices=ref,source='evaluate.h fixed c1b80eaa officialYaneuraou AperyWCSC26 materialenum; NOTindependenthumanconsensus',purpose='descriptiveONLY afterALL28fitendpoints anddevelopmentalreadyfrozen; neveroptimizer/selector/stopping/root/horizoncontrol'),axes=axes,all_study_freeze_records=freeze,rows=rows,new_go=0,seconds=time.perf_counter()-t,scope='16ALLinitial/endpoint descriptors, including unchangedaliases; orderties countedas nonreversed, not agreementproof. Cost/trueterminaltransfer remainseparate. No Stockfish/Chess or generic-rule learning claim.');assert not(O/'result.json').exists();(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([{k:v for k,v in x.items() if k not in ['source_sha256','initial','endpoint']} for x in rows]))
