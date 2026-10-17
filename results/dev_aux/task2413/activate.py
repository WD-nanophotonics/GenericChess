from pathlib import Path
import json,hashlib,datetime
root=Path.cwd();out=Path('results/dev_aux/task2413');reservation=json.loads((out/'reservation.json').read_text());selection=json.loads(Path('results/dev_aux/task2405/selection.json').read_text());baseline=[1.5,1.5]
if selection['selected']==baseline:
 (out/'inactive.json').write_text(json.dumps(dict(status='UNEXECUTED_CONDITION_FALSE',reason='TRAINselectedbaseline; noalternativelearnedprice',planned_slots=64,actual_games=0),indent=2));raise SystemExit(0)
assert not(out/'slots.json').exists();prices=[baseline,selection['selected']];slots=[]
for family in range(8):
 for role in(0,1):
  for opponent in(range(2)if(family+role)%2==0 else reversed(range(2))):
   for board,hand in(prices if(family+role+opponent)%2==0 else reversed(prices)):
    slots.append(dict(slot=len(slots),root=family,opponent=opponent,candidate_color=role,ratio=board,hand_ratio=hand,arm='LOW_ONLY_INCREMENTAL'))
(out/'slots.json').write_text(json.dumps(slots,indent=2));(out/'pilot.py').write_text(Path('results/dev_aux/task2401/pilot.py').read_text().replace("OUT=Path('results/dev_aux/task2401')","OUT=Path('results/dev_aux/task2413')"))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();p=json.loads(Path('results/dev_aux/task2401/plan.json').read_text());p.update(input='results/dev_aux/task2402/inputs.json',input_sha=sha('results/dev_aux/task2402/inputs.json'),slots_sha=sha(out/'slots.json'),expected_games=64,one_cap_seconds=reservation['cap_seconds'],forecast_seconds=reservation['forecast_seconds'],estimated_seconds=reservation['forecast_seconds'],scope=reservation['scope'],candidate_prices=prices,opponents=[dict(p['opponents'][0],ratio=x)for x in reservation['opponents']]);p['pins']={name:sha(name)for name in[(out/'pilot.py').as_posix(),(out/'reservation.json').as_posix(),'results/dev_aux/task2405/selection.json','results/dev_aux/task2397/material.py','results/dev_aux/task2392/reader.py','results/dev_aux/task2384/incremental.py']+[r['rules']for r in json.loads(Path(p['input']).read_text())]};(out/'plan.json').write_text(json.dumps(p,indent=2));print(json.dumps(dict(slots=len(slots),prices=prices,foes=reservation['opponents'],original_cap=p['one_cap_seconds'])))
