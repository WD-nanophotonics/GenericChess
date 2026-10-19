"""Register DEV_AUX108 BEFORE fitness: SAME cold Generic Fixed TD on NEW 4x4 rules with ONE pre-fixed
movement-generator change (leap-only: leap_probability=1.0, ray_probability=0.0; all else default), P/A/X channels unchanged.

Per Dot 1792414510.091249: one fixed configuration, no grid; initial vs ONE fixed endpoint (Cold@100k);
held-out EVAL roots fixed before fitness; per-rule results reported.
Held-out rule (mechanical): per rule, EVAL families = first 8 codes from 364600 upward whose 4-ply root
record is NOT among the TRAIN root records of families 364100..364599 (TRAIN uses 364100+index//2).
Terminal roots are kept and reported.
Decision (pooled full paired bounds, U/missing=[-1,1]):
 LEARNS_LEAP if lower(Cold@100k-Cold@0)>0; NO_GAIN if upper<=0; else UNRESOLVED.
Per rule (reported, not pooled away): count rules with lower>0, upper<0, undetermined.
"""
from pathlib import Path
import json,random,hashlib,datetime,itertools
from generic_chess.generation.config import GeneratorConfig,GenerationError
from generic_chess.generation.generator import generate_game
from generic_chess.rules.schema import ruleset_to_dict,ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset
import results.dev_aux.task2565.train as T
D=Path('results/dev_aux/task2592')
GEN=[364001,364002,364003,364004];SEEDS=[1977,8173,27182,31415];CONFIG=dict(board_size=4,leap_probability=1.0,ray_probability=0.0,max_generation_attempts=32)
TRAIN_OFF=364100;TRAIN_SPAN=500;EVAL_START=364600
CODE=['results/dev_aux/task2592/run.py','results/dev_aux/task2592/register.py','results/dev_aux/task2592/bind.py','results/dev_aux/task2592/analyze.py','results/dev_aux/task2586/run.py','results/dev_aux/task2586/analyze.py','results/dev_aux/task2587/analyze.py','results/dev_aux/task2565/train.py','results/dev_aux/task2565/audit.py','results/dev_aux/task2565/verify.py','results/dev_aux/task2565/evaluate.py','results/dev_aux/task2525/run.py','results/dev_aux/task2511/generic.py','results/dev_aux/task2492/learning.py','results/dev_aux/task2492/episode.py','results/dev_aux/task2532/free_model.py','results/dev_aux/task2504/search.py','results/dev_aux/task2529/training_audit.py','results/dev_aux/task2529/incremental_replay.py','results/dev_aux/task2392/reader.py','generic_chess/generation/generator.py','generic_chess/generation/config.py','generic_chess/rules/compiler.py','generic_chess/session/session.py']
def sha(n):return hashlib.sha256(Path(n).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(path,obj):
 assert not path.exists(),path;path.write_text(json.dumps(obj,indent=2))
def root(gs,cc,f):
 e=T.environment(gs,cc);T.prefix(e,gs,f,4);return json.dumps(e.record(),sort_keys=True),e.terminal()is not None
def run():
 s=json.loads(Path('.local_agent/session.json').read_text());assert s['state']=='active'
 rules=[];failures=[];admission=[];heldout={};terminal_roots={}
 for gs in GEN:
  try:g=generate_game(GeneratorConfig(seed=gs,**CONFIG))
  except GenerationError as e:failures.append(dict(generator_seed=gs,error=str(e)));continue
  types=sorted(t.type_id for t in g.ruleset.piece_types if not t.is_anchor)
  if types!=['A','P','X']:admission.append(dict(generator_seed=gs,types=types));continue
  d=ruleset_to_dict(g.ruleset);path=D/f'rules-{gs}.json';assert not path.exists();path.write_text(json.dumps(d,indent=2));rules.append(gs)
  cc=compile_ruleset(ruleset_from_dict(d));train={root(gs,cc,TRAIN_OFF+i)[0]for i in range(TRAIN_SPAN)};chosen=[];term=[];f=EVAL_START
  while len(chosen)<8:
   r,t=root(gs,cc,f)
   if r not in train:chosen.append(f);term.append(t)
   f+=1;assert f<EVAL_START+5000
  heldout[str(gs)]=chosen;terminal_roots[str(gs)]=sum(term)
 arms=[[gs,seed,'Fixed']for gs in rules for seed in SEEDS];random.Random(2592).shuffle(arms)
 plan=dict(session_id=s['id'],registered_at=now(),domain='generic',dimension=6,initial_seeds=SEEDS,methods=['Fixed'],arms_order=arms,nodes_per_arm=100000,cap_seconds=2400,max_games=4096,foe=[1.]*6,depth=2,nodes_per_query=8192,seconds_per_query=2.0,H=128,prefix_plies=4,training_family_offset=TRAIN_OFF,ordering_seed_offset=1002594000,eta=.05,**{'lambda':.95},snapshot_nodes=[100000],
  pins={n:sha(n)for n in CODE if n!='results/dev_aux/task2592/analyze.py'},
  scope='ONE pre-fixed movement-generator change: leap_probability=1.0,ray_probability=0.0 (leap-only) on 4x4, all else default; P/A/X channels unchanged. NEW rules 364001-4. SAME task2565 Generic TD Fixed regime, cold seed-random initial, 100k paid nodes. No selection/regeneration.')
 write(D/'generic'/'plan.json',plan)
 write(D/'audit-plan.json',dict(registered_at=now(),full_math_history=True,root_witness='First AND last complete observed query per training arm; mechanical.',unpruned_node_cap=600000,unpruned_seconds_cap=180,claim='Same rule authority unpruned validation.'))
 foes=dict(uniform=[1.]*6,random99031=[1.0,1.4106491989128949,0.7659333865420771,1.136200535517595,0.6565261145043573,1.0420397060515065])
 slots=[[gs,seed,f,c,t,o]for gs in rules for seed,f,c,t,o in itertools.product(SEEDS,heldout[str(gs)],(0,1),('Cold@0','Cold@100k'),foes)];random.Random(25920).shuffle(slots)
 write(D/'eval'/'eval-plan.json',dict(domain='generic',rules=rules,slots=slots,foes=foes,depth=2,nodes_per_query=8192,seconds_per_query=2.0,cap_seconds=2400,H=128,prefix_plies=4,ordering_seed_offset=1002595000,registered_before_any_fitness=True,heldout_families=heldout,
  scope='Actual legal terminal WLD; U/missing [-1,1]. Cold@0 vs Cold@100k x 4 rules x 4 seeds x 8 HELD-OUT families per rule (roots not among TRAIN families 364100..364599) x 2 roles x 2 foes.'))
 pins={n:sha(n)for n in CODE}
 for n in('generic/plan.json','audit-plan.json','eval/eval-plan.json')+tuple(f'rules-{gs}.json'for gs in rules):pins[f'results/dev_aux/task2592/{n}']=sha(D/n)
 write(D/'registration.json',dict(registered_at=now(),session_id=s['id'],executor='AUX_CLAUDE (Claude Code) in DEV_AUX checkout, user direction 2026-10-19',
  question='Does the SAME cold per-rule Generic TD re-learn a gain under ONE pre-fixed unfamiliar movement configuration (leap-only, 4x4, P/A/X)?',
  dot_basis='DOT_REPLY 1792414510.091249: 4x4 fixed P/A/X movement-generator change, one pre-fixed config, initial vs one endpoint, held-out roots fixed before fitness, per-rule reporting. Second pre-fixed config = candidate (1) of Slack 107a; Dot silent >12 min twice, so chosen by AUX_CLAUDE as the cheapest decision-relevant option (how common are per-rule failures).',
  generator_config=CONFIG,decision_rule=dict(pooled='LEARNS_LEAP if lower(Cold@100k-Cold@0)>0; NO_GAIN if upper<=0; else UNRESOLVED',per_rule='report counts lower>0 / upper<0 / undetermined; no pooling away failures'),
  heldout_rule=f'per rule first 8 families >= {EVAL_START} whose 4-ply root not among TRAIN families {TRAIN_OFF}..{TRAIN_OFF+TRAIN_SPAN-1}',heldout_families=heldout,terminal_heldout_roots=terminal_roots,
  generation_failures=failures,admission_failures=admission,rules=rules,
  expected_minutes='TRAIN 1.6M nodes ~10 min (4x4 measured 3.0-3.3k nodes/s; cap 40) + EVAL 1024 games ~8 min (4x4 measured 0.42-0.45 s/game; cap 40) + audits ~3; well under 120.',
  pins=pins,scientific_status='OPEN',no_new_fitness_yet=True))
 print(json.dumps(dict(rules=rules,failures=failures,admission=admission,heldout=heldout,terminal=terminal_roots,arms=len(arms),slots=len(slots))))
if __name__=='__main__':run()
