"""Matched-family cross-opponent utility interaction; no extra games/price selection."""
from pathlib import Path
from collections import Counter
import json,random,chess
OUT=Path('results/dev_aux/task2514');BASE=Path('results/dev_aux')
def run():
 p=json.loads((BASE/'task2516/plan.json').read_text());families=p['panels']['different_foe']['families'];indices={};behavior=Counter()
 for foe,path in(('uniform',BASE/'task2513/endpoint/games.jsonl'),('random',BASE/'task2516/different_foe/games.jsonl')):
  indices[foe]={(r['seed'],r['family'],r['color'],r['treatment']):r for r in map(json.loads,path.read_text().splitlines())}
 for s in p['seeds']:
  for f in families:
   for c in(0,1):
    for t in('initial','td','tree'):
     a=indices['random'].get((s,f,c,t));b=indices['uniform'].get((s,f,c,t))
     if a is None or b is None:behavior['missing_pair']+=1;continue
     assert a['weights']==b['weights']and a['initial_record']==b['initial_record'];am=a['record']['moves'];bm=b['record']['moves'];first=next((i for i,(x,y)in enumerate(zip(am,bm))if x!=y),None)
     if first is None:
      if am==bm:behavior['identical_full_record']+=1
      else:assert a['reward']is None or b['reward']is None;behavior['strict_prefix_censor']+=1
     else:
      board=chess.Board(a['record']['initial'])
      for u in am[:first]:board.push_uci(u)
      assert int(not board.turn)!=c;behavior['foe_first_difference']+=1
 def interval(foe,s,f,c,t):
  reward=indices[foe].get((s,f,c,t),{}).get('reward');return[-1.,1.]if reward is None else[float(reward)]*2
 def contrast(s,f,c,a,b):
  ar=interval('random',s,f,c,a);br=interval('random',s,f,c,b);au=interval('uniform',s,f,c,a);bu=interval('uniform',s,f,c,b)
  return[ar[0]-br[1]-au[1]+bu[0],ar[1]-br[0]-au[0]+bu[1]]
 comparisons=[]
 for a,b in(('td','initial'),('tree','initial'),('tree','td')):
  rr=[]
  for f in families:
   values=[contrast(s,f,c,a,b)for s in p['seeds']for c in(0,1)];rr.append([sum(x[j]for x in values)/len(values)for j in(0,1)])
  bounds=[sum(x[j]for x in rr)/len(rr)for j in(0,1)];rng=random.Random(88004);boot=[]
  for _ in range(5000):
   ss=[rng.choice(p['seeds'])for _ in p['seeds']];ff=[rng.choice(families)for _ in families];vv=[contrast(s,f,c,a,b)for s in ss for f in ff for c in(0,1)];boot.append([sum(x[j]for x in vv)/len(vv)for j in(0,1)])
  comparisons.append(dict(candidate=a,baseline=b,random_minus_uniform_gain_interaction_bounds=bounds,descriptive_seed_family_95_envelope=[sorted(x[0]for x in boot)[124],sorted(x[1]for x in boot)[4874]],matched_family_bounds=rr))
 result=dict(status='PASS_MATCHED_FOE_SWITCH_FIRST_DIFFERENCE_AND_INTERACTION',families=families,seeds=p['seeds'],foe_weights=p['foe_weights'],behavior=dict(behavior),comparisons=comparisons,scope='Same8endpointfamily subset/shared4seeds/bothroles/finalweights, onlyfixedfoe changes. Firstactualpathdivergence mustbe foe-turn, notcandidate. Differentfoe is random notrankedstronger. ActualU/missing4term bounds retained, descriptivecrossedbootstrap; repeatedfamiliesnotnewholdout. No extrafitness, parameterchoice, causalclaimfromunmatched16v8averages.');(OUT/'foe-interaction.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
