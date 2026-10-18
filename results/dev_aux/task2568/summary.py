"""Finite paired strength/cost summary: every registered slot and censor retained."""
from pathlib import Path
from collections import Counter,defaultdict
import json,itertools,sys,hashlib

def bounds(game):
 if game is None or game['reward']is None:return(-1.,1.)
 return(game['reward'],game['reward'])
def contrast(rows,slots,left,right):
 # Each scheduled seed/family/role/foe is one matched cell; no populationCI.
 keys=sorted({(s[1],s[2],s[3],s[5])for s in slots});lo=hi=0.;actual=Counter();cells=[]
 for seed,family,color,foe in keys:
  a=rows.get((0,seed,family,color,left,foe));b=rows.get((0,seed,family,color,right,foe));aa,bb=bounds(a),bounds(b);x,y=aa[0]-bb[1],aa[1]-bb[0];lo+=x;hi+=y;actual['both_terminal']+=a is not None and b is not None and a['reward']is not None and b['reward']is not None;actual['missing_pair']+=a is None or b is None;actual['paired_U']+=a is not None and b is not None and(a['reward']is None or b['reward']is None);cells.append(dict(seed=seed,family=family,color=color,foe=foe,bounds=[x,y],same_fullrecord=a is not None and b is not None and a['record']==b['record']))
 return dict(n=len(keys),bounds=[lo/max(1,len(keys)),hi/max(1,len(keys))],counts=dict(actual),cells=cells)
def run(directory):
 d=Path(directory);p=json.loads((d/'plan.json').read_text());e=json.loads((d/'eval-plan.json').read_text());t=json.loads((d/'result.json').read_text());ev=json.loads((d/'eval-result.json').read_text());rows={tuple(r['slot']):r for r in map(json.loads,(d/'eval-games.jsonl').open())};assert len(rows)==ev['actual'];pairs=[('TD','initial'),('TC','initial'),('WDL','initial'),('TC','TD'),('TD','WDL'),('TC','WDL')];out={}
 for left,right in pairs:
  key=left+'-'+right;out[key]=dict(all=contrast(rows,e['slots'],left,right),by_foe={f:contrast(rows,[s for s in e['slots']if s[5]==f],left,right)for f in e['foes']},by_seed={str(seed):{f:contrast(rows,[s for s in e['slots']if s[1]==seed and s[5]==f],left,right)for f in e['foes']}for seed in sorted({s[1]for s in e['slots']})},by_role={str(color):{f:contrast(rows,[s for s in e['slots']if s[3]==color and s[5]==f],left,right)for f in e['foes']}for color in [0,1]},by_family={str(family):contrast(rows,[s for s in e['slots']if s[2]==family],left,right)for family in sorted({s[2]for s in e['slots']})})
 training=defaultdict(Counter);losses=defaultdict(float);train_records=set();armweights={};updates=Counter();tc_rates={};terminal_kind=Counter()
 for g in map(json.loads,(d/'games.jsonl').open()):
  key=str((g['seed'],g['method']));training[key].update(dict(games=1,terminal=g['outcome']is not None,unknown=g['outcome']is None,queries=g['queries'],observed=g['observed'],terms=g['stats']['samples'],nodes=g['nodes'],actual_weight_change=g['weights']!=g['initial_weights']));training[key][g['ending']]+=1
  if g['stats']['loss']is not None:losses[key]+=g['stats']['loss']*g['stats']['samples']
  train_records.add(json.dumps(g['initial_record'],sort_keys=True,separators=(',',':')))
  if g['method']=='TC':tc_rates[str(g['seed'])]=g['stats']['rates_after']
 for r in map(json.loads,(d/'comparisons.jsonl').open()):updates[str(r['seed'])]+=r['accepted']
 roots={json.dumps(g['initial_record'],sort_keys=True,separators=(',',':'))for g in rows.values()};overlap=roots&train_records
 for a in t['arms']:armweights[str((a['seed'],a['method']))]=a['weights']
 summaries={key:dict(counts=dict(value),weighted_td_loss=losses[key]/max(1,value['terms']))for key,value in training.items()}
 orders={method:[sorted(range(5),key=lambda i:a['weights'][i])for a in t['arms']if a['method']==method]for method in ['TD','TC','WDL']};order_unanimity={key:len(value)==4 and len(set(map(tuple,value)))==1 for key,value in orders.items()}
 train_cost_by_method=defaultdict(Counter);eval_cost_by_treatment=defaultdict(Counter)
 for a in t['arms']:train_cost_by_method[a['method']].update(dict(nodes=a['nodes'],seconds=a['seconds'],games=a['games']))
 for row in rows.values():eval_cost_by_treatment[row['slot'][4]].update(dict(nodes=row['nodes'],queries=row['queries'],games=1,actual_terminal=row['outcome']is not None,unknown=row['outcome']is None))
 result=dict(status='COMPLETE_DERIVED_WITH_ALL_CENSORING',TRAIN=t,EVAL=ev,TRAIN_cost_by_method=dict(train_cost_by_method),EVAL_cost_by_treatment=dict(eval_cost_by_treatment),contrasts=out,train_arms=summaries,WDL_accepted_rounds=dict(updates),tc_final_rates=tc_rates,weight_order_unanimity=order_unanimity,exposure=dict(train_complete_initial_records=len(train_records),eval_complete_initial_records=len(roots),current_train_root_overlaps=len(overlap)),paid_nodes=t['nodes']+ev['nodes'],listed_producer_seconds=t['seconds']+ev['seconds'],scope='Finite registered panel W-L differences withUNKNOWN/missing [-1,1], not statisticalconfidence/equivalence or probabilitycalibration. All4initials/foes/roles paid, no DEVmodel/seed/rootselection. Source/engineering/audit/I-O outside listedproducerwall; actualqueryseconds andnodecostdistinct.')
 (d/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(paid_nodes=result['paid_nodes'],listed_producer_seconds=result['listed_producer_seconds'],eval=ev,contrasts={k:{f:v['bounds']for f,v in x['by_foe'].items()}for k,x in out.items()},exposure=result['exposure'],order_unanimity=order_unanimity)))
if __name__=='__main__':run(sys.argv[1])
