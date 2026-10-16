"""All jointly legal placement-matched composition comparisons; no pricefit."""
from pathlib import Path
from collections import defaultdict,Counter
import json,time
from scripts.generic_royal_actor import RoyalActor
OUT=Path('results/dev_aux/task2077')
def run():
 t=time.perf_counter();p=json.loads((OUT/'plan.json').read_text());assert json.loads(Path('results/dev_aux/task2074/result.json').read_text())['status']=='PASS_COMPLETE_COVERAGE_BELLMAN_RANK_CANONICAL_HISTORY';labels=[json.loads(x)for x in Path('results/dev_aux/task2073/labels.jsonl').read_text().splitlines()];groups=defaultdict(lambda:defaultdict(list));actor=RoyalActor(4)
 for l in labels:
  if l['inventory']not in('KKBN','KKNN','KKBB'):continue
  raw=l['board'];extras=[i for i,x in enumerate(raw[:-1])if x not in('.','K','k')];owner=int(raw[extras[0]].islower());key=(raw.index('K'),raw.index('k'),tuple(extras),owner,raw[-1]);v={'WIN':1,'DRAW':0,'LOSS':-1}[l['label']];v=v if raw[-1]==owner else-v;assert v in(0,1)
  safe=not any(actor.attacked(raw,actor.king(raw,side),1-side)for side in(0,1));groups[key][l['inventory']].append((v,safe,l['status']))
 selected=[];safe=[]
 for key,g in groups.items():
  if len(g['KKNN'])!=1 or len(g['KKBB'])!=1 or len(g['KKBN'])!=2:continue
  vals=dict(NN=g['KKNN'][0][0],BB=g['KKBB'][0][0],BN=sum(v for v,_,_ in g['KKBN'])/2);selected.append(vals)
  if all(s for rows in g.values()for _,s,_ in rows):safe.append(vals)
 def summary(rows):
  n=len(rows);return dict(matched_placement_families=n,attacker_win_fraction={k:sum(r[k]for r in rows)/n for k in('NN','BB','BN')},BN_minus_NN=sum(r['BN']-r['NN']for r in rows)/n,BN_minus_BB=sum(r['BN']-r['BB']for r in rows)/n,BN_strictly_better_than_both=sum(r['BN']>max(r['NN'],r['BB'])for r in rows),BN_strictly_worse_than_both=sum(r['BN']<min(r['NN'],r['BB'])for r in rows),counts={str(k):v for k,v in Counter((r['NN'],r['BB'],r['BN'])for r in rows).items()})
 result=dict(status='COMPLETE_EXACT_MATCHED_COMPOSITION_ENUMERATION',all_jointly_legal=summary(selected),all_four_assignments_both_kings_safe=summary(safe),seconds=time.perf_counter()-t,scope=p['quantity'],no_scalar_ratio_or_actualpolicy_strength_claim=True);assert result['seconds']<p['seconds_cap'];(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
