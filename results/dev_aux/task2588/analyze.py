"""ALL registered DEV_AUX104 contrasts + pre-registered decision + full T/U decomposition."""
from pathlib import Path
from collections import Counter
import json,hashlib
from results.dev_aux.task2586.analyze import contrast
from results.dev_aux.task2587.analyze import decompose
D=Path('results/dev_aux/task2588');E=D/'eval';G=D/'generic'
def load(p):return json.loads(Path(p).read_text())
def run():
 p=load(G/'plan.json');reg=load(D/'registration.json');ep=load(E/'eval-plan.json');t=load(G/'result.json');ev=load(E/'eval-result.json')
 assert reg['registered_at']<load(G/'started.json')['utc']<load(E/'eval-started.json')['utc']
 for n,h in reg['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 rows={tuple(g['slot']):g for g in map(json.loads,(E/'eval-games.jsonl').open())};assert len(rows)==ev['actual'];S=ep['slots']
 pairs=[('Cold@25k','Cold@0'),('Cold@50k','Cold@0'),('Cold@100k','Cold@0'),('Cold@100k','Cold@25k')]
 out={a+' - '+b:dict(all=contrast(rows,S,a,b),by_foe={o:contrast(rows,[s for s in S if s[5]==o],a,b)for o in ep['foes']},by_rule={str(gs):contrast(rows,[s for s in S if s[0]==gs],a,b)for gs in ep['rules']},by_seed={str(x):contrast(rows,[s for s in S if s[1]==x],a,b)for x in p['initial_seeds']})for a,b in pairs}
 k=out['Cold@100k - Cold@0']['all']['bounds'];decision='LEARNS_5x5'if k[0]>0 else'NO_GAIN'if k[1]<=0 else'UNRESOLVED'
 U=Counter(s[4]for s,g in rows.items()if g['reward']is None)
 result=dict(status='PASS_ALL_REGISTERED_CONTRASTS',decision=decision,decision_input=k,channels=reg['channels'],TRAIN={x:v for x,v in t.items()if x!='arms'},EVAL=ev,contrasts=out,decomposition=decompose(rows,S,'Cold@100k','Cold@0'),U_by_model=dict(U),paid_nodes=t['nodes']+ev['nodes'],producer_seconds=t['seconds']+ev['seconds'],scope='Pre-registered decision on finite pooled paired bounds; NEW 5x5 rules x 4 initials; repeated roots not independent; foes exposed/positional. No CI/population claim.')
 (E/'summary.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(dict(decision=decision,input=k,EVAL={x:v for x,v in ev.items()if x!='missing_slots'},U=dict(U),contrasts={x:dict(all=v['all']['bounds'],**{o:z['bounds']for o,z in v['by_foe'].items()},rules={r:z['bounds']for r,z in v['by_rule'].items()})for x,v in out.items()},decomposition=result['decomposition']),indent=1))
if __name__=='__main__':run()
