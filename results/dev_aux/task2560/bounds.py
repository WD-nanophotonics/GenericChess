"""Independent interior-bound checks at exact histories intercepted in an audit process."""
from pathlib import Path
from collections import Counter
from math import isclose
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2525.run import RecordedSessionEnv
from results.dev_aux.task2529.training_audit import terminal,feat
from results.dev_aux.task2532.free_model import FreeModel
from results.dev_aux.task2392.reader import SharedDeleteStopReader
import results.dev_aux.task2504.search as production_search
D=Path('results/dev_aux/task2558');A=Path('results/dev_aux/task2560');CHANNELS=(('board','P'),('board','A'),('board','X'),('hand','A'),('hand','P'),('hand','X'))
class Limit(Exception):pass

def run(prefix_rule=None,stop_root=None):
 start=time.perf_counter();p=json.loads((D/'plan.json').read_text());ap=json.loads((A/'bounds-plan.json').read_text());stop=SharedDeleteStopReader(Path.cwd()if stop_root is None else Path(stop_root));stop();selected={};counts=Counter();rows=[];status='COMPLETE'
 for line in(D/'queries.jsonl').open():
  q=json.loads(line)
  if prefix_rule is not None and q['generator_seed']>prefix_rule:break
  if prefix_rule is not None and q['generator_seed']!=prefix_rule:continue
  if q['observed']:selected.setdefault((q['generator_seed'],q['method'],q['seed']),q)
 cc={g:compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{g}.json').read_text())))for g in p['generator_seeds']}
 def poll():
  if time.perf_counter()-start>=ap['seconds_cap']or counts['independent_nodes']+counts['rerun_nodes']>=ap['nodes_cap']:raise Limit()
  if counts['independent_nodes']%128==0:stop()
  counts['independent_nodes']+=1
 for key,q in sorted(selected.items()):
  env=RecordedSessionEnv(GameSession.replay(cc[key[0]],deserialize_game_record(json.dumps(q['record_before']))),CHANNELS);original=production_search.Sample;captured=[]
  def intercept(phi,lo,hi,depth):
   sample=original(phi,lo,hi,depth);captured.append((sample,env.record()));return sample
  try:
   production_search.Sample=intercept
   rr=production_search.TrainingSearch(q['effective_depth'],quiet=False).search(env,FreeModel(q['weights']),nodes=q['effective_nodes'],seconds=min(30.,ap['seconds_cap']-(time.perf_counter()-start)),seed=q['ordering_seed'],cancel=stop);counts['rerun_nodes']+=rr.nodes
  finally:production_search.Sample=original
  assert rr.complete and rr.nodes==q['nodes']and rr.value==q['value']and len(rr.samples)==len(q['samples'])
  assert [dict(phi=list(s.phi),lower=str(s.lower),upper=str(s.upper),depth=s.depth)for s in rr.samples]==q['samples'];assert env.record()==q['record_before'];env.push(rr.action);assert env.record()==q['record_after'];env.pop();n0=counts['independent_nodes'];local=Counter();checks=[]
  try:
   for sample,record in captured:
    e=RecordedSessionEnv(GameSession.replay(cc[key[0]],deserialize_game_record(json.dumps(record))),CHANNELS);assert tuple(feat(e.session,CHANNELS))==sample.phi
    def exact(depth):
     poll();z=terminal(e.session)
     if z is not None:return 1e6*z
     if depth==0:return sum(a*b for a,b in zip(feat(e.session,CHANNELS),q['weights']))
     own=e.player()==0;values=[]
     for action in e.actions():
      e.push(action)
      try:values.append(exact(depth-1))
      finally:e.pop()
     assert values;return(max if own else min)(values)
    v=exact(sample.depth);assert sample.lower-1e-9<=v<=sample.upper+1e-9;kind='exact'if sample.lower==sample.upper else'upper'if sample.lower==float('-inf')else'lower';local[kind]+=1;checks.append(dict(depth=sample.depth,lower=str(sample.lower),upper=str(sample.upper),independent_value=v,record_sha=hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()))
    assert e.record()==record
   rows.append(dict(rule=key[0],method=key[1],seed=key[2],source_query_sha=hashlib.sha256(json.dumps(q,sort_keys=True).encode()).hexdigest(),source_game=q['gameid'],source_ply=q['ply'],sample_counts=dict(local),independent_nodes=counts['independent_nodes']-n0,rerun_nodes=rr.nodes,checks=checks));counts.update(local);counts['verified_queries']+=1
  except Limit:status='PARTIAL_ORIGINAL_AUDIT_CAP';break
 out=dict(status=status,prefix_rule=prefix_rule,expected_queries=8 if prefix_rule is not None else 32,available=len(selected),verified=len(rows),counts=dict(counts),rows=rows,seconds=time.perf_counter()-start,scope='Sample factory intercepted only in this separate audit process; actualproduction TrainingSearch rerun matches originalreceipt/nodes/action and every selected interior sample is independently fullwidthminimax-checked on its complete exact Session history. No production edit, training update or new fitness. Same Core, selected32queries not every training tree/allrules/externalengine proof. Separate rerun+unpruned auditwork charged.')
 (A/('bounds.json'if prefix_rule is None else'bounds-first-rule.json')).write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k not in('rows','scope')}))
if __name__=='__main__':run()
