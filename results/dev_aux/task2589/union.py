"""Re-apply the DEV_AUX104 registered decision to the union of 104 games and 105 completion games."""
from pathlib import Path
from collections import Counter
import json,hashlib
from results.dev_aux.task2586.analyze import contrast
from results.dev_aux.task2587.analyze import decompose
A=Path('results/dev_aux/task2588');D=Path('results/dev_aux/task2589')
def load(p):return json.loads(Path(p).read_text())
def run():
 reg=load(D/'registration.json')
 for n,h in reg['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 assert reg['registered_at']<load(D/'eval'/'eval-started.json')['utc']
 ep=load(A/'eval'/'eval-plan.json');a={tuple(g['slot']):g for g in map(json.loads,(A/'eval'/'eval-games.jsonl').open())};b={tuple(g['slot']):g for g in map(json.loads,(D/'eval'/'eval-games.jsonl').open())}
 assert not set(a)&set(b);rows={**a,**b};S=ep['slots'];missing=[s for s in S if tuple(s)not in rows]
 pairs=[('Cold@25k','Cold@0'),('Cold@50k','Cold@0'),('Cold@100k','Cold@0'),('Cold@100k','Cold@25k')]
 out={x+' - '+y:dict(all=contrast(rows,S,x,y),by_foe={o:contrast(rows,[s for s in S if s[5]==o],x,y)for o in ep['foes']},by_rule={str(gs):contrast(rows,[s for s in S if s[0]==gs],x,y)for gs in ep['rules']},by_seed={str(k):contrast(rows,[s for s in S if s[1]==k],x,y)for k in sorted({s[1]for s in S})})for x,y in pairs}
 k=out['Cold@100k - Cold@0']['all']['bounds'];decision='LEARNS_5x5'if k[0]>0 else'NO_GAIN'if k[1]<=0 else'UNRESOLVED'
 U=Counter(s[4]for s,g in rows.items()if g['reward']is None)
 res=dict(status='UNION_REGISTERED_RULE_REAPPLIED',decision=decision,decision_input=k,games_104=len(a),games_105=len(b),still_missing=len(missing),EVAL_105=load(D/'eval'/'eval-result.json'),contrasts=out,decomposition=decompose(rows,S,'Cold@100k','Cold@0'),U_by_model=dict(U),scope='Union of DEV_AUX104 PARTIAL_CAP games and DEV_AUX105 completion of exactly the missing slots; identical models/roots/foes/ordering. Finite pooled paired bounds, not CIs.')
 (D/'eval'/'union-summary.json').write_text(json.dumps(res,indent=2))
 print(json.dumps(dict(decision=decision,input=k,games=[len(a),len(b)],still_missing=len(missing),U=dict(U),contrasts={x:dict(all=v['all']['bounds'],**{o:z['bounds']for o,z in v['by_foe'].items()},rules={r:z['bounds']for r,z in v['by_rule'].items()})for x,v in out.items()},decomposition=res['decomposition']),indent=1))
if __name__=='__main__':run()
