"""Horizon cost/signal curves from already-paid, deterministic node policies."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,collections,random
R=Path.cwd();O=R/'results/dev_aux/task1734';O.mkdir(exist_ok=False);out=[]
for task in (1723,1728):
 D=R/f'results/dev_aux/task{task}';plan=json.loads((D/'start.json').read_bytes())['plan'];games=[json.loads(l) for l in (D/'games.jsonl').open()];choices=[json.loads(l) for l in (D/'choices.jsonl').open()];lookup={(x['nodes'],tuple(x['price']),tuple(x['state'])):x for x in choices};ops={x['id']:x for x in plan['opponents']}
 for h in (12,24,48,96):
  keys=set();gg=collections.defaultdict(list);categories=collections.Counter()
  for x in games:
   ended=len(x['trajectory'])<=h and x['payoff'] is not None
   cat=x['category'] if ended else 'UNKNOWN_AT_SHORT_HORIZON';pay=x['payoff'] if ended else None;categories[cat]+=1;gg[tuple(x['price']),x['phase']].append(dict(family=x['family'],color=x['color'],opponent=x['opponent'],payoff=pay,event=pay or 0,lower=-1 if pay is None else pay,upper=1 if pay is None else pay))
   for z in x['trajectory'][:h]:
    op=ops[x['opponent']];p=tuple(x['price']) if z['own'] else tuple(op['price']);n=plan['candidate_nodes'] if z['own'] else op['nodes'];key=n,p,tuple(z['state'])
    if key in lookup:keys.add(key)
  summaries=[dict(price=p,phase=ph,games=len(rows),event_net=sum(z['event'] for z in rows)/len(rows),known=sum(z['payoff'] is not None for z in rows),lower=sum(z['lower'] for z in rows)/len(rows),upper=sum(z['upper'] for z in rows)/len(rows)) for (p,ph),rows in gg.items()]
  selected={}
  if task==1723:
   pp=list(map(tuple,plan['prices']))
   for ph in ('TRAIN1','TRAIN2'):selected[ph]=min(pp,key=lambda p:(-sum(z['event'] for z in gg[p,ph]),p))
   selected['POOLED']=min(pp,key=lambda p:(-sum(z['event'] for ph in ('TRAIN1','TRAIN2') for z in gg[p,ph]),p))
  out.append(dict(source_task=task,H=h,actual_new_native_go=0,prefix_required_unique_queries=len(keys),original_paid_unique_queries=len(choices),reported_nodes_of_prefix_queries=sum(lookup[k]['reported_nodes'] for k in keys),categories=dict(categories),selected_under_short_finite_objective=selected,summaries=summaries))
(O/'result.json').write_text(json.dumps(dict(status='COMPLETE_PAID_TRAJECTORY_HORIZON_CURVES',curves=out,interpretation='Counterfactual querywork, NOT measured rerunwall speedup. Short-H actualW-L eventobjective: no terminal byH remains UNKNOWN, even if a later paid proofshowsDraw. Price choices underfixedper-querynodes independentH; fullgridtraining allprices paid, shortH selector canreconstruct. Only originallyrunDEVprofiles are measured; never inventDEVfornewshortHwinner. Adaptive pathwoulddependH, so notreconstructed here. Perft/qualification/one-timeproofcost notsilentlyfree.'),indent=2))
for z in out:print({k:v for k,v in z.items() if k!='summaries'})

