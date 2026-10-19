"""Register DEV_AUX103 BEFORE fitness: warm (OldRulesMean) vs cold Fixed TD on NEW rules, same paid nodes.

Decision rule (fixed here, margin m=.0625, full paired bounds with U=[-1,1]):
 WARM_SAVES_DOSE  if lower(Warm@25k - Cold@100k) >= -m AND lower(Warm@100k - Cold@100k) >= -m
 WARM_WORSE       if upper(Warm@100k - Cold@100k) < 0
 otherwise UNRESOLVED -> keep cold random initialization as the default (no change).
"""
from pathlib import Path
import json,random,hashlib,datetime,itertools
from generic_chess.generation.config import GeneratorConfig,GenerationError
from generic_chess.generation.generator import generate_game
from generic_chess.rules.schema import ruleset_to_dict
D=Path('results/dev_aux/task2587');OLD=Path('results/dev_aux/task2565/generic/result.json')
GEN=[348001,348002,348003,348004];SEEDS=[1977,8173,27182,31415];SNAP=[25000,50000,100000];MARGIN=.0625
CODE=['results/dev_aux/task2587/train.py','results/dev_aux/task2587/audit.py','results/dev_aux/task2587/run.py','results/dev_aux/task2587/register.py','results/dev_aux/task2587/bind.py','results/dev_aux/task2587/analyze.py','results/dev_aux/task2586/run.py','results/dev_aux/task2565/train.py','results/dev_aux/task2565/audit.py','results/dev_aux/task2565/verify.py','results/dev_aux/task2565/evaluate.py','results/dev_aux/task2525/run.py','results/dev_aux/task2511/generic.py','results/dev_aux/task2492/learning.py','results/dev_aux/task2492/episode.py','results/dev_aux/task2532/free_model.py','results/dev_aux/task2504/search.py','results/dev_aux/task2529/training_audit.py','results/dev_aux/task2529/incremental_replay.py','results/dev_aux/task2392/reader.py','generic_chess/generation/generator.py','generic_chess/generation/config.py','generic_chess/rules/compiler.py','generic_chess/session/session.py',str(OLD).replace('\\','/')]
def sha(n):return hashlib.sha256(Path(n).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(path,obj):
 assert not path.exists(),path;path.write_text(json.dumps(obj,indent=2))
def old_means():
 old=json.loads(OLD.read_text());out={}
 for seed in SEEDS:
  ws=[a['weights']for a in old['arms']if a['method']=='Fixed'and a['seed']==seed];assert len(ws)==4;out[seed]=[sum(c)/4 for c in zip(*ws)]
 return out
def run():
 s=json.loads(Path('.local_agent/session.json').read_text());assert s['state']=='active'
 rules=[];failures=[]
 for gs in GEN:
  try:g=generate_game(GeneratorConfig(seed=gs,board_size=4,max_generation_attempts=32))
  except GenerationError as e:failures.append(dict(generator_seed=gs,error=str(e)));continue
  assert sorted(t.type_id for t in g.ruleset.piece_types if not t.is_anchor)==['A','P','X'],gs
  path=D/f'rules-{gs}.json';assert not path.exists();path.write_text(json.dumps(ruleset_to_dict(g.ruleset),indent=2));rules.append(gs)
 means=old_means()
 arms=[[gs,seed,m]for gs in rules for seed in SEEDS for m in('Fixed','FixedWarm')];random.Random(2587).shuffle(arms)
 plan=dict(session_id=s['id'],registered_at=now(),domain='generic',dimension=6,initial_seeds=SEEDS,methods=['Fixed','FixedWarm'],arms_order=arms,nodes_per_arm=SNAP[-1],cap_seconds=2400,max_games=4096,foe=[1.]*6,depth=2,nodes_per_query=8192,seconds_per_query=2.0,H=128,prefix_plies=4,training_family_offset=347000,ordering_seed_offset=1002588000,eta=.05,**{'lambda':.95},snapshot_nodes=SNAP,
  initial_weights={f'{gs}/{seed}':means[seed]for gs in rules for seed in SEEDS},
  pins={n:sha(n)for n in CODE if n!='results/dev_aux/task2587/analyze.py'},
  scope='NEW 4x4 rules 348001-4. SAME Generic TD Fixed regime (task2565 code; copies change ONLY FixedWarm initial). Fixed=cold seed-random initial; FixedWarm=per-seed OldRulesMean (mean of DEV_AUX96 Fixed endpoints on OLD rules 271001-4, no 102 data). Paired: same rule, seed, families, roots, foe, paid nodes. No selection.')
 write(D/'generic'/'plan.json',plan)
 write(D/'audit-plan.json',dict(registered_at=now(),full_math_history=True,root_witness='First AND last complete observed query per training arm; mechanical.',unpruned_node_cap=600000,unpruned_seconds_cap=180,claim='Same rule authority unpruned validation.'))
 treatments=['Cold@0','Warm@0']+[f'{x}@{b//1000}k'for x in('Cold','Warm')for b in SNAP]
 foes=dict(uniform=[1.]*6,random99031=[1.0,1.4106491989128949,0.7659333865420771,1.136200535517595,0.6565261145043573,1.0420397060515065])
 slots=[[gs,seed,f,c,t,o]for gs,seed,f,c,t,o in itertools.product(rules,SEEDS,range(347801,347809),(0,1),treatments,foes)];random.Random(25870).shuffle(slots)
 write(D/'eval'/'eval-plan.json',dict(domain='generic',rules=rules,slots=slots,foes=foes,depth=2,nodes_per_query=8192,seconds_per_query=2.0,cap_seconds=3000,H=128,prefix_plies=4,ordering_seed_offset=1002589000,registered_before_any_fitness=True,
  scope='Actual legal terminal WLD; U/missing [-1,1]. 8 models x 4 rules x 4 seeds x NEW families 347801-8 x 2 roles x 2 foes. Cold@0=seed initial, Warm@0=OldRulesMean.'))
 pins={n:sha(n)for n in CODE}
 for n in('generic/plan.json','audit-plan.json','eval/eval-plan.json')+tuple(f'rules-{gs}.json'for gs in rules):pins[f'results/dev_aux/task2587/{n}']=sha(D/n)
 write(D/'registration.json',dict(registered_at=now(),session_id=s['id'],executor='AUX_CLAUDE (Claude Code) in DEV_AUX checkout, user direction 2026-10-19',
  question='On NEW rules, does a warm start from OldRulesMean reach cold Fixed TD utility at less paid dose?',
  dot_basis='DOT_REPLY 1792402091.889509: fix a decision threshold before further evaluation; full pair decomposition, no outcome-selected subsets.',
  decision_rule=dict(margin=MARGIN,WARM_SAVES_DOSE='lower(Warm@25k-Cold@100k)>=-m AND lower(Warm@100k-Cold@100k)>=-m',WARM_WORSE='upper(Warm@100k-Cold@100k)<0',UNRESOLVED='otherwise; keep cold default',bounds='full registered pairs, U/missing=[-1,1], pooled over rules/seeds/families/roles/foes'),
  registered_contrasts=['Warm@B-Cold@B for B in 0,25k,50k,100k','Warm@25k-Cold@100k','Cold@100k-Cold@0','Warm@100k-Warm@0','each pooled/by foe/by rule/by seed + full T/U decomposition for the two decision contrasts'],
  generation_failures=failures,rules=rules,
  expected_minutes='TRAIN 3.2M nodes ~17 min (3.3k nodes/s; cap 40) + EVAL 4096 games ~34 min (smoke 0.5 s/game; cap 50) + audits ~5; under 120.',
  pins=pins,scientific_status='OPEN',no_new_fitness_yet=True))
 print(json.dumps(dict(rules=rules,failures=failures,arms=len(arms),slots=len(slots),pins=len(pins))))
if __name__=='__main__':run()
