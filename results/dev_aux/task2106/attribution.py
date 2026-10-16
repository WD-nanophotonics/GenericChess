from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2100.campaign import evaluate
from results.dev_aux.task2105.provider import TriggerProvider
OUT=Path('results/dev_aux/task2106')
def run():
 start=time.perf_counter();deadline=start+120;root=Path('results/dev_aux/task2105');games=[json.loads(x)for x in(root/'games.jsonl').read_text(encoding='utf-8').splitlines()];physical=[g for g in games if g['reused_from']is None];moves=defaultdict(list)
 for line in(root/'moves.jsonl').read_text(encoding='utf-8').splitlines():
  r=json.loads(line);moves[r['physical_id']].append(r)
 inputs=json.loads((root/'inputs.json').read_text(encoding='utf-8'))['roots'];compiled={};entries=[];metrics=Counter();cases=[];seen=set()
 for g in physical:
  if g['family']not in compiled:compiled[g['family']]=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[g['family']]['rules']).read_text(encoding='utf-8')))
  c=compiled[g['family']];s=GameSession(c);record=deserialize_game_record(json.dumps(g['record']));steps=moves[g['physical_id']];entry=None
  for ply,(step,a)in enumerate(zip(steps,record.actions)):
   n=sum(p is not None for p in s.state.position.board)
   if step['source']=='PROOF':metrics['proof_adoptions_above4'if n>4 else'proof_adoptions_at_most4']+=1
   if n<=4 and step['source']in('MATERIAL_SEARCH','LEGAL_FALLBACK'):metrics['postentry_normal_or_legal_fallback']+=1
   if g['phase']=='TRAIN'and n<=4 and step['source']=='MATERIAL_SEARCH'and step['proof_reason']=='certified_complete_graph_no_win'and step['side']==g['candidate_side']and len(cases)<12:
    rr=serialize_game_record(s.to_record());h=hashlib.sha256(rr.encode()).hexdigest()
    if h not in seen:seen.add(h);cases.append((g['family'],c,s.to_record(),g['physical_id'],ply))
   s.submit(a)
   if entry is None and sum(p is not None for p in s.state.position.board)<=4:
    next_step=steps[ply+1]if ply+1<len(steps)else None;entry=dict(entered=True,entry_ply=ply+1,remaining_rule_plies=96-s.state.ply_count,side=s.state.position.side_to_move,max_prior_count=max(n for _,n in s.state.repetition_counts),full_record=json.loads(serialize_game_record(s.to_record())),actual_entry_result=dict(status=s.result.status.value,winner=s.result.winner),first_decision=None if next_step is None else dict(source=next_step['source'],reason=next_step['proof_reason']))
  entries.append(dict(physical_id=g['physical_id'],phase=g['phase'],family=g['family'],ratio=g['ratio'],candidate_side=g['candidate_side'],actual_outcome=g['outcome'],entry=entry if entry is not None else dict(entered=False,terminal_or_incomplete=dict(status=s.result.status.value,winner=s.result.winner))))
 metrics['physical_denominator']=len(physical);metrics['entered']=sum(e['entry']['entered']for e in entries);metrics['never_entered']=len(physical)-metrics['entered'];(OUT/'first-entries.json').write_text(json.dumps(entries,separators=(',',':')),encoding='utf-8')
 load=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2097','results/dev_aux/task2098','results/dev_aux/task2099');loadtime=time.perf_counter()-load;receipts=[];witness=None;limits=PhaseLimits(proof_nodes=1024,verification_nodes=16384,proof_seconds=.2,verification_seconds=.2,normal_seconds=.25)
 for family,c,record,pid,ply in cases:
  if time.perf_counter()>=deadline:break
  s=GameSession.replay(c,record);rows=[]
  for ratio in(1.,.25,2.,2.,.25,1.):
   if time.perf_counter()>=deadline:break
   player=SessionCachedPhasePlayer(c,evaluate(ratio),bank=SessionLogicalProofBank(TriggerProvider(teacher),capacity=256),limits=limits,proof_enabled=True,max_depth=2,proof_depth=64);d=player.choose(s,max_nodes=512,seconds=.75,cancel=lambda:time.perf_counter()>=deadline);rows.append(dict(ratio=ratio,choice=None if d.choice is None else action_to_dict(d.choice.action),source=d.source,proof_reason=d.proof_reason,completed_depth=None if d.normal_receipt is None else d.normal_receipt.completed_depth,search_nodes=d.search_nodes,seconds=d.seconds))
  stable=len(rows)==6 and all(rows[j]['choice']==rows[5-j]['choice']and rows[j]['completed_depth']==rows[5-j]['completed_depth']==2 and rows[j]['source']==rows[5-j]['source']=='MATERIAL_SEARCH'for j in range(3));different=len({json.dumps(r['choice'],sort_keys=True)for r in rows[:3]})>1;case=dict(family=family,physical_id=pid,ply=ply,rows=rows,stable_depth2=stable,different_price_actions=different);receipts.append(case)
  if stable and different:witness=dict(**case,full_record=json.loads(serialize_game_record(record)));break
 result=dict(status='FOUND_POSTTRIGGER_PRICE_ACTION_COUNTEREXAMPLE'if witness else'NO_STABLE_WITNESS_WITHIN_DECLARED_CASES',first_entry_metrics=dict(metrics),eligible_TRAIN_counterexample_cases=len(cases),queried_cases=len(receipts),teacher_load_seconds=loadtime,seconds=time.perf_counter()-start,witness=witness,scope='TriggerdoesNOTisolatepretriggerformation: normalstillusescandidateprice andsmallPNcanconvertbeforeentry. OnlywholepolicyW-Lattributed. Fullrecord/target/depth/node/coldstart held; diagnosticnormal.25wallcap differsfromstudy.02, nocurrentWDLclaimornewgame. Nonentrydenominatorretained.')
 (OUT/'counterfactual-queries.json').write_text(json.dumps(receipts,indent=2),encoding='utf-8');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k!='witness'}))
if __name__=='__main__':run()
