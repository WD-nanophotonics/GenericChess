"""TRAIN-only root-action sensitivity under matched fixed material search."""
from pathlib import Path
from collections import Counter
import json,time,hashlib
from results.dev_aux.task2251.study import GuidedPlayer,Guide
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_session_proof_player import commit_session_decision
OUT=Path('results/dev_aux/task2259')
def key(b):return ''.join(b[:-1])+str(b[-1])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(plan_sha=sha(OUT/'plan.json'))));guide=Guide();labels={}
 for i,line in enumerate(Path('results/dev_aux/task2249/labels.jsonl').open(encoding='utf-8')):
  if i%1024==0:stop()
  r=json.loads(line);labels[key(r['board'])]=r['label']
 roots=[r for r in json.loads(Path('results/dev_aux/task2258/inputs.json').read_text())['roots']if r['split']=='TRAIN'];rows=[];value={'WIN':1,'LOSS':-1,'DRAW':0}
 def cancel():stop();return time.perf_counter()-start>=p['cap_seconds']
 with(OUT/'queries.jsonl').open('x',encoding='utf-8')as f:
  for r in roots:
   c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')))
   for ratio in p['grid']:
    if cancel():raise TimeoutError('original_root_probe_cap')
    s=GameSession.replay(c,deserialize_game_record(json.dumps(r['record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==r['state_sha'];player=GuidedPlayer(c,ratio,guide,p);d=player.choose(s,max_nodes=p['normal_nodes'],seconds=p['step_seconds'],cancel=cancel)
    action=None if d.choice is None else uci(d.choice.action);quality=None
    if d.choice is not None:commit_session_decision(s,d,[player],cancel=cancel);quality=-value[labels[key(actor_state(s.state))]]
    row=dict(family=r['family'],ratio=ratio,source=d.source,action=action,canonical_action_quality=quality,root_label=r['target_label'],normal_depth=None if d.normal_receipt is None else d.normal_receipt.completed_depth,visits=d.search_nodes,seconds=d.seconds,exit_cause=d.exit_cause)
    rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
 result=dict(status='COMPLETE_TRAIN_ONLY_ACTION_SENSITIVITY',queries=len(rows),TRAIN_roots=len(roots),DEV_price_queries=0,seconds=time.perf_counter()-start,by_price={str(x):dict(Counter(str(r['canonical_action_quality'])for r in rows if r['ratio']==x))for x in p['grid']},changed_action_families=sum(len({r['action']for r in rows if r['family']==root['family']})>1 for root in roots),changed_quality_families=sum(len({r['canonical_action_quality']for r in rows if r['family']==root['family']})>1 for root in roots),depths=dict(Counter(str(r['normal_depth'])for r in rows)),scope='Diagnosticcanonicalactionqualitynotactualhistoryreward,nottrainingselection/DEVresult. Completeexposedreference used privately forTRAINdiagnostic; fixed fullGameSessionordinaryD3choices only. All32TR/all5pricesretained; no favorable-rootfilter/defaultchange.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
