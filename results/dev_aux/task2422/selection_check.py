"""Independent closed-table selection/provenance audit; no fitter or new fitness."""
from pathlib import Path
from datetime import datetime
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state,orbit
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2422')
def run():
 tick=time.perf_counter();stop=SharedDeleteStopReader(Path.cwd());stop();read=lambda p:json.loads(Path(p).read_text());f=Path('results/dev_aux/task2401');p=read(f/'plan.json');registration=read(f/'registration.json');slots=read(f/'slots.json');records=[json.loads(x)for x in(f/'games.jsonl').read_text().splitlines()];games={g['slot']:g for g in records};assert len(games)==len(records);selection=read('results/dev_aux/task2405/selection.json');values={};counts={}
 for price in registration['train_grid']:
  subset=[s for s in slots if[s['ratio'],s['hand_ratio']]==price];assert len(subset)==16 and len(set((s['root'],s['candidate_color'])for s in subset))==16;lo=hi=0
  for s in subset:
   g=games.get(s['slot']);r=None if g is None else g['reward'];lo+=-1 if r is None else r;hi+=1 if r is None else r
  values[tuple(price)]=(lo/16,hi/16)
 base=tuple(registration['baseline']);eligible=[x for x,v in values.items()if v[0]>values[base][1]];expected=min(eligible,key=lambda x:(-values[x][0],x))if eligible else base;assert list(expected)==selection['selected'];assert hashlib.sha256((f/'games.jsonl').read_bytes()).hexdigest()==selection['train_games_sha']
 for row in selection['rows']:assert list(values[tuple(row['price'])])==row['bounds']
 def instant(t):return datetime.fromisoformat(t)
 reserve=Path('results/dev_aux/task2402');reserve_registration=read(reserve/'reservation.json');assert instant(reserve_registration['utc'])<instant(read(f/'started.json')['utc'])<instant(selection['utc'])<instant(read(reserve/'started.json')['utc'])
 def group(row):
  stop();c=compile_ruleset_for_execution(deserialize_ruleset(Path(row['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));assert all(not h.counts for h in s.state.position.hands);return min(repr(x)for x in orbit(tuple(actor_state(s.state))))
 prior=read('results/dev_aux/task2358/inputs.json')+read('results/dev_aux/task2341/inputs.json')['roots'];old={group(r)for r in prior};newrows=read(reserve/'inputs.json');new=[group(r)for r in newrows];assert len(new)==len(set(new))==8 and not set(new)&old;assert all(g==r['group']for g,r in zip(new,newrows))
 cap_expected={2401:2400,2402:900,2413:1800,2420:900};caps=[]
 for task,cap in cap_expected.items():
  q=read(f'results/dev_aux/task{task}/plan.json');assert q['one_cap_seconds']==cap;caps.append(dict(task=task,original_cap=cap,forecast=q['forecast_seconds']))
 assert sum(c['forecast']for c in caps)+360<7200;assert sum(c['original_cap']for c in caps)+360+30<7200
 out=dict(status='PASS_CLOSED_SELECTOR_AND_PREFIT_PROVENANCE',actual_selected=list(expected),finite_candidate_bounds=[dict(price=list(k),bounds=list(v))for k,v in values.items()],reserved_initial_orbits=8,excluded_old_initial_orbits=len(old),reserve_registration_before_TRAIN_before_selection_before_reserve_start=True,caps=caps,whole_logical_forecast_including_two180sdiagnostics=sum(c['forecast']for c in caps)+360,whole_max_frozen_caps_plus2diagnostics_and_gate=sum(c['original_cap']for c in caps)+390,seconds=time.perf_counter()-tick,scope='Independent arithmetic/provenance/initialorbit audit, notnewfitter/fitness/teacherlabelqueries. New8initialorbits excludedoldTRAIN+82Conly, NOTallhistoricaltrajectories/rules orunseenreferenceknowledge. Sameconditionalprice/parameters/caps, nooutcomesreplacedbysuccess.')
 (OUT/'result.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
