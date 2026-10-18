"""Absolute outcomes and remaining margin; UNKNOWN/missing are not draws."""
from pathlib import Path
from collections import Counter,defaultdict
import json
D=Path('results/dev_aux/task2572')
def run():
 p=json.loads((D/'eval-plan.json').read_text());counts=defaultdict(Counter);expected=Counter(s[4]+'/'+s[5]for s in p['slots'])
 for g in map(json.loads,(D/'eval-games.jsonl').open()):
  key=g['slot'][4]+'/'+g['slot'][5];counts[key].update(dict(games=1,nodes=g['nodes'],queries=g['queries'],W=g['reward']==1,L=g['reward']==-1,D=g['reward']==0,unknown=g['reward']is None));counts[key]['reward_sum']+=g['reward']if g['reward']is not None else 0
 out={}
 for key,n in sorted(expected.items()):
  c=counts[key];missing=n-c['games'];u=missing+c['unknown'];lo,hi=(c['reward_sum']-u)/n,(c['reward_sum']+u)/n;out[key]=dict(c,expected=n,missing=missing,mean_W_minus_L=lo if lo==hi else None,reward_bounds=[lo,hi],room_to_maximum_bounds=[1-hi,1-lo])
 result=dict(status='ALL_CONTEXT_ABSOLUTE_WLD_AND_HEADROOM_RETAINED',by_model_and_foe=out,scope='AbsoluteWLD andknownheadroom preventmisreadingshrinkingpricegain. Tacticalsearchmayimproveinitialbaseline morethanlearnedmodels; it canalsoworsensomemodels. Zero incrementalpricegain not identicalplay orq2weakness/universalpricefailure. PreserveW/L/D/U/missing separately, finiteboundsnotCIs.')
 (D/'absolute-wld.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(status=result['status'],groups=len(out))))
if __name__=='__main__':run()
