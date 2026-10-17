"""Prospective matched opponent interaction; zero-containing interval is not invariance."""
from pathlib import Path
import json,random,time
D=Path('results/dev_aux/task2540');O=Path('results/dev_aux/task2541')
def run():
 began=time.perf_counter();p=json.loads((D/'plan.json').read_text());plan=json.loads((O/'interaction-plan.json').read_text());index={tuple(r['slot']):r for r in map(json.loads,(D/'games.jsonl').read_text().splitlines())};foes=plan['foes'];rules=p['generator_seeds'];seeds=p['initial_seeds'];families=p['families']
 def iv(g,s,f,c,t,foe):
  v=index.get((g,s,f,c,t,foe),{}).get('reward');return(-1,1)if v is None else(v,v)
 def contrast(g,s,f,c,foe):
  a=iv(g,s,f,c,'TD',foe);b=iv(g,s,f,c,'WDL',foe);return a[0]-b[1],a[1]-b[0]
 def bound(gs,ss,fs):
  lo=hi=0;n=0
  for g in gs:
   for s in ss:
    for f in fs:
     for c in(0,1):
      a=contrast(g,s,f,c,foes[0]);b=contrast(g,s,f,c,foes[1]);lo+=b[0]-a[1];hi+=b[1]-a[0];n+=1
  return[lo/n,hi/n]
 rng=random.Random(plan['bootstrap_seed']);boot=[]
 for _ in range(plan['resamples']):
  gs=[rng.choice(rules)for _ in rules];ss=[rng.choice(seeds)for _ in seeds];lo=hi=0
  for g in gs:
   fs=[rng.choice(families)for _ in families];a=bound([g],ss,fs);lo+=a[0];hi+=a[1]
  boot.append((lo/len(gs),hi/len(gs)))
 out=dict(status='MATCHED_OPPONENT_INTERACTION_BOUNDED',definition=f'(TD-WDL)@{foes[1]} minus (TD-WDL)@{foes[0]}',bounds=bound(rules,seeds,families),per_rule=[dict(rule=g,bounds=bound([g],seeds,families))for g in rules],per_seed=[dict(seed=s,bounds=bound(rules,[s],families))for s in seeds],descriptive_95=[sorted(x[0]for x in boot)[74],sorted(x[1]for x in boot)[2924]],seconds=time.perf_counter()-began,scope='Same rule/initial/root/role cells andresamplingdraws matchedacrossfixedfoes. Unknown/missing[-1,1]each; conservative4-outcomeinterval. ZeroenvelopeNOTequivalence/invariance; previouslyusedrandomfoenotnewstrategyholdout, no strengthhierarchyassumed. Allmodels/evaluationunchanged.')
 (O/'interaction.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
