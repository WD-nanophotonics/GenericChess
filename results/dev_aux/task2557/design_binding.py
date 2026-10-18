"""Independent model/recipe binding, including exact pre-future-pin plan recovery."""
from pathlib import Path
import json,hashlib,itertools
O=Path('results/dev_aux/task2557')
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 T=Path('results/dev_aux/task2555');E=Path('results/dev_aux/task2556');old=load('results/dev_aux/task2546/result.json');new=load(T/'result.json');p=load(E/'plan.json');reg=load(T/'study-registration.json');bind=load(E/'pre-fitness-binding.json');assert sha(T/'plan.json')==reg['plans']['results/dev_aux/task2555/plan.json'];assert sha(E/'models.json')==bind['models_sha']
 # Append-only future hashes are removed in a COPY; the registered whole-plan SHA must match exactly.
 names=['results/dev_aux/task2546/result.json','results/dev_aux/task2555/plan.json','results/dev_aux/task2555/run.py','results/dev_aux/task2556/evaluate.py'];p0=dict(p);p0['pins']={n:p['pins'][n]for n in names};raw=json.dumps(p0,indent=2).encode();expected=reg['plans']['results/dev_aux/task2556/plan.json'];variants={'LF':raw,'CRLF':raw.replace(b'\n',b'\r\n')};matches=[(k,v)for k,v in variants.items()if hashlib.sha256(v).hexdigest()==expected];assert len(matches)==1 and expected==bind['registered_eval_plan_sha'];line_endings,raw=matches[0];h=expected;outpath=E/'registered-plan-before-binding.json';outpath.write_bytes(raw)
 models=load(E/'models.json');assert len(models['arms'])==64;by={(r['generator_seed'],r['method'],r['seed']):r for r in models['arms']};verified=0
 for label,data in [('D2',old),('D3',new)]:
  for a in data['arms']:
   name=label+('TD'if a['method']=='TD'else'Tree');r=by[a['generator_seed'],name,a['seed']];assert all(r[k]==a[k]for k in a if k!='method');assert r['source_method']==a['method']and r['source_training_depth']==int(label[-1]);assert a['nodes']==200000;verified+=1
 q=load(T/'plan.json');qold=load('results/dev_aux/task2546/plan.json');keys=['generator_seeds','initial_seeds','arms_order','nodes_per_arm','max_games','prefix_plies','H','eta','lam','foe','training_family_offset','ordering_seed_offset'];assert all(q[k]==qold[k]for k in keys);assert q['depth']==3 and qold['depth']==2 and q['opponent_depth']==2 and q['opponent_nodes_per_query']==qold['nodes_per_query']==4096;assert q['nodes_per_query']==16384
 product=set(itertools.product(p['generator_seeds'],p['initial_seeds'],p['families'],(0,1),['initial','D2TD','D2Tree','D3TD','D3Tree'],p['opponents'],(3,)));assert product==set(map(tuple,p['slots']))and len(p['slots'])==640
 result=dict(status='PASS_EXACT_REGISTERED_RECIPE_AND_ALL64_ENDPOINTS',models_verified=verified,slots_verified=640,registered_plan_sha=h,registered_line_endings=line_endings,training_design_equal_keys=keys,future_binding='Only future result/source/model hashes appended; exact prebinding bytecopy recovered by filtering pins and validated against BEFORETRAIN registration SHA. Current active plan untouched.',scope='Code/data/source provenance and complete endpoint inclusion, not independent identity authentication or scientific usefulness.')
 (O/'design-binding.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
