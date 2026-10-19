"""Register DEV_AUX105 BEFORE running: completion of EXACTLY the slots missing from DEV_AUX104 EVAL.

Same bound models (task2588/eval/result.json copied byte-identical), roots, foes, depth, query caps and
ordering_seed_offset as task2588/eval/eval-plan.json; only the slot list is the missing subset and the
global cap is new. task2588 games stay unchanged. The task2588 registered decision rule is re-applied to the
union by task2589/union.py (pinned here).
"""
from pathlib import Path
import json,hashlib,datetime,shutil
A=Path('results/dev_aux/task2588');D=Path('results/dev_aux/task2589')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,obj):
 assert not path.exists(),path;path.write_text(json.dumps(obj,indent=2))
def run():
 s=json.loads(Path('.local_agent/session.json').read_text());assert s['state']=='active'
 ep=json.loads((A/'eval'/'eval-plan.json').read_text());done={tuple(json.loads(l)['slot'])for l in(A/'eval'/'eval-games.jsonl').open()}
 missing=[x for x in ep['slots']if tuple(x)not in done];assert len(missing)+len(done)==len(ep['slots'])
 plan=dict(ep);plan['slots']=missing;plan['cap_seconds']=2400;plan['completion_of']=str(A/'eval'/'eval-plan.json').replace('\\','/');plan['completion_of_sha']=sha(A/'eval'/'eval-plan.json');plan['scope']='Completion of exactly the '+str(len(missing))+' DEV_AUX104 slots missing at its PARTIAL_CAP; everything else identical; existing 104 games unchanged.'
 (D/'eval').mkdir(parents=True,exist_ok=True);write(D/'eval'/'eval-plan.json',plan);dst=D/'eval'/'result.json';assert not dst.exists();shutil.copyfile(A/'eval'/'result.json',dst)
 pins={n:sha(n)for n in['results/dev_aux/task2589/register.py','results/dev_aux/task2589/union.py','results/dev_aux/task2588/run.py','results/dev_aux/task2588/registration.json','results/dev_aux/task2588/eval/eval-plan.json','results/dev_aux/task2588/eval/result.json','results/dev_aux/task2588/eval/eval-games.jsonl','results/dev_aux/task2588/eval/eval-result.json','results/dev_aux/task2589/eval/eval-plan.json','results/dev_aux/task2589/eval/result.json','results/dev_aux/task2565/evaluate.py','results/dev_aux/task2565/verify.py','results/dev_aux/task2586/analyze.py','results/dev_aux/task2587/analyze.py']}
 write(D/'registration.json',dict(registered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),session_id=s['id'],executor='AUX_CLAUDE (Claude Code) in DEV_AUX checkout, user direction 2026-10-19',
  question='Re-apply the DEV_AUX104 registered LEARNS_5x5 rule to the union of 104 games and the completed missing slots.',
  missing_slots=len(missing),by_model={m:sum(x[4]==m for x in missing)for m in sorted({x[4]for x in missing})},
  expected_minutes=f'{len(missing)} games x ~1.97 s (104 actual rate) ~ {round(len(missing)*1.97/60)} min; cap 40 min; under 120.',
  decision_rule='task2588 registration: LEARNS_5x5 if lower(Cold@100k-Cold@0)>0; NO_GAIN if upper<=0; else UNRESOLVED; pooled full paired bounds over the union.',
  pins=pins,scientific_status='OPEN',no_new_fitness_yet=True))
 print(json.dumps(dict(missing=len(missing),done=len(done))))
if __name__=='__main__':run()
