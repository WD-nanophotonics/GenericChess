"""Register DEV_AUX102 BEFORE any new fitness: NEW generated 4x4 rules, Fixednu TD curve, common EVAL.

Generates rules for NEW generator seeds once (no retry/outcome filter; failures recorded),
then writes generic/plan.json, audit-plan.json, eval/eval-plan.json, registration.json.
"""
from pathlib import Path
import json,random,hashlib,datetime,itertools
from generic_chess.generation.config import GeneratorConfig,GenerationError
from generic_chess.generation.generator import generate_game
from generic_chess.rules.schema import ruleset_to_dict
D=Path('results/dev_aux/task2586')
GEN=[351001,351002,351003,351004];SEEDS=[1977,8173,27182,31415];SNAP=[100000,200000,400000]
CODE=['results/dev_aux/task2565/train.py','results/dev_aux/task2565/audit.py','results/dev_aux/task2565/verify.py','results/dev_aux/task2565/evaluate.py','results/dev_aux/task2525/run.py','results/dev_aux/task2511/generic.py','results/dev_aux/task2492/learning.py','results/dev_aux/task2492/episode.py','results/dev_aux/task2532/free_model.py','results/dev_aux/task2504/search.py','results/dev_aux/task2529/training_audit.py','results/dev_aux/task2529/incremental_replay.py','results/dev_aux/task2392/reader.py','results/dev_aux/task2568/summary.py','generic_chess/generation/generator.py','generic_chess/generation/config.py','generic_chess/rules/compiler.py','generic_chess/session/session.py','results/dev_aux/task2565/generic/result.json','results/dev_aux/task2586/run.py','results/dev_aux/task2586/register.py','results/dev_aux/task2586/bind.py','results/dev_aux/task2586/analyze.py']
def sha(n):return hashlib.sha256(Path(n).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(path,obj):
 assert not path.exists(),path;path.write_text(json.dumps(obj,indent=2))
def run():
 s=json.loads(Path('.local_agent/session.json').read_text());assert s['state']=='active'
 rules=[];failures=[]
 for gs in GEN:
  try:g=generate_game(GeneratorConfig(seed=gs,board_size=4,max_generation_attempts=32))
  except GenerationError as e:failures.append(dict(generator_seed=gs,error=str(e)));continue
  path=D/f'rules-{gs}.json';assert not path.exists();path.write_text(json.dumps(ruleset_to_dict(g.ruleset),indent=2));rules.append(gs)
  assert sorted(t.type_id for t in g.ruleset.piece_types if not t.is_anchor)==['A','P','X'],gs
 arms=[[gs,seed,'Fixed']for gs in rules for seed in SEEDS];random.Random(2586).shuffle(arms)
 plan=dict(session_id=s['id'],registered_at=now(),domain='generic',dimension=6,initial_seeds=SEEDS,methods=['Fixed'],arms_order=arms,nodes_per_arm=SNAP[-1],cap_seconds=3000,max_games=8192,foe=[1.]*6,depth=2,nodes_per_query=8192,seconds_per_query=2.0,H=128,prefix_plies=4,training_family_offset=341000,ordering_seed_offset=1002586000,eta=.05,**{'lambda':.95},snapshot_nodes=SNAP,
  pins={n:sha(n)for n in CODE if n!='results/dev_aux/task2586/analyze.py'},
  scope='NEW generated 4x4 rules (generator seeds 351001-4, never used by DEV_AUX/PRIMARY plans), full GameSession semantics incl promotion/drops/current board/base hand/history. SAME task2565 Generic TD (6 free signed channel coefficients, eta.05/lambda.95, D2 plain, H128, prefix4) Fixed regime only: candidate alternates roles vs fixed uniform nu. All4initials. Equal paid nodes incl foe/failed. No human prior, no seed/checkpoint/rule selection; generator soft playability only, no outcome filter or regeneration.')
 write(D/'generic'/'plan.json',plan)
 write(D/'audit-plan.json',dict(registered_at=now(),full_math_history=True,root_witness='First AND last complete observed query per training arm; mechanical, not by outcome.',unpruned_node_cap=600000,unpruned_seconds_cap=180,claim='Same rule authority/sample unpruned validation, not independent engine or all-domain proof.'))
 treatments=['initial']+[f'Fixed@{b//1000}k'for b in SNAP]+['OldRulesMean']
 foes=dict(uniform=[1.]*6,random99031=[1.0,1.4106491989128949,0.7659333865420771,1.136200535517595,0.6565261145043573,1.0420397060515065])
 families=list(range(345001,345009))
 slots=[[gs,seed,f,c,t,o]for gs,seed,f,c,t,o in itertools.product(rules,SEEDS,families,(0,1),treatments,foes)];random.Random(25860).shuffle(slots)
 (D/'eval').mkdir(exist_ok=True)
 write(D/'eval'/'eval-plan.json',dict(domain='generic',rules=rules,slots=slots,foes=foes,depth=2,nodes_per_query=8192,seconds_per_query=2.0,cap_seconds=2400,H=128,prefix_plies=4,ordering_seed_offset=1002587000,registered_before_any_fitness=True,
  treatments=dict(initial='each seed initial weights',**{f'Fixed@{b//1000}k':f'last closed Fixed episode <= {b} paid nodes on THIS rule'for b in SNAP},OldRulesMean='per-seed arithmetic mean of the 4 DEV_AUX96 Fixed 150k endpoints trained on OLD rules 271001-4 (task2565/generic/result.json); zero new training on the NEW rule (cross-rule price transfer)'),
  scope='Actual legal terminal WLD only; H/resource/missing UNKNOWN bounded [-1,1]. Same fixed foes (DEV_AUX96 uniform/random99031), roles, NEW families 345001-8 for all models. No selection. Repeated roots across models/seeds are not independent samples.'))
 pins={n:sha(n)for n in CODE}
 for n in('generic/plan.json','audit-plan.json','eval/eval-plan.json')+tuple(f'rules-{gs}.json'for gs in rules):pins[str(D/n).replace('\\','/')]=sha(D/n)
 write(D/'registration.json',dict(registered_at=now(),session_id=s['id'],executor='AUX_CLAUDE (Claude Code) in DEV_AUX checkout, user direction 2026-10-19',
  question='Does the SAME Generic TD learner (Fixednu regime) improve actual WLD over initial on NEW unseen generated full-semantics rules, and do prices learned on OTHER rules (OldRulesMean) transfer without retraining?',
  dot_basis='DOT_REPLY 1792397818.663009 ranked (a) small full-semantics Generic transfer with Fixednu control first; executable + separating candidates before scaling.',
  generation_failures=failures,rules=rules,
  registered_contrasts=['Fixed@B - initial, B in 100k/200k/400k','Fixed@400k - Fixed@100k (curve)','OldRulesMean - initial','Fixed@400k - OldRulesMean','each pooled/by rule/by foe/by seed/by role; finite paired bounds, U=[-1,1]'],
  expected_minutes='TRAIN 6.4M nodes est ~33 min (smoke 3.3k nodes/s; hard cap 50) + EVAL 2560 games est ~26 min (smoke 0.6 s/game; hard cap 40) + audits ~5; total well under 120.',
  pins=pins,scientific_status='OPEN',no_new_fitness_yet=True))
 print(json.dumps(dict(rules=rules,failures=failures,arms=len(arms),slots=len(slots),pins=len(pins))))
if __name__=='__main__':run()
