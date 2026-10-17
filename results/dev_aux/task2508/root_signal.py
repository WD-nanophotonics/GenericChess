"""Use all existing TRAIN paired receipts; no new search, game or labels."""
from pathlib import Path
from collections import Counter
from math import tanh,isclose
import json
OUT=Path('results/dev_aux/task2508')
def run():
 rows=[json.loads(x)for x in Path('results/dev_aux/task2505/queries.jsonl').read_text().splitlines()];by={};counts=Counter();details=[]
 for r in rows:by.setdefault((r['seed'],r['family']),{})[r['quiet']]=r
 assert len(by)==64
 for key,pair in by.items():
  a,b=pair[False],pair[True];assert a['record']==b['record']and a['initial']==b['initial']and a['complete']and b['complete']
  def gradient(r):
   if r['pv_terminal']:return [0.]*5
   phi=r['pv_phi'];value=sum(x*w for x,w in zip(phi,r['initial']));assert value==r['value'];v=tanh(value/10.)
   return [0. if i==0 else x*(1-v*v)/10. for i,x in enumerate(phi)]
  ga,gb=gradient(a),gradient(b);score=a['value']!=b['value'];feature=(a['pv_terminal'],a['pv_phi'])!=(b['pv_terminal'],b['pv_phi']);action=a['action']!=b['action'];grad=any(not isclose(x,y,abs_tol=1e-14)for x,y in zip(ga,gb))
  counts['pairs']+=1;counts['score_changed']+=score;counts['PV_feature_changed']+=feature;counts['gradient_changed']+=grad;counts['root_action_changed']+=action;counts['same_features_and_score']+=not(feature or score);counts['q_nonquiet_capped_targets']+=b['stats']['q_truncated_leaf_labels'];counts['q_cap_still_tactical']+=b['stats']['q_cap_still_tactical']
  details.append(dict(seed=key[0],family=key[1],score_changed=score,feature_changed=feature,gradient_changed=grad,action_changed=action,plain_score=a['value'],q_score=b['value'],plain_PV=a['pv_phi'],q_PV=b['pv_phi'],plain_gradient=ga,q_gradient=gb,plain_nodes=a['nodes'],q_nodes=b['nodes']))
 result=dict(status='PASS_ALL64_MATCHED_TRAIN_QUERY_FEATURE_AND_GRADIENT_CHECKS',counts=dict(counts),plain_nodes=sum(r['nodes']for r in rows if not r['quiet']),q_nodes=sum(r['nodes']for r in rows if r['quiet']),plain_seconds=sum(r['seconds']for r in rows if not r['quiet']),q_seconds=sum(r['seconds']for r in rows if r['quiet']),details=details,scope='AllinitialTRAINpairedroots, not selection orWDL. Score/features/action changes show intervention, NOT improved accuracy/strength; q2 remains an explicit approximation. No failed/fullqquery subset upgraded to a truth oracle.')
 (OUT/'root-signal.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='details'}))
if __name__=='__main__':run()
