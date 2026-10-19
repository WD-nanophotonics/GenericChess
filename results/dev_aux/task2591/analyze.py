"""DEV_AUX107 probe decision on 363001: new Lam1@100k games + reused task2590 Cold@0/Cold@100k games (same slots)."""
from pathlib import Path
import json,hashlib
from results.dev_aux.task2586.analyze import contrast
from results.dev_aux.task2587.analyze import decompose
A=Path('results/dev_aux/task2590');D=Path('results/dev_aux/task2591');GS=363001
def load(p):return json.loads(Path(p).read_text())
def run():
 reg=load(D/'registration.json')
 for n,h in reg['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 assert reg['registered_at']<load(D/'generic'/'started.json')['utc']<load(D/'eval'/'eval-started.json')['utc']
 old={tuple(g['slot']):g for g in map(json.loads,(A/'eval'/'eval-games.jsonl').open())if g['slot'][0]==GS};new={tuple(g['slot']):g for g in map(json.loads,(D/'eval'/'eval-games.jsonl').open())}
 rows={**old,**new};ep=load(A/'eval'/'eval-plan.json');S=[s for s in ep['slots']if s[0]==GS]+load(D/'eval'/'eval-plan.json')['slots']
 out={f'{a} - {b}':dict(all=contrast(rows,S,a,b),by_foe={o:contrast(rows,[s for s in S if s[5]==o],a,b)for o in ep['foes']},by_seed={str(x):contrast(rows,[s for s in S if s[1]==x],a,b)for x in sorted({s[1]for s in S})})for a,b in(('Lam1@100k','Cold@0'),('Lam1@100k','Cold@100k'),('Cold@100k','Cold@0'))}
 k=out['Lam1@100k - Cold@0']['all']['bounds'];decision='FLIP'if k[0]>0 else'NO_FLIP'if k[1]<=0 else'UNRESOLVED'
 res=dict(status='PROBE_ANALYZED',decision=decision,decision_input=k,contrasts=out,decomposition=decompose(rows,S,'Lam1@100k','Cold@0'),EVAL=load(D/'eval'/'eval-result.json'),TRAIN={x:v for x,v in load(D/'generic'/'result.json').items()if x!='arms'},scope='Mechanism probe on ONE rule; lambda changed; finite paired bounds; not the SAME-learner claim, not causal channel attribution.')
 (D/'eval'/'summary.json').write_text(json.dumps(res,indent=2))
 print(json.dumps(dict(decision=decision,input=k,contrasts={x:dict(all=v['all']['bounds'],**{o:z['bounds']for o,z in v['by_foe'].items()},seeds={s:z['bounds']for s,z in v['by_seed'].items()})for x,v in out.items()},decomposition=res['decomposition']),indent=1))
if __name__=='__main__':run()
