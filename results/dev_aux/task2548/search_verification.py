"""Unpruned D2 audit of root/action/PV AND every recorded interior bound."""
from pathlib import Path
import json,time,hashlib,random
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2525.run import RecordedSessionEnv
from results.dev_aux.task2529.training_audit import terminal,feat
from results.dev_aux.task2392.reader import SharedDeleteStopReader
D=Path('results/dev_aux/task2548');T=Path('results/dev_aux/task2546');CHANNELS=(('board','P'),('board','A'),('board','X'),('hand','A'),('hand','P'),('hand','X'))
class Limit(Exception):pass

def run(stop_root=None,prefix_rule=None):
 began=time.perf_counter();plan=json.loads((D/'search-plan.json').read_text());assert (T/'result.json').exists()if prefix_rule is None else(D/'training-audit-first-rule.json').exists();p=json.loads((T/'plan.json').read_text());stop=SharedDeleteStopReader(Path.cwd()if stop_root is None else Path(stop_root));stop();selected={}
 for line in(T/'queries.jsonl').open():
  q=json.loads(line)
  if q['complete']and q['actor']==q['color']and(prefix_rule is None or q['generator_seed']==prefix_rule):
   for threshold in plan['thresholds']:
    key=q['generator_seed'],q['method'],q['seed'],threshold
    if key not in selected and q['total_nodes']-q['nodes']>=threshold:selected[key]=q
 cc={gs:compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{gs}.json').read_text())))for gs in p['generator_seeds']};nodes=0;results=[];bounds=0;nonexact=0;status='COMPLETE'
 def poll():
  nonlocal nodes
  if nodes>=plan['node_ceiling']or time.perf_counter()-began>=plan['cap_seconds']:raise Limit()
  if nodes%128==0:stop()
  nodes+=1
 for key,q in sorted(selected.items()):
  env=RecordedSessionEnv(GameSession.replay(cc[key[0]],deserialize_game_record(json.dumps(q['record_before']))),CHANNELS);before=env.record();w=q['weights'];n0=nodes;samples=q['samples'];si=0;local=[]
  def solve(depth):
   poll();z=terminal(env.session)
   if z is not None:return 1000000.*z,[(None,True)]
   if depth==0:
    phi=feat(env.session,CHANNELS);return sum(a*b for a,b in zip(phi,w)),[(list(phi),False)]
   values=[];pv=[];own=env.player()==0
   for action in env.actions():
    env.push(action)
    try:v,leaves=solve(depth-1)
    finally:env.pop()
    if not values or(v>(max(values))if own else v<min(values)):pv=leaves
    elif v==(max(values)if own else min(values)):pv+=leaves
    values.append(v)
   return(max if own else min)(values),pv
  try:
   poll();own=env.player()==0;actions=list(env.actions());rng=random.Random(int.from_bytes(hashlib.sha256((str(q['ordering_seed'])+'|').encode()).digest()[:8],'big'));rng.shuffle(actions);vals=[];chosen=[]
   for action in actions:
    env.push(action)
    try:
     z=terminal(env.session);childphi=list(feat(env.session,CHANNELS))if z is None else None;ischosen=env.record()==q['record_after'];v,witness=solve(1)
     if ischosen:chosen.append((v,witness))
     if z is None:
      sample=samples[si];si+=1;assert sample['depth']==1 and sample['phi']==childphi;lo=float(sample['lower']);hi=float(sample['upper']);assert lo-1e-10<=v<=hi+1e-10,(key,lo,v,hi);bounds+=1;nonexact+=lo!=hi;local.append(dict(depth=1,lower=sample['lower'],upper=sample['upper'],exact_value=v,child_record_sha=hashlib.sha256(json.dumps(env.record(),sort_keys=True).encode()).hexdigest()))
    finally:env.pop()
    vals.append(v)
   exact=(max if own else min)(vals);root=samples[si];si+=1;assert si==len(samples)and root['depth']==2 and root['phi']==list(feat(env.session,CHANNELS));assert float(root['lower'])==float(root['upper'])==exact==q['value'];assert len(chosen)==1 and chosen[0][0]==exact and(q['pv_phi'],q['pv_terminal'])in chosen[0][1];assert env.record()==before;bounds+=1
   results.append(dict(key=key,gameid=q['gameid'],ply=q['ply'],nodes=nodes-n0,value=exact,interior_bounds=local,root_exact=True,committed_action_PV_witness=True,source_query_sha=hashlib.sha256(json.dumps(q,sort_keys=True).encode()).hexdigest()))
  except Limit:status='PARTIAL_ORIGINAL_CAP';assert env.record()==before;break
 expected=plan['expected']if prefix_rule is None else plan['expected']//len(p['generator_seeds'])
 out=dict(status=status,expected=expected,available=len(selected),verified=len(results),unverified=expected-len(results),nodes=nodes,verified_bounds=bounds,nonexact_bounds=nonexact,rows=results,seconds=time.perf_counter()-began,scope=plan['scope']+' Same actual Session authority; unpruned minimax independent of TrainingSearch/TreeStrap. Every nonterminal root child path bound checked, including bound inequalities. Not every TRAIN query rerun/all generated rules proved.')
 (D/('search-verification.json'if prefix_rule is None else'search-verification-first-rule.json')).write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k!='rows'}))
if __name__=='__main__':run()
