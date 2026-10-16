from pathlib import Path
import json,hashlib,datetime
OUT=Path('results/dev_aux/task2366')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 sel=json.loads(Path('results/dev_aux/task2357/selection.json').read_text());assert sel['status']=='TRAIN_SELECTION_COMPLETE'and sel['selected_price']==1. and not sel['strict_improvement_accepted'];assert Path('results/dev_aux/task2355/completion.json').exists();c=json.loads((OUT/'pre-query-contract.json').read_text());start=datetime.datetime.fromisoformat(json.loads(Path('.local_agent/session.json').read_text())['started_at']);assert(datetime.datetime.now(datetime.timezone.utc)-start).total_seconds()+c['one_cap_seconds']+300<=5400
 rows=json.loads((OUT/'registered-roots.json').read_text());roots=[dict(index=r['family'],rules=r['rules'],record=r['record'],state_sha=r['state_sha'],group=r['group'],canonical_reference_label=r['target_label'],original_split='TRAIN')for r in rows];assert len(roots)==8
 def save(n,v):
  with(OUT/n).open('x')as f:json.dump(v,f,indent=2)
 save('inputs.json',roots);slots=[];grid=[.5,1.,1.5,2.,3.]
 for root in sorted(r['index']for r in roots):
  for color in(0,1):
   shift=(root+color)%5;prices=grid[shift:]+grid[:shift]
   for ratio in prices:slots.append(dict(slot=len(slots),matrix_slot=len(slots),root=root,opponent=0,candidate_color=color,ratio=ratio,arm='LOW_ONLY_INCREMENTAL'))
 save('slots.json',slots);p=json.loads(Path('results/dev_aux/task2355/plan.json').read_text());p.update(input=str(OUT/'inputs.json'),input_sha=sha(OUT/'inputs.json'),slots_sha=sha(OUT/'slots.json'),expected_games=80,one_cap_seconds=c['one_cap_seconds'],estimated_seconds=c['forecast_seconds']);p['opponents']=[dict(p['opponents'][0],ratio=2.)];p['selection']=c['selection'];p['scope']=c['scope']+' Compareprevious8onlymatchedfoe2subset ifdiscussingmu; do not attributepooledtwofoe aggregate differencepurelytomu.';names=['results/dev_aux/task2354/pilot.py','results/dev_aux/task2366/freeze.py','results/dev_aux/task2366/pre-query-contract.json','results/dev_aux/task2366/registered-roots.json','results/dev_aux/task2367/select.py','results/dev_aux/task2368/consume.py','results/dev_aux/task2357/selection.json','results/dev_aux/task2341/inputs.json','results/dev_aux/task2210/player.py','results/dev_aux/task2273/incremental_adapted.py','generic_chess/core/semantic_executor.py','generic_chess/session/session.py'];p['pins']={n:sha(n)for n in names};save('plan.json',p);print(json.dumps(dict(expected=80,roots=[r['index']for r in roots],foe=2,cap=1800,forecast=1400)))
if __name__=='__main__':run()
