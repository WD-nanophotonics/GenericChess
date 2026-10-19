"""ALL registered DEV_AUX108 contrasts: pooled decision + per-rule counts + full T/U decomposition."""
from pathlib import Path
from collections import Counter
import json,hashlib
from results.dev_aux.task2586.analyze import contrast
from results.dev_aux.task2587.analyze import decompose
D=Path('results/dev_aux/task2592');E=D/'eval';G=D/'generic'
def load(p):return json.loads(Path(p).read_text())
def run():
 p=load(G/'plan.json');reg=load(D/'registration.json');ep=load(E/'eval-plan.json');t=load(G/'result.json');ev=load(E/'eval-result.json')
 assert reg['registered_at']<load(G/'started.json')['utc']<load(E/'eval-started.json')['utc']
 for n,h in reg['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 rows={tuple(g['slot']):g for g in map(json.loads,(E/'eval-games.jsonl').open())};assert len(rows)==ev['actual'];S=ep['slots'];a,b='Cold@100k','Cold@0'
 out=dict(all=contrast(rows,S,a,b),by_foe={o:contrast(rows,[s for s in S if s[5]==o],a,b)for o in ep['foes']},by_rule={str(gs):contrast(rows,[s for s in S if s[0]==gs],a,b)for gs in ep['rules']},by_rule_foe={f'{gs}/{o}':contrast(rows,[s for s in S if s[0]==gs and s[5]==o],a,b)for gs in ep['rules']for o in ep['foes']},by_seed={str(x):contrast(rows,[s for s in S if s[1]==x],a,b)for x in p['initial_seeds']})
 k=out['all']['bounds'];decision='LEARNS_LEAP'if k[0]>0 else'NO_GAIN'if k[1]<=0 else'UNRESOLVED'
 per=Counter('positive'if v['bounds'][0]>0 else'negative'if v['bounds'][1]<0 else'undetermined'for v in out['by_rule'].values())
 trainroots={(g['generator_seed'],json.dumps(g['initial_record'],sort_keys=True))for g in map(json.loads,(G/'games.jsonl').open())};overlap=sum((s[0],json.dumps(g['initial_record'],sort_keys=True))in trainroots for s,g in rows.items())
 U=Counter(s[4]for s,g in rows.items()if g['reward']is None)
 res=dict(status='PASS_ALL_REGISTERED_CONTRASTS',decision=decision,decision_input=k,per_rule=dict(per),contrast=out,decomposition=decompose(rows,S,a,b),U_by_model=dict(U),U_total=sum(U.values()),eval_slots_with_actual_TRAIN_root=overlap,TRAIN={x:v for x,v in t.items()if x!='arms'},EVAL=ev,paid_nodes=t['nodes']+ev['nodes'],producer_seconds=t['seconds']+ev['seconds'],scope='One pre-fixed movement config; finite pooled paired bounds; per-rule counts reported; held-out roots by pre-fitness rule (actual overlap re-checked). No CI/population/all-rule claim.')
 (E/'summary.json').write_text(json.dumps(res,indent=2))
 print(json.dumps(dict(decision=decision,input=k,per_rule=dict(per),foes={o:v['bounds']for o,v in out['by_foe'].items()},rules={r:v['bounds']for r,v in out['by_rule'].items()},rule_foe={r:v['bounds']for r,v in out['by_rule_foe'].items()},U=res['U_total'],overlap=overlap,EVAL={x:v for x,v in ev.items()if x!='missing_slots'},decomposition=res['decomposition']),indent=1))
if __name__=='__main__':run()
