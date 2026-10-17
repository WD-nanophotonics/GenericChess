"""Verify frozen stochastic root draws and measure actual full-record reuse."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,random,time
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2525.run import RecordedSessionEnv
from results.dev_aux.task2529.training_audit import terminal
D=Path('results/dev_aux/task2529');T=Path('results/dev_aux/task2527')
def digest(r):return hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def run():
 began=time.perf_counter();p=json.loads(Path('results/dev_aux/task2528/registration.json').read_text());tr=json.loads((T/'result.json').read_text());names={a['generator_seed']:a['channels']for a in tr['arms']};train=defaultdict(set);training_mass=Counter();prefix_count=Counter()
 for line in(T/'episodes.jsonl').open():
  e=json.loads(line);train[e['generator_seed']].add(digest(e['initial_record']));training_mass[e['generator_seed']]+=1
 rows=[];expected={};initial_inventory=[]
 for gs in p['generator_seeds']:
  if gs not in names:continue
  cc=compile_ruleset(ruleset_from_dict(json.loads((T/f'rules-{gs}.json').read_text())))
  initial_inventory.append(dict(generator_seed=gs,initial_entities=cc.initial_entity_count,initial_board_occupied=sum(pc is not None for pc in cc.initial_position.board),board_cells=json.loads((T/f'rules-{gs}.json').read_text())['board_size']**2))
  for fam in p['families']:
   env=RecordedSessionEnv(GameSession(cc),names[gs]);rng=random.Random(gs*1000000+fam)
   for _ in range(p['prefix_plies']):
    if terminal(env.session)is not None:break
    env.push(rng.choice(sorted(env.actions(),key=repr)))
   record=env.record();h=digest(record);expected[gs,fam]=h;rows.append(dict(generator_seed=gs,family=fam,root_sha=h,already_actual_TRAIN_root=h in train[gs],actual_prefix_plies=len(record['actions']),terminal_at_start=terminal(env.session),training_attempts=training_mass[gs],unique_actual_training_roots=len(train[gs])))
 for task in('task2528','task2531'):
  path=Path('results/dev_aux',task,'games.jsonl')
  if not path.exists():continue
  for line in path.open():
   e=json.loads(line);assert digest(e['initial_record'])==expected[e['generator_seed'],e['family']];prefix_count[task]+=1
 out=dict(status='PASS_ACTUAL_REGISTERED_ROOT_DRAW_BINDING',planned_root_draws=len(p['generator_seeds'])*len(p['families']),root_draws=len(rows),initial_inventory=initial_inventory,unique_full_roots=len(set((r['generator_seed'],r['root_sha'])for r in rows)),overlap_draws=sum(r['already_actual_TRAIN_root']for r in rows),terminal_draws=sum(r['terminal_at_start']is not None for r in rows),games_verified=dict(prefix_count),rows=rows,scope='NEW131001..4PRNGbindingstreams are not automaticallyunseenphysicalstates/fullhistories; actualreuse reported. UniformFULLtypedbindings, completehistory hashes notboardcoalescing; TRAINattemptedmass no survival/outcome filtering. Regeneratedrootchoices only, no evaluationsearch/newfitness/externalrulesengine. Repeatedinitials/roles/checkpoints share16plannedrule-family draws, not512independentstarts.',seconds=time.perf_counter()-began);(D/'root-overlap.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k!='rows'}))
if __name__=='__main__':run()
