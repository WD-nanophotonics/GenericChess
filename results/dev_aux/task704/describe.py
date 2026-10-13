import json,math,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task704'
for n in [688,697]:assert json.loads((R/f'results/dev_aux/task{n}/result.json').read_bytes())['status'].startswith('PASS_ALL_')
for n in [689,698]:assert json.loads((R/f'results/dev_aux/task{n}/score_table_frozen.json').read_bytes())['reference_read_here']==False
ref=json.loads((R/'results/dev_aux/task560/result.json').read_bytes())['source_prior'];axes=[2,3,4,5,6,7,9,10,11,12,13,14];rows=[]
for task,label in [(686,'mean12_24'),(695,'q12_only')]:
 for e in json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes())['endpoints']:
  for stage,w in [('initial',e['initial']),('endpoint',e['endpoint'])]:
   pairs=[dict(a=a,b=b,source_sign=(ref[a]>ref[b])-(ref[a]<ref[b]),candidate_sign=(w[a]>w[b])-(w[a]<w[b])) for i,a in enumerate([1,2,3,4,7,5,6]) for b in [1,2,3,4,7,5,6][i+1:]];rows.append(dict(method=label,start=e['start'],stage=stage,weights=w,rook_to_pawn=w[6]/w[1],bishop_to_pawn=w[5]/w[1],base7_pair_ordering_agreements=sum(x['source_sign']==x['candidate_sign'] for x in pairs),all_base_order_pairs=pairs,negative_promotion_deltas=[dict(base=a,promoted=b,delta=w[b]-w[a]) for a,b in [(1,9),(2,10),(3,11),(4,12),(5,13),(6,14)] if w[b]<w[a]],source_all12_logMSE=sum(math.log(w[a]/ref[a])**2 for a in axes)/12,source_base6_logMSE=sum(math.log(w[a]/ref[a])**2 for a in axes if a<8)/6))
out=dict(status='ALL8_PAIRED_MODEL_DESCRIPTORS_AFTER_FROZEN_SCORES',rows=rows,source_reference_sha256=hashlib.sha256((R/'results/dev_aux/task560/result.json').read_bytes()).hexdigest(),scope='Frozen sourceprior descriptiveproxy, NOT independenthumanconsensus/optimalprices. All4endpoints ALLaxes frozen before scores and thisreference read. No target/root/modelselection/fitness usingreference. Maturematerial-only Yanemodifiedcaller isnotunalignedNNUE/unmodifiedengine control.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(rows))
