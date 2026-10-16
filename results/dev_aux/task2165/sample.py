from pathlib import Path
from fractions import Fraction
from dataclasses import replace
from collections import Counter
import json,time,random,hashlib
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state,orbit
from scripts.generic_royal_actor import RoyalActor
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2165')
def literal_tree(actor,raw,depth,target=0):
 moves=actor.moves(raw)
 if not moves:
  check=actor.attacked(raw,actor.king(raw,raw[-1]),1-raw[-1])
  return dict(terminal='LOSS'if check and raw[-1]==target else'WIN'if check else'DRAW'),1
 if depth==0:
  coeff=[0,0]
  for ch in raw[:-1]:
   if ch not in('.','K','k'):coeff[ch.upper()=='N']+=1 if int(ch.islower())==target else-1
  return dict(coeff=coeff),1
 edges=[];nodes=1
 for name,child in moves:
  t,n=literal_tree(actor,child,depth-1,target);edges.append((name,t));nodes+=n
 return dict(own=raw[-1]==target,edges=edges),nodes

def val(tree,r):
 if'terminal'in tree:return float('inf')if tree['terminal']=='WIN'else-float('inf')if tree['terminal']=='LOSS'else Fraction(0)
 if'coeff'in tree:return tree['coeff'][0]+r*tree['coeff'][1]
 values=[val(t,r)for a,t in tree['edges']]
 return max(values)if tree['own']else min(values)

def profile(tree,ratios):
 out=[]
 for r in ratios:
  values=[val(t,r)for a,t in tree['edges']];best=max(values);top=[a for(a,t),v in zip(tree['edges'],values)if v==best]
  out.append(dict(ratio=str(r),top_actions=top,first_action=top[0]))
 return out

def run():
 if(OUT/'started.json').exists():raise RuntimeError('single180cap inputdraw neverrestart')
 start=time.perf_counter();p=json.loads((OUT/'plan.json').read_text(encoding='utf-8'));deadline=start+180;stop=EvidenceStopReader(Path.cwd());rng=random.Random(p['seed']);actor=RoyalActor(3);seen=set();assessed=[];roots=[];tries=0;excluded=0;ratios=list(map(Fraction,p['ratios']))
 (OUT/'started.json').write_text(json.dumps(dict(started_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap_seconds=180)),encoding='utf-8')
 base=deserialize_ruleset(Path(p['base_rules']).read_text(encoding='utf-8'))
 for task in p['exclusion_tasks']:
  folder=Path(f'results/dev_aux/task{task}');oldinputs=json.loads((folder/'inputs.json').read_text(encoding='utf-8'))['roots'];compiled={}
  for g in map(json.loads,(folder/'games.jsonl').read_text(encoding='utf-8').splitlines()):
   if g['reused_from']is not None:continue
   stop()
   if g['family']not in compiled:compiled[g['family']]=compile_ruleset_for_execution(deserialize_ruleset(Path(oldinputs[g['family']]['rules']).read_text(encoding='utf-8')))
   s=GameSession(compiled[g['family']]);seen.update(orbit(actor_state(s.state)));excluded+=1
   for action in deserialize_game_record(json.dumps(g['record'])).actions:s.submit(action);seen.update(orbit(actor_state(s.state)));excluded+=1
 while len(roots)<32 and len(assessed)<512 and tries<100000 and time.perf_counter()<deadline:
  stop();tries+=1;raw=['.']*9
  for sq,ch in zip(rng.sample(range(9),6),'KkBNbn'):raw[sq]=ch
  raw=tuple(raw)+(0,)
  if raw in seen or any(actor.attacked(raw,actor.king(raw,s),1-s)or len(actor.moves(raw[:-1]+(s,)))<2 for s in(0,1)):continue
  seen.update(orbit(raw));tree,nodes=literal_tree(actor,raw,2);profiles=profile(tree,ratios);upper=nodes+1+len(tree['edges']);active=len({r['first_action']for r in profiles})>1;accepted=active and upper<=64
  record=dict(candidate=len(assessed),root=list(raw),full_depth2_nodes=nodes,iterative_depth1plus2_node_upper=upper,profiles=profiles,price_active=active,accepted=accepted);assessed.append(record)
  if accepted:
   board=tuple(None if ch=='.'else Piece(int(ch.islower()),ch.upper(),ch.upper())for ch in raw[:-1]);rule=replace(base,initial_position=tuple(tuple(board[y:y+3])for y in range(0,9,3)),initial_setup_options=());c=compile_ruleset_for_execution(rule);assert actor_state(GameSession(c).state)==raw;path=OUT/f'rules-{len(roots)}.json';path.write_text(serialize_ruleset(rule),encoding='utf-8');roots.append(dict(family=len(roots),phase='TRAIN'if len(roots)<32 else'DEV',candidate=record['candidate'],root=list(raw),rules=str(path),fingerprint=c.ruleset_fingerprint))
 out=dict(status='FROZEN32_INPUTS_ONLY_NO_FIT'if len(roots)==32 else'PARTIAL_INPUT_FEASIBILITY',roots=roots,attempts=tries,structural_assessed=len(assessed),price_active=sum(r['price_active']for r in assessed),accepted=len(roots),excluded_prior_actual_positions=excluded,seconds=time.perf_counter()-start,no_WDL_rank_proof_fitness_filter=True,prior_population_labels_exposed=True,new_game_or_fit=0)
 (OUT/'inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8');(OUT/'assessed.json').write_text(json.dumps(assessed,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items()if k!='roots'}),flush=True)
if __name__=='__main__':run()
