from pathlib import Path
import json,hashlib,datetime
OUT=Path('results/dev_aux/task2362')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 c=json.loads((OUT/'pre-query-contract.json').read_text());selector=Path('results/dev_aux/task2357/selection.json');sel=json.loads(selector.read_text());assert sel['status']=='TRAIN_SELECTION_COMPLETE'
 if not sel['strict_improvement_accepted']:
  extension=json.loads((OUT/'fallback-extension.json').read_text());selector=Path(extension['selector']);sel=json.loads(selector.read_text());assert sel['status']=='TRAIN_SELECTION_COMPLETE'and sel['strict_improvement_accepted'];c=dict(c,one_cap_seconds=extension['one_cap_seconds'],forecast_seconds=extension['forecast_seconds'],scope=c['scope']+' FOLLOWUP_ROUTE: '+extension['explanation'])
 assert sel['strict_improvement_accepted'];assert Path('results/dev_aux/task2355/completion.json').exists();start=datetime.datetime.fromisoformat(json.loads(Path('.local_agent/session.json').read_text())['started_at']);assert (datetime.datetime.now(datetime.timezone.utc)-start).total_seconds()+c['one_cap_seconds']+300<=5400
 data=json.loads(Path(c['input']).read_text());assert sha(c['input'])==c['input_sha'];roots=[dict(index=r['family'],rules=r['rules'],record=r['record'],state_sha=r['state_sha'],group=r['group'],canonical_reference_label=r['target_label'],original_split='PREFIT2341_PRICE_UNQUERIED_RESERVE')for r in data['roots']];assert len(roots)==16;price=float(sel['selected_price']);assert price!=1.
 def save(n,v):
  with(OUT/n).open('x')as f:json.dump(v,f,indent=2)
 save('inputs.json',roots);slots=[]
 for root in range(16):
  for opponent in range(2):
   for color in(0,1):
    for ratio in((1.,price)if(root+opponent+color)%2==0 else(price,1.)):slots.append(dict(slot=len(slots),root=root,opponent=opponent,candidate_color=color,ratio=ratio,arm='LOW_ONLY_INCREMENTAL'))
 save('slots.json',slots);p=json.loads(Path('results/dev_aux/task2331/plan.json').read_text());p.update(input=str(OUT/'inputs.json'),input_sha=sha(OUT/'inputs.json'),slots_sha=sha(OUT/'slots.json'),expected_games=128,one_cap_seconds=c['one_cap_seconds'],estimated_seconds=c['forecast_seconds'],candidate_prices=[1.,price]);p['selection']='ALL16prefit2341reservefamilies/foes1.5,4/roles, baseline1 vs ONLYfrozenactualTRAINselectedprice. Adjacentpairs paritybalanced, noadaptation/refit fromreserveoutcomes.';p['scope']=c['scope'];p['selector_source']=str(selector);names=['results/dev_aux/task2354/pilot.py','results/dev_aux/task2362/freeze.py','results/dev_aux/task2362/pre-query-contract.json','results/dev_aux/task2357/select.py',str(selector),'results/dev_aux/task2362/fallback-extension.json','results/dev_aux/task2341/inputs.json','results/dev_aux/task2341/exposure-correction.json','results/dev_aux/task2363/consume.py','results/dev_aux/task2364/analyze.py','results/dev_aux/task2210/player.py','results/dev_aux/task2273/incremental_adapted.py','generic_chess/core/semantic_executor.py','generic_chess/session/session.py'];names+=['results/dev_aux/task2355/plan.json','results/dev_aux/task2358/plan.json','results/dev_aux/task2359/result.json']
 if selector.parent.name=='task2367':names+=['results/dev_aux/task2367/select.py','results/dev_aux/task2366/plan.json']
 p['pins']={n:sha(n)for n in names};save('plan.json',p);print(json.dumps(dict(expected=128,baseline=1.,candidate=price,cap=c['one_cap_seconds'],forecast=c['forecast_seconds'])))
if __name__=='__main__':run()
