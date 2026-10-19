"""Register DEV_AUX107 BEFORE fitness: mechanism probe on hybrid rule 363001 (lambda 0.95 -> 1.0 ONLY).

Motivation: task2590/credit-split.json found 363001 heuristic-bootstrap dominated (ratio .78-1.41 on all seeds).
Dot 1792416458.862699: if a strong mechanism is found, do ONE minimal targeted check. This changes a learner
hyperparameter, so it is a MECHANISM PROBE, not the SAME-learner claim.
Everything else identical to task2590 for rule 363001: rule file (byte copy), seeds, cold initial, 100k paid nodes,
training_family_offset, ordering_seed_offset, foe, depth, H, prefix; EVAL slots/ordering identical to task2590 so the
existing task2590 Cold@0 and Cold@100k games are the paired comparison (not re-run).
Decision (pooled over 363001 slots, full paired bounds, U=[-1,1]):
 FLIP if lower(Lam1@100k - Cold@0) > 0; NO_FLIP if upper(Lam1@100k - Cold@0) <= 0; else UNRESOLVED.
 Also reported: Lam1@100k - Cold@100k(lambda .95).
"""
from pathlib import Path
import json,hashlib,datetime,random
A=Path('results/dev_aux/task2590');D=Path('results/dev_aux/task2591');GS=363001
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(path,obj):
 assert not path.exists(),path;path.write_text(json.dumps(obj,indent=2))
def run():
 s=json.loads(Path('.local_agent/session.json').read_text());assert s['state']=='active';assert sha(A/f'rules-{GS}.json')==sha(D/f'rules-{GS}.json')
 base=json.loads((A/'generic'/'plan.json').read_text());plan=dict(base);plan['session_id']=s['id'];plan['registered_at']=now();plan['arms_order']=[a for a in base['arms_order']if a[0]==GS];plan['lambda']=1.0
 code=['results/dev_aux/task2591/run.py','results/dev_aux/task2591/register.py','results/dev_aux/task2591/bind.py','results/dev_aux/task2591/analyze.py','results/dev_aux/task2586/run.py','results/dev_aux/task2586/analyze.py','results/dev_aux/task2587/analyze.py','results/dev_aux/task2565/train.py','results/dev_aux/task2565/audit.py','results/dev_aux/task2565/verify.py','results/dev_aux/task2565/evaluate.py','results/dev_aux/task2492/episode.py','results/dev_aux/task2504/search.py']
 plan['pins']={n:sha(n)for n in code if n!='results/dev_aux/task2591/analyze.py'};plan['scope']='MECHANISM PROBE: task2590 rule 363001 arms with lambda 1.0 instead of .95; all else identical (same families/ordering, cold initial, 100k).'
 write(D/'generic'/'plan.json',plan)
 write(D/'audit-plan.json',json.loads((A/'audit-plan.json').read_text()))
 ep=json.loads((A/'eval'/'eval-plan.json').read_text());e=dict(ep);e['rules']=[GS]
 e['slots']=[[x[0],x[1],x[2],x[3],'Lam1@100k',x[5]]for x in ep['slots']if x[0]==GS and x[4]=='Cold@100k'];e['heldout_families']={str(GS):ep['heldout_families'][str(GS)]}
 e['scope']='Lam1@100k on exactly the task2590 rule-363001 Cold@100k slot keys (same roots/foes/roles/ordering); comparison rows reused from task2590.'
 write(D/'eval'/'eval-plan.json',e)
 pins={n:sha(n)for n in code}
 for n in('generic/plan.json','audit-plan.json','eval/eval-plan.json',f'rules-{GS}.json'):pins[f'results/dev_aux/task2591/{n}']=sha(D/n)
 for n in('eval/eval-games.jsonl','eval/eval-plan.json','eval/result.json','generic/result.json','credit-split.json'):pins[f'results/dev_aux/task2590/{n}']=sha(A/n)
 write(D/'registration.json',dict(registered_at=now(),session_id=s['id'],executor='AUX_CLAUDE (Claude Code) in DEV_AUX checkout, user direction 2026-10-19',
  question='Does concentrating TD credit on outcome-seen steps (lambda 1.0) flip the 363001 learning sign?',basis='task2590 credit-split heuristic dominance; Dot 1792416458.862699 minimal targeted check rule. Dot follow-up split1 unanswered after 10 min; run is <120 min (no prior review needed).',
  decision_rule='FLIP if lower(Lam1@100k-Cold@0)>0; NO_FLIP if upper<=0; else UNRESOLVED; also Lam1@100k-Cold@100k reported.',
  expected_minutes='TRAIN 400k nodes ~2.5 min + EVAL 128 games ~1 min + audits; well under 120.',pins=pins,scientific_status='OPEN',no_new_fitness_yet=True))
 print(json.dumps(dict(arms=plan['arms_order'],slots=len(e['slots']),lam=plan['lambda'])))
if __name__=='__main__':run()
