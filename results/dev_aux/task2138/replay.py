"""Offline consumers only: no producers, training, PN or live-account reads."""
from pathlib import Path
from fractions import Fraction
import json,time,math
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_session_win_proof import SessionWinCertificate,SessionStrategyCursor
from generic_chess.session.result import SessionStatus
from results.dev_aux.task2100.campaign import evaluate
from results.dev_aux.task2048.portable_certificate import decode
from results.dev_aux.task2117.capacity import value
OUT=Path('.replay_output72')
def run():
 OUT.mkdir(exist_ok=False);start=time.perf_counter();deadline=start+600;result={}
 from results.dev_aux.task2119 import audit as tree_audit
 tree_audit.OUT=OUT/'legacy-node-check';tree_audit.OUT.mkdir();tree_audit.run();result['all14180_public_nodes']='PASS; legacyregioncompletenessclaimsuperseded'
 from results.dev_aux.task2127 import audit as population_audit
 population_audit.OUT=OUT/'population';population_audit.OUT.mkdir();population_audit.run();result['all9800_corrected_population']='PASS'
 original=[json.loads(x)for x in Path('results/dev_aux/task2117/trees.jsonl').read_text().splitlines()];portable=[json.loads(x)for x in Path('results/dev_aux/task2138/trees-portable.jsonl').read_text().splitlines()];corrected=[json.loads(x)for x in Path('results/dev_aux/task2126/queries-corrected.jsonl').read_text().splitlines()]
 def untag(v):
  if isinstance(v,list):return[untag(x)for x in v]
  if isinstance(v,dict):return{k:({'WIN':math.inf,'LOSS':-math.inf,'DRAW':0}[x]if k=='terminal'else untag(x))for k,x in v.items()}
  return v
 reps=list(map(Fraction,['1/2','1','3/2','2','3']))
 for old,public,row in zip(original,portable,corrected):
  assert untag(public)==old;sets=[];first=[]
  for r in reps:
   scores=[value(t,r)for _,t in old['tree']['edges']];best=max(scores);aa=tuple(a for(a,_),v in zip(old['tree']['edges'],scores)if v==best);sets.append(aa);first.append(aa[0])
  assert len(set(sets))==row['distinct_top_sets']and len(set(first))==row['distinct_first_actions']
 result['168_portable_and_complete_global_regions']='PASS'
 for task in(2120,2128):
  from results.dev_aux.task2129 import audit
  audit.OUT=OUT/('audit'+str(task));audit.OUT.mkdir();audit.audit(task)
 from results.dev_aux.task2135 import audit as learning_audit
 learning_audit.OUT=OUT/'learning';learning_audit.OUT.mkdir();learning_audit.audit(2134);result['actual_game_audits']=[2120,2128,2134]
 # Recordedfixed-nodequalification has clock0 and no changedsearchsemantics.
 roots=json.loads(Path('results/dev_aux/task2100/inputs.json').read_text())['roots'];compiled={};count=0
 for r in json.loads(Path('results/dev_aux/task2122/software-queries.json').read_text()):
  f=r['family']
  if f not in compiled:compiled[f]=compile_ruleset_for_execution(deserialize_ruleset(Path(roots[f]['rules']).read_text(encoding='utf-8')))
  c=compiled[f];s=GameSession(c);d=ProofMaterialPlayer(c,evaluate(r['ratio']),proof_enabled=False,max_depth=3).choose(s.state,max_nodes=r['node_cap'],seconds=1.,cancel=lambda:time.perf_counter()>=deadline,_clock=lambda:0.)
  assert (None if d.action is None else action_to_dict(d.action))==r['choice']and d.completed_depth==r['completed_depth']and d.search_nodes==r['nodes']and d.source==r['source']and d.exit_cause==r['exit_cause'];count+=1
 result['node_only_software_queries']=count
 # Allsavednewprobe certificates and actualpaths, withoutconstructingnewproofs.
 certcount=pathmoves=0
 for task in(2121,2133):
  for r in json.loads(Path(f'results/dev_aux/task{task}/certificates.json').read_text()):
   c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['root_record'])));cert=SessionWinCertificate(c.ruleset_fingerprint,s.to_record(),s.state,r['target'],decode(r['tree'],c.ruleset_fingerprint));cursor=SessionStrategyCursor(s,cert,max_nodes=65536,seconds=2.);certcount+=1
   while s.result.status is SessionStatus.ONGOING:
    choice=cursor.choose(s)if s.state.position.side_to_move==r['target']else max(cursor.node.edges,key=lambda e:e[1].rank)[0];cursor.commit(s,choice);pathmoves+=1
   assert s.result.winner==r['target']
 result['probe_certificates']=certcount;result['probe_actual_cursor_moves']=pathmoves
 # Newdiagnosticcontinuation isnever substitutedintooriginalunknownoutcome.
 g=json.loads(Path('results/dev_aux/task2134/games.jsonl').read_text().splitlines()[-1]);assert g['outcome']=='UNKNOWN'and not Path('results/dev_aux/task2134/selector-lock.json').exists();r=json.loads(Path('results/dev_aux/task2134/inputs.json').read_text())['roots'][g['family']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')));s=GameSession.replay(c,deserialize_game_record(Path('results/dev_aux/task2137/actual-record.json').read_text()));assert s.result.winner==0 and s.result.status is SessionStatus.CHECKMATE;result['separate_diagnostic_mate_original_stays_UNKNOWN']=True
 result.update(status='PASS_OFFLINE_SOURCE_AND_RECORD_CONSUMERS72',seconds=time.perf_counter()-start,new_PN_training_or_study_game_queries=0,scope='Pureclosedrecord/certification/cursor consumers plus576boundednormalalgorithmchecks. SamehostPython/OSnotbundled. GlobalregioncheckincludesactualDRAW0; legacy2119checkusedONLYforallpublicnodeconsistency. No liveflag/accountreads or producer/capreset. Priorbasepublicationprojectionunusedbridge stillNOToriginalbyteidentity andmustnotimport.')
 (OUT/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8');assert 'generic_chess.learning.alphasho_bridge'not in __import__('sys').modules;print(json.dumps(result),flush=True)
if __name__=='__main__':run()
