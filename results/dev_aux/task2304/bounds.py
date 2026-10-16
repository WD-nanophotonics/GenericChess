"""Exact denominators and sharp one-sided UNKNOWN reward bounds, no fill."""
from pathlib import Path
from collections import Counter
import json,numpy as np
OUT=Path("results/dev_aux/task2304")
def run():
 folder=Path("results/dev_aux/task2287");p=json.loads((folder/"plan.json").read_text());roots=json.loads((folder/"inputs.json").read_text())["roots"];gs=[json.loads(x)for x in(folder/"games.jsonl").read_text().splitlines()];completion=json.loads((folder/"completion.json").read_text());slots=[]
 for seed in p['seeds']:
  for root in roots:
   for foe in p['opponent_prices']:
    for role in p['candidate_colors']:
     profiles=p['profiles']if(root['family']+role)%2==0 else list(reversed(p['profiles']))
     for price in profiles:slots.append(dict(slot=len(slots),seed=seed,family=root['family'],foe=foe,role=role,ratio=price))
 seen={g['slot']:g for g in gs};interrupted=completion['unknown_interrupted_slots'];missing=[s for s in slots if s['slot']not in seen];assert [s['slot']for s in missing]==interrupted==[248]
 def bounds(g):return(-1.,1.)if g is None or g['reward']is None else(g['reward'],)*2
 idx={(g['context'],g['family'],g['opponent_ratio'],g['candidate_color'],g['ratio']):g for g in gs};rng=np.random.default_rng(20261017792304);contrasts={}
 for seed in p['seeds']:
  cc={}
  for a,b in[(1.5,2.),(3.,2.),(1.5,3.)]:
   lo=[];hi=[]
   for root in roots:
    values=[]
    for foe in p['opponent_prices']:
     for role in p['candidate_colors']:
      x=bounds(idx.get((seed,root['family'],foe,role,a)));y=bounds(idx.get((seed,root['family'],foe,role,b)));values.append((y[0]-x[1],y[1]-x[0]))
    lo.append(sum(v[0]for v in values)/4);hi.append(sum(v[1]for v in values)/4)
   lo=np.array(lo);hi=np.array(hi);ind=rng.integers(0,32,size=(10000,32));cc[str(b)+'-vs-'+str(a)]=dict(sharp_net_lower=float(lo.mean()),sharp_net_upper=float(hi.mean()),descriptive95_envelope=[float(np.quantile(lo[ind].mean(axis=1),.025)),float(np.quantile(hi[ind].mean(axis=1),.975))],family_blocks=32)
  contrasts[str(seed)]=cc
 result=dict(status="PASS_EXACT_SLOT_DENOMINATORS_AND_SHARP_UNKNOWN_BOUNDS",planned=768,attempted=768,actual_completed_terminals=767,returned_completed_records=767,actual_terminal_counts=dict(Counter(g['outcome']for g in gs)),interrupted_unknown_count=1,interrupted_unknown_slots=missing,never_executed_slots=0,known_ongoing_returned_records=0,sharp_contrasts=contrasts,scope="Oneunknown SLOT_ID248, not248unknowns. Completeoutcomes remain767actualW/L/D; attemptedinterruptedU1 hasno completedrecord andisneverfilled0. Eachunknownreward[-1,+1] combinedwithknownpairedreward forsharperbounds. Earlier2290fullpair[-2,+2]bounds remainvalidconservative historicalanalysis, notchangedoutcomes or fit.3vsold1hasNOmissingpairs.")
 (OUT/"result.json").write_bytes(json.dumps(result,indent=2).encode());print(json.dumps(result))
if __name__=="__main__":run()
