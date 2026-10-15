"""Paired physical handoff mechanism, same fixed candidates and original roots."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,collections,random
R=Path.cwd();O=R/'results/dev_aux/task1757';O.mkdir(exist_ok=False);results=[];allpairs=[];rng=random.Random(2026701557)
for new,old in ((1748,1730),(1752,1739)):
 D=R/f'results/dev_aux/task{new}';p=json.loads((D/'start.json').read_bytes())['plan'];run=json.loads((D/'result.json').read_bytes());assert run['status']=='COMPLETE';oldg=[json.loads(l) for l in (R/f'results/dev_aux/task{old}/games.jsonl').open()];newg=[json.loads(l) for l in (D/'games.jsonl').open()]
 key=lambda x:(tuple(x['price']),x['phase'],x['family'],x['color'],x['opponent'])
 og={key(x):x for x in oldg};ng={key(x):x for x in newg};cc=collections.Counter();witness=[]
 for k,b in ng.items():
  if k not in og:continue
  a=og[k];aa=a['trajectory'];bb=b['trajectory'];i=0
  while i<min(len(aa),len(bb)) and aa[i]['move']==bb[i]['move']:assert aa[i]['state']==bb[i]['state'];i+=1
  same=i==len(aa)==len(bb)
  if not same:
   assert i<len(aa) and i<len(bb) and aa[i]['state']==bb[i]['state'] and bb[i]['policy_source']=='EXACT_KRK_RANK_MOVE'
   if len(witness)<16:witness.append(dict(key=k,ply=i,state=bb[i]['state'],native_move=aa[i]['move'],rank_move=bb[i]['move'],old_category=a['category'],new_category=b['category']))
  cc['matched_existing_episodes']+=1;cc['same_complete_trajectory']+=same;cc['first_divergence_at_verified_rank_policy']+=not same;cc['cycle_to_physical_mate']+=a['category']=='PROVED_POLICY_CYCLE_DRAW' and b['category']=='PHYSICAL_MATE';cc['native_terminal_to_changed_label']+=a['category'].startswith('PHYSICAL') and a['payoff']!=b['payoff']
 C=tuple(p['fixed_native_candidate']);B=tuple(p['baseline']);ids=sorted({x['family'] for x in newg if x['phase']=='DEV'});contrasts=[]
 def familyprice(rows,price,op,k):
  out={}
  for f in ids:
   aa=[x for x in rows if x['phase']=='DEV' and tuple(x['price'])==price and x['family']==f and(op=='MIXTURE' or x['opponent']==op)]
   assert len(aa)==(4 if op=='MIXTURE' else 2);out[f]=sum((x[k] or 0) for x in aa)/len(aa)
  return out
 for op in ['MIXTURE']+[o['id'] for o in p['opponents']]:
  ff={}
  for label,rows in [('OLD',oldg),('NEW',newg)]:
   ca={k:familyprice(rows,C,op,k) for k in ('payoff','lower','upper')};ba={k:familyprice(rows,B,op,k) for k in ca}
   ff[label]=dict(point={f:ca['payoff'][f]-ba['payoff'][f] for f in ids},lower={f:ca['lower'][f]-ba['upper'][f] for f in ids},upper={f:ca['upper'][f]-ba['lower'][f] for f in ids})
  d={f:ff['NEW']['point'][f]-ff['OLD']['point'][f] for f in ids};lo={f:ff['NEW']['lower'][f]-ff['OLD']['upper'][f] for f in ids};hi={f:ff['NEW']['upper'][f]-ff['OLD']['lower'][f] for f in ids};bo=[];bl=[];bh=[]
  for _ in range(10000):
   ss=rng.choices(ids,k=len(ids));bo.append(sum(d[f] for f in ss)/len(ss));bl.append(sum(lo[f] for f in ss)/len(ss));bh.append(sum(hi[f] for f in ss)/len(ss))
  bo.sort();bl.sort();bh.sort();contrasts.append(dict(opponent=op,old_fixed_gain=sum(ff['OLD']['point'].values())/len(ids),new_fixed_gain=sum(ff['NEW']['point'].values())/len(ids),paired_gain_interaction=sum(d.values())/len(ids),family95=[bo[249],bo[9749]],interaction_infinite_bounds=[sum(lo.values())/len(ids),sum(hi.values())/len(ids)],infinite_family95=[bl[249],bh[9749]]))
 for price in sorted({tuple(x['price']) for x in newg if x['phase']=='DEV'}):
  for mode,rows in [('NATIVE',oldg),('HYBRID',newg)]:
   aa=[x for x in rows if x['phase']=='DEV' and tuple(x['price'])==price]
   if aa:allpairs.append(dict(source_new=new,price=price,mode=mode,categories=dict(collections.Counter(x['category'] for x in aa)),net=sum(x['payoff'] or 0 for x in aa)/len(aa),games=len(aa)))
 results.append(dict(new_run=new,source_native=old,fixed_candidate=C,prefix_counts=dict(cc),first_divergence_witnesses=witness,contrasts=contrasts,scope='Fixed-originalTRAINcandidate/primaryWDLinteraction isolateschangedpostKRKpolicy. NewhybridTRAINwinner alsousesdifferentglobalgridselector, so do notascribeitsdifference solelytopostKRK. Samepreviouslyexposed48families, notnewholdout.'))
out=dict(status='PASS_PHYSICAL_KRK_HANDOFF_PREFIX_CAUSAL_CONTROL',results=results,DEV_categories=allpairs,actual_new_native_go=0)
(O/'result.json').write_text(json.dumps(out,indent=2))
for x in results:print({k:v for k,v in x.items() if k!='first_divergence_witnesses'})

