"""ALL registered DEV_AUX102 contrasts on NEW rules; finite paired bounds, no selection."""
from pathlib import Path
from collections import Counter,defaultdict
import json,itertools,hashlib
D=Path('results/dev_aux/task2586');E=D/'eval';G=D/'generic'
def load(p):return json.loads(Path(p).read_text())
def bounds(g):
 if g is None or g['reward']is None:return(-1.,1.)
 return(float(g['reward']),float(g['reward']))
def contrast(rows,slots,left,right):
 keys=sorted({(s[0],s[1],s[2],s[3],s[5])for s in slots});lo=hi=0.;cc=Counter()
 for gs,seed,f,c,o in keys:
  a=rows.get((gs,seed,f,c,left,o));b=rows.get((gs,seed,f,c,right,o));aa,bb=bounds(a),bounds(b);lo+=aa[0]-bb[1];hi+=aa[1]-bb[0]
  cc['both_terminal']+=a is not None and b is not None and a['reward']is not None and b['reward']is not None;cc['missing']+=a is None or b is None
 n=max(1,len(keys));return dict(n=len(keys),bounds=[lo/n,hi/n],counts=dict(cc))
def run():
 p=load(G/'plan.json');reg=load(D/'registration.json');ep=load(E/'eval-plan.json');t=load(G/'result.json');ev=load(E/'eval-result.json');bind=load(E/'result.json')
 assert reg['registered_at']<load(G/'started.json')['utc']<load(E/'eval-started.json')['utc']
 for n,h in reg['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 assert bind['training_sha']==hashlib.sha256((G/'result.json').read_bytes()).hexdigest()
 rows={tuple(g['slot']):g for g in map(json.loads,(E/'eval-games.jsonl').open())};assert len(rows)==ev['actual']
 pairs=[('Fixed@100k','initial'),('Fixed@200k','initial'),('Fixed@400k','initial'),('Fixed@400k','Fixed@100k'),('OldRulesMean','initial'),('Fixed@400k','OldRulesMean')]
 S=ep['slots'];out={}
 for a,b in pairs:
  out[a+' - '+b]=dict(all=contrast(rows,S,a,b),by_foe={o:contrast(rows,[s for s in S if s[5]==o],a,b)for o in ep['foes']},by_rule={str(gs):{o:contrast(rows,[s for s in S if s[0]==gs and s[5]==o],a,b)for o in ep['foes']}for gs in ep['rules']},by_seed={str(seed):{o:contrast(rows,[s for s in S if s[1]==seed and s[5]==o],a,b)for o in ep['foes']}for seed in p['initial_seeds']},by_role={str(c):{o:contrast(rows,[s for s in S if s[3]==c and s[5]==o],a,b)for o in ep['foes']}for c in(0,1)},
   by_rule_seed={f'{gs}/{seed}':contrast(rows,[s for s in S if s[0]==gs and s[1]==seed],a,b)for gs in ep['rules']for seed in p['initial_seeds']})
 absolute={}
 for gs,m,o in itertools.product(ep['rules'],sorted({s[4]for s in S}),ep['foes']):
  cc=Counter()
  for s in S:
   if s[0]==gs and s[4]==m and s[5]==o:
    g=rows.get(tuple(s));cc['missing'if g is None else'U'if g['reward']is None else'W'if g['reward']>0 else'L'if g['reward']<0 else'D']+=1
  absolute[f'{gs}/{m}/{o}']=dict(cc)
 train=defaultdict(Counter)
 for g in map(json.loads,(G/'games.jsonl').open()):
  k=f"{g['generator_seed']}/{g['seed']}";train[k].update(dict(games=1,nodes=g['nodes'],terms=g['stats']['samples'],terminal=g['outcome']is not None,U=g['outcome']is None))
 trainroots={json.dumps(g['initial_record'],sort_keys=True)for g in map(json.loads,(G/'games.jsonl').open())};evalroots={json.dumps(g['initial_record'],sort_keys=True)for g in rows.values()}
 result=dict(status='PASS_ALL_REGISTERED_CONTRASTS',TRAIN={k:v for k,v in t.items()if k!='arms'},EVAL=ev,contrasts=out,absolute_WLD=absolute,TRAIN_arms={k:dict(v)for k,v in train.items()},bound_weights={f"{a['method']}/{a['generator_seed']}/{a['seed']}":a['weights']for a in bind['arms']},exposure=dict(TRAIN_records=len(trainroots),EVAL_records=len(evalroots),overlap=len(trainroots&evalroots)),paid_nodes=t['nodes']+ev['nodes'],producer_seconds=t['seconds']+ev['seconds'],scope='NEW-rule finite paired bounds; 4 rules x 4 initials, repeated roots not independent; foes exposed in DEV_AUX96. No CI/population/all-rule claim. OldRulesMean is a fixed pre-registered aggregate of old endpoints, not a selected model.')
 (E/'summary.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(dict(status=result['status'],EVAL={k:v for k,v in ev.items()if k!='missing_slots'},contrasts={k:dict(all=v['all']['bounds'],**{o:z['bounds']for o,z in v['by_foe'].items()})for k,v in out.items()},exposure=result['exposure']),indent=1))
if __name__=='__main__':run()
