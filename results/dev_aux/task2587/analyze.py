"""ALL registered DEV_AUX103 contrasts + pre-registered decision rule + full T/U decomposition."""
from pathlib import Path
from collections import Counter
import json,hashlib
from results.dev_aux.task2586.analyze import contrast
D=Path('results/dev_aux/task2587');E=D/'eval';G=D/'generic'
def load(p):return json.loads(Path(p).read_text())
def decompose(rows,slots,a,b):
 keys=sorted({(s[0],s[1],s[2],s[3],s[5])for s in slots});cat=Counter();lo=Counter();hi=Counter()
 for gs,seed,f,c,o in keys:
  x=rows.get((gs,seed,f,c,a,o));y=rows.get((gs,seed,f,c,b,o))
  xs=(-1,1)if x is None or x['reward']is None else(x['reward'],)*2;ys=(-1,1)if y is None or y['reward']is None else(y['reward'],)*2
  k=('T'if xs[0]==xs[1]else'U')+('T'if ys[0]==ys[1]else'U');cat[k]+=1;lo[k]+=xs[0]-ys[1];hi[k]+=xs[1]-ys[0]
 return dict(denominator=len(keys),categories=dict(cat),per_category=[dict(category=k,bounds=[lo[k],hi[k]])for k in sorted(cat)])
def run():
 p=load(G/'plan.json');reg=load(D/'registration.json');ep=load(E/'eval-plan.json');t=load(G/'result.json');ev=load(E/'eval-result.json')
 assert reg['registered_at']<load(G/'started.json')['utc']<load(E/'eval-started.json')['utc']
 for n,h in reg['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 rows={tuple(g['slot']):g for g in map(json.loads,(E/'eval-games.jsonl').open())};assert len(rows)==ev['actual'];S=ep['slots']
 pairs=[(f'Warm@{b}',f'Cold@{b}')for b in('0','25k','50k','100k')]+[('Warm@25k','Cold@100k'),('Cold@100k','Cold@0'),('Warm@100k','Warm@0')]
 out={}
 for a,b in pairs:
  out[a+' - '+b]=dict(all=contrast(rows,S,a,b),by_foe={o:contrast(rows,[s for s in S if s[5]==o],a,b)for o in ep['foes']},by_rule={str(gs):contrast(rows,[s for s in S if s[0]==gs],a,b)for gs in ep['rules']},by_seed={str(x):contrast(rows,[s for s in S if s[1]==x],a,b)for x in p['initial_seeds']})
 m=reg['decision_rule']['margin'];k1=out['Warm@25k - Cold@100k']['all']['bounds'];k2=out['Warm@100k - Cold@100k']['all']['bounds']
 decision='WARM_SAVES_DOSE'if k1[0]>=-m and k2[0]>=-m else'WARM_WORSE'if k2[1]<0 else'UNRESOLVED'
 decomp={k:decompose(rows,S,*k.split(' - '))for k in('Warm@25k - Cold@100k','Warm@100k - Cold@100k')}
 U=Counter(s[4]for s,g in rows.items()if g['reward']is None)
 result=dict(status='PASS_ALL_REGISTERED_CONTRASTS',decision=decision,decision_inputs={'Warm@25k - Cold@100k':k1,'Warm@100k - Cold@100k':k2,'margin':m},TRAIN={k:v for k,v in t.items()if k!='arms'},EVAL=ev,contrasts=out,decomposition=decomp,U_by_model=dict(U),paid_nodes=t['nodes']+ev['nodes'],producer_seconds=t['seconds']+ev['seconds'],scope='Pre-registered decision on finite pooled paired bounds; 4 NEW rules x 4 initials; repeated roots not independent; foes exposed. No CI/population claim.')
 (E/'summary.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(dict(decision=decision,inputs=result['decision_inputs'],EVAL={k:v for k,v in ev.items()if k!='missing_slots'},U=dict(U),contrasts={k:dict(all=v['all']['bounds'],**{o:z['bounds']for o,z in v['by_foe'].items()})for k,v in out.items()},decomposition=decomp),indent=1))
if __name__=='__main__':run()
