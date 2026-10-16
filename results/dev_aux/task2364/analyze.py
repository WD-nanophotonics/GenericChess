"""Prespecified family-blocked actual-WL contrasts and first actual divergences."""
from pathlib import Path
from collections import defaultdict,Counter
import json,time,random
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2364')
def run(task=2362):
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());f=Path(f'results/dev_aux/task{task}');read=lambda p:json.loads(Path(p).read_text());p=read(f/'plan.json');done=read(f/'completion.json');slots=read(f/'slots.json');games=list(map(json.loads,(f/'games.jsonl').read_text().splitlines()));decisions=defaultdict(list)
 for r in map(json.loads,(f/'decisions.jsonl').read_text().splitlines()):decisions[r['slot']].append(r)
 assert len(slots)==p['expected_games']==128 and done['games']==len(games)and done['missing']==128-len(games)
 priceA,priceB=p['candidate_prices'];assert task==2362;by={g['slot']:g for g in games};pairs=defaultdict(dict)
 for sl in slots:pairs[(sl['root'],sl['opponent'],sl['candidate_color'])][sl['ratio']]=sl
 def interval(g):return(-1.,1.)if g is None or g['reward']is None else(g['reward'],g['reward'])
 rows=[];difs=[];cost=defaultdict(float);ownproofs=Counter();pricesout={x:Counter()for x in(priceA,priceB)}
 for key,pair in sorted(pairs.items()):
  stop();a=by.get(pair[priceA]['slot']);b=by.get(pair[priceB]['slot']);ia=interval(a);ib=interval(b);rows.append(dict(family=key[0],opponent=key[1],color=key[2],slots=[pair[priceA]['slot'],pair[priceB]['slot']],rewards=[None if a is None else a['reward'],None if b is None else b['reward']],delta_low=ib[0]-ia[1],delta_high=ib[1]-ia[0],exact=None if ia[0]!=ia[1]or ib[0]!=ib[1]else ib[0]-ia[0],records_equal=a is not None and b is not None and a['record']==b['record']))
  if a is None or b is None:continue
  da=decisions[a['slot']][:a['plies']];db=decisions[b['slot']][:b['plies']];first=None
  for n,(x,y)in enumerate(zip(da,db)):
   if x['choice']!=y['choice']:
    assert x['root_record']==y['root_record']and x['root_state_sha']==y['root_state_sha'];first=dict(family=key[0],opponent=key[1],color=key[2],ply=n,is_candidate=x['is_candidate'],sources=[x['source'],y['source']],normal_depths=[None if d['normal_receipt']is None else d['normal_receipt']['completed_depth']for d in(x,y)],normal_causes=[None if d['normal_receipt']is None else d['normal_receipt']['exit_cause']for d in(x,y)],choices=[x['choice'],y['choice']],root_record=x['root_record'],outcomes=[a['outcome'],b['outcome']],delta=rows[-1]['exact']);break
  if first is not None:difs.append(first)
 proof_timing=[]
 for g in games:
  ownmaterial=0
  for decision in decisions[g['slot']][:g['plies']]:
   if decision['is_candidate']and decision['source']=='FULL_SESSION_MATERIAL_SEARCH':ownmaterial+=1
   if decision['is_candidate']and decision['source']in('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY'):proof_timing.append(dict(slot=g['slot'],family=g['root'],price=g['ratio'],ply=decision['ply'],source=decision['source'],own_material_decisions_before=ownmaterial))
  pricesout[g['ratio']][g['outcome']]+=1;cost[g['ratio']]+=g['seconds']
  ownproofs[g['ratio']]+=sum(d['is_candidate']and d['source']=='VERIFIED_GRAPH_STRATEGY'for d in decisions[g['slot']])
 def estimate(selected):
  grouped=defaultdict(list)
  for r in selected:grouped[r['family']].append(r)
  bounds=[(sum(r['delta_low']for r in rr)/len(rr),sum(r['delta_high']for r in rr)/len(rr))for family,rr in sorted(grouped.items())];rng=random.Random(810037);samples=[]
  for k in range(10000):
   if k%1000==0:stop()
   sample=[bounds[rng.randrange(len(bounds))]for j in bounds];samples.append((sum(x[0]for x in sample)/len(sample),sum(x[1]for x in sample)/len(sample)))
  lows=sorted(x[0]for x in samples);highs=sorted(x[1]for x in samples)
  return dict(families=len(bounds),pairedslots=len(selected),mean_lower=sum(x[0]for x in bounds)/len(bounds),mean_upper=sum(x[1]for x in bounds)/len(bounds),descriptive_family_bootstrap=[lows[249],highs[9749]],complete_pairs=sum(r['exact']is not None for r in selected),positive_families=sum(x[0]>0 for x in bounds),negative_families=sum(x[1]<0 for x in bounds),family_bounds=bounds)
 result=dict(status='CLOSED_ACTUAL_WL_FAMILY_CONTRAST_NO_FIT',task=task,contrast=[priceB,priceA],planned_games=128,actual_returned=len(games),actual_terminals=sum(g['outcome']!='U'for g in games),UNKNOWN=sum(g['outcome']=='U'for g in games),never_executed=128-len(games),actual_game_plies=sum(g['plies']for g in games),by_price={str(k):dict(v)for k,v in pricesout.items()},game_seconds=dict(cost),candidate_graph_admissions=dict(ownproofs),candidate_proof_timing=proof_timing,overall=estimate(rows),by_foe={str(k):estimate([r for r in rows if r['opponent']==k])for k in(0,1)},by_color={str(k):estimate([r for r in rows if r['color']==k])for k in(0,1)},identical_full_record_pairs=sum(r['records_equal']for r in rows),first_actual_divergences=difs,pairs=rows,seconds=time.perf_counter()-t,scope='ALLfrozen16families/64pricepairs; PREFITreservedvalidation TRAINselectedprice minusbaseline1, nofit/bestpriceclaim. Realterminalrewards only; U/missing intervalbounds. Roles/foes clustered byfamily, bootstrapdescriptive notrobustness/equivalenceproof. Firstfoedifference couldbe wallresource/pathnoise, notmaterialcausalproof. Proofadmission/timeordering notmediation. Samefamilycontrolcorrelated; referenceconditionalmu/exposure/prepayment disclosed.')
 with(OUT/f'task{task}-result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:result[k]for k in('status','task','actual_returned','actual_terminals','UNKNOWN','never_executed','actual_game_plies','by_price','game_seconds','overall','identical_full_record_pairs')}))
if __name__=='__main__':import sys;run(int(sys.argv[1])if len(sys.argv)>1 else 2362)
