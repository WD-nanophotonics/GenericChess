"""Register DEV_AUX104 BEFORE fitness: SAME cold Generic Fixed TD on NEW 5x5 rules (one widened factor).

Decision rule (fixed here; pooled full paired bounds, U/missing=[-1,1]):
 LEARNS_5x5  if lower(Cold@100k - initial) > 0
 NO_GAIN     if upper(Cold@100k - initial) <= 0
 otherwise UNRESOLVED.
Admission: a generated rule whose non-anchor types differ from the panel channel set is recorded as an
admission failure and NOT replaced (no regeneration).
"""
from pathlib import Path
import json,random,hashlib,datetime,itertools
from generic_chess.generation.config import GeneratorConfig,GenerationError
from generic_chess.generation.generator import generate_game
from generic_chess.rules.schema import ruleset_to_dict
from results.dev_aux.task2588.run import channels_for
D=Path('results/dev_aux/task2588')
GEN=[356001,356002,356003,356004];SEEDS=[1977,8173,27182,31415];SNAP=[25000,50000,100000];BOARD=5
CODE=['results/dev_aux/task2588/run.py','results/dev_aux/task2588/register.py','results/dev_aux/task2588/bind.py','results/dev_aux/task2588/analyze.py','results/dev_aux/task2586/run.py','results/dev_aux/task2586/analyze.py','results/dev_aux/task2565/train.py','results/dev_aux/task2565/audit.py','results/dev_aux/task2565/verify.py','results/dev_aux/task2565/evaluate.py','results/dev_aux/task2525/run.py','results/dev_aux/task2511/generic.py','results/dev_aux/task2492/learning.py','results/dev_aux/task2492/episode.py','results/dev_aux/task2532/free_model.py','results/dev_aux/task2504/search.py','results/dev_aux/task2529/training_audit.py','results/dev_aux/task2529/incremental_replay.py','results/dev_aux/task2392/reader.py','generic_chess/generation/generator.py','generic_chess/generation/config.py','generic_chess/rules/compiler.py','generic_chess/session/session.py']
def sha(n):return hashlib.sha256(Path(n).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(path,obj):
 assert not path.exists(),path;path.write_text(json.dumps(obj,indent=2))
def run():
 s=json.loads(Path('.local_agent/session.json').read_text());assert s['state']=='active'
 rules=[];failures=[];admission=[];panel=None
 for gs in GEN:
  try:g=generate_game(GeneratorConfig(seed=gs,board_size=BOARD,max_generation_attempts=32))
  except GenerationError as e:failures.append(dict(generator_seed=gs,error=str(e)));continue
  types=sorted(t.type_id for t in g.ruleset.piece_types if not t.is_anchor);ch=channels_for(types)
  if panel is None:panel=ch
  if ch!=panel:admission.append(dict(generator_seed=gs,types=types,reason='channel set differs from panel'));continue
  path=D/f'rules-{gs}.json';assert not path.exists();path.write_text(json.dumps(ruleset_to_dict(g.ruleset),indent=2));rules.append(gs)
 assert panel is not None and len(panel)==6
 arms=[[gs,seed,'Fixed']for gs in rules for seed in SEEDS];random.Random(2588).shuffle(arms)
 plan=dict(session_id=s['id'],registered_at=now(),domain='generic',dimension=6,initial_seeds=SEEDS,methods=['Fixed'],arms_order=arms,nodes_per_arm=SNAP[-1],cap_seconds=3000,max_games=4096,foe=[1.]*6,depth=2,nodes_per_query=8192,seconds_per_query=2.0,H=128,prefix_plies=4,training_family_offset=356100,ordering_seed_offset=1002590000,eta=.05,**{'lambda':.95},snapshot_nodes=SNAP,
  pins={n:sha(n)for n in CODE if n!='results/dev_aux/task2588/analyze.py'},
  scope='ONE widened factor: board_size 5 (generator config otherwise default as in 102/103). NEW rules 356001-4. SAME task2565 Generic TD Fixed regime, cold seed-random initial, rule-derived channels '+repr(panel)+'. No selection/regeneration.')
 write(D/'generic'/'plan.json',plan)
 write(D/'audit-plan.json',dict(registered_at=now(),full_math_history=True,root_witness='First AND last complete observed query per training arm; mechanical.',unpruned_node_cap=600000,unpruned_seconds_cap=240,claim='Same rule authority unpruned validation.'))
 treatments=['Cold@0']+[f'Cold@{b//1000}k'for b in SNAP]
 foes=dict(uniform=[1.]*6,random99031=[1.0,1.4106491989128949,0.7659333865420771,1.136200535517595,0.6565261145043573,1.0420397060515065])
 slots=[[gs,seed,f,c,t,o]for gs,seed,f,c,t,o in itertools.product(rules,SEEDS,range(356801,356809),(0,1),treatments,foes)];random.Random(25880).shuffle(slots)
 write(D/'eval'/'eval-plan.json',dict(domain='generic',rules=rules,slots=slots,foes=foes,depth=2,nodes_per_query=8192,seconds_per_query=2.0,cap_seconds=3000,H=128,prefix_plies=4,ordering_seed_offset=1002591000,registered_before_any_fitness=True,
  scope='Actual legal terminal WLD; U/missing [-1,1]. Cold@0/25k/50k/100k x rules x 4 seeds x NEW families 356801-8 x 2 roles x 2 foes. random99031 is a fixed generic 6-vector applied positionally to the rule-derived channels.'))
 pins={n:sha(n)for n in CODE}
 for n in('generic/plan.json','audit-plan.json','eval/eval-plan.json')+tuple(f'rules-{gs}.json'for gs in rules):pins[f'results/dev_aux/task2588/{n}']=sha(D/n)
 write(D/'registration.json',dict(registered_at=now(),session_id=s['id'],executor='AUX_CLAUDE (Claude Code) in DEV_AUX checkout, user direction 2026-10-19',
  question='Does the SAME cold per-rule Generic Fixed TD improve actual WLD over initial when ONE domain factor widens to board_size 5?',
  dot_basis='DOT reply to 103a: next main direction (c), widen ONE domain factor with per-rule cold TD as baseline.',
  channels=[list(c)for c in panel],decision_rule=dict(LEARNS_5x5='lower(Cold@100k-initial)>0',NO_GAIN='upper(Cold@100k-initial)<=0',UNRESOLVED='otherwise',bounds='pooled full paired, U/missing=[-1,1]'),
  registered_contrasts=['Cold@B - Cold@0 for B in 25k,50k,100k','Cold@100k - Cold@25k','pooled/by foe/by rule/by seed + full T/U decomposition of Cold@100k - Cold@0'],
  generation_failures=failures,admission_failures=admission,rules=rules,
  expected_minutes='TRAIN 1.6M nodes ~15 min (smoke 1.8k nodes/s; cap 50) + EVAL 2048 games ~33 min (smoke 1.27 s/nonterminal game; cap 50) + audits ~5; under 120.',pre_fitness_root_description='Mechanical EVAL prefixes: 8 of 32 rule/family roots already terminal after <=4 random plies (rule-checked before registration, no fitness). Kept, not filtered: they add 0 to every paired contrast and lower sensitivity.',
  pins=pins,scientific_status='OPEN',no_new_fitness_yet=True))
 print(json.dumps(dict(rules=rules,failures=failures,admission=admission,channels=panel,arms=len(arms),slots=len(slots))))
if __name__=='__main__':run()
