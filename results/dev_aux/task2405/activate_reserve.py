from pathlib import Path
import json,hashlib,datetime
root=Path.cwd();out=Path('results/dev_aux/task2402');selection=json.loads(Path('results/dev_aux/task2405/selection.json').read_text());reserve=json.loads((out/'reservation.json').read_text());prices=[reserve['baseline']]
if selection['selected']!=reserve['baseline']:prices.append(selection['selected'])
slots=[]
for family in range(8):
 for role in(0,1):
  for board,hand in(prices if(family+role)%2==0 else reversed(prices)):
   slots.append(dict(slot=len(slots),root=family,opponent=0,candidate_color=role,ratio=board,hand_ratio=hand,arm='LOW_ONLY_INCREMENTAL'))
with(out/'slots.json').open('x')as f:json.dump(slots,f,indent=2)
source=Path('results/dev_aux/task2401/pilot.py').read_text().replace("OUT=Path('results/dev_aux/task2401')","OUT=Path('results/dev_aux/task2402')")
with(out/'pilot.py').open('x')as f:f.write(source)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();p=json.loads(Path('results/dev_aux/task2401/plan.json').read_text());p.update(input=(out/'inputs.json').as_posix(),input_sha=sha(out/'inputs.json'),slots_sha=sha(out/'slots.json'),expected_games=len(slots),one_cap_seconds=reserve['reserve_cap'],estimated_seconds=reserve['reserve_forecast'],forecast_seconds=reserve['reserve_forecast'],scope=reserve['scope']+' NEW8price-prefitreservedinitialorbits nowexposed; samefixedfoe2 andcandidatepolicy. Baseline+immutableTRAINselectiononly; ifbaselinewinsselectoronlyonearm andno improvementcontrast.',candidate_prices=prices)
p['pins']={name:sha(name)for name in[(out/'pilot.py').as_posix(),'results/dev_aux/task2392/reader.py','results/dev_aux/task2397/material.py','results/dev_aux/task2384/incremental.py','results/dev_aux/task2405/selection.json',(out/'reservation.json').as_posix()]+[r['rules']for r in json.loads((out/'inputs.json').read_text())]}
with(out/'plan.json').open('x')as f:json.dump(p,f,indent=2)
print(json.dumps(dict(expected=len(slots),prices=prices,original_reserve_cap=p['one_cap_seconds'],utc=datetime.datetime.now(datetime.timezone.utc).isoformat())))
