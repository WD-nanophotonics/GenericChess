"""Independent full-history evaluator-control replay and paid-phase attribution."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_win_proof import _same_state
ROOT=Path('results/dev_aux/task2063');OUT=Path('results/dev_aux/task2079')
def sha(s):return hashlib.sha256(repr(s).encode()).hexdigest()
def run():
 t=time.perf_counter();p=json.loads((ROOT/'run-plan.json').read_text());done=json.loads((ROOT/'completion.json').read_text());assert done['status']in('COMPLETE','GLOBAL_CAP','INCOMPLETE_OUTCOME');assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['source_sha'].items())
 games=[json.loads(x)for x in(ROOT/'games.jsonl').read_text().splitlines()];moves=[json.loads(x)for x in(ROOT/'moves.jsonl').read_text().splitlines()];assert len(games)==done['completed']and len(moves)==done['moves'];by=defaultdict(list)
 for step in moves:by[step['slot']].append(step)
 assert set(by)<=set(g['slot']for g in games)
 teacher={''.join(l['board'][:-1])+str(l['board'][-1]):l for l in(json.loads(x)for x in Path('results/dev_aux/task2058/labels.jsonl').read_text().splitlines())};actor=RoyalActor(4);phase=Counter();no_win=Counter();sources=Counter();actual=Counter();proof_games=0;pending=[];outerlate=0
 for expected,g in zip(p['slots'],games):
  assert all(g[k]==v for k,v in expected.items());c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['roots'][g['family']]['rules']).read_text()));s=GameSession(c);rows=by[g['slot']];assert len(rows)==g['moves'];owners=set()
  for ply,step in enumerate(rows):
   assert ply==step['ply']and s.result.status is SessionStatus.ONGOING and sha(s.state)==step['before_state_sha'];assert s.state.position.side_to_move==step['side'];assert step['proof_nodes']<=p['proof_nodes']and step['search_nodes']<=p['normal_nodes']and step['verification_nodes']<=p['verification_nodes']
   before=actor_state(s.state);l=teacher[''.join(before[:-1])+str(before[-1])];sources[step['source']]+=1
   for key in('proof_seconds','normal_seconds','seconds'):phase[key]+=step[key]
   if l['label']in('DRAW','LOSS'):
    no_win['decisions']+=1;no_win['PN_nodes']+=step['proof_nodes'];no_win['PN_seconds']+=step['proof_seconds']
   limits=step['phase_limits'];assert limits['normal_nodes']==p['normal_nodes']and limits['proof_nodes']==p['proof_nodes']and limits['normal_seconds']==p['normal_seconds']
   literal=dict(actor.moves(before));public={uci(a):a for a in s.legal_actions()};assert set(literal)==set(public)
   encoded={**g['record'],'actions':[step['choice']]};action=deserialize_game_record(json.dumps(encoded)).actions[0];name=uci(action);assert name in public;s.submit(public[name]);assert actor_state(s.state)==literal[name]and sha(s.state)==step['after_state_sha']
   assert dict(status=s.result.status.value,winner=s.result.winner)==step['result']
   for a,b in zip(step['before_ranks'],step['after_ranks']):
    if a is not None and a>0:assert b is not None and b<a
   if step['source']=='PROOF':owners.add(step['side'])
   outerlate+=step['seconds']>p['step_seconds']
  replay=GameSession.replay(c,deserialize_game_record(json.dumps(g['record'])));assert _same_state(replay.state,s.state)and _same_state(replay.result,s.result)and sha(s.state)==g['final_state_sha']
  outcome='UNKNOWN'if s.result.status is SessionStatus.ONGOING else'DRAW'if s.result.winner is None else'WIN'if s.result.winner==g['candidate_side']else'LOSS';assert outcome==g['outcome']and g['score']==(1 if outcome=='WIN'else-1 if outcome=='LOSS'else 0 if outcome=='DRAW'else None);actual[outcome]+=1
  if owners:
   assert len(owners)==1
   if outcome=='UNKNOWN':pending.append(g['slot'])
   else:assert s.result.winner==next(iter(owners));proof_games+=1
 models={name:dict(Counter(g['outcome']for g in games if g['model']==name))for name in('material','kingking','kingpiece')};full=[]
 for f in range(16):
  batch=[g for g in games if g['family']==f]
  if len(batch)==6 and all(g['score']is not None for g in batch):full.append(f)
 paired={}
 for name in('kingking','kingpiece'):
  ds=[sum(g['score']for g in games if g['family']==f and g['model']==name)/2-sum(g['score']for g in games if g['family']==f and g['model']=='material')/2 for f in full];paired[name]=dict(complete_family_deltas=ds,mean=None if not ds else sum(ds)/len(ds))
 result=dict(status='PASS_COMPLETE_ACTUAL_CONTROL'if done['status']=='COMPLETE'else'PASS_PARTIAL_CONTROL_PRESERVED',campaign_status=done['status'],physical_games=len(games),physical_moves=len(moves),planned_games=96,unrun_slots=[s['slot']for s in p['slots'][len(games):]],unfinished_actual_slots=[g['slot']for g in games if g['outcome']=='UNKNOWN'],actual_outcomes=dict(actual),model_outcomes=models,fully_completed_families=full,paired_complete_family_gains=paired,source_counts=dict(sources),paid_phase_seconds=dict(phase),positional_no_win_paid_PN=dict(no_win),all_finished_adopted_proof_games_won=not pending,finished_proof_games=proof_games,pending_proof_slots=pending,outer_late_steps=outerlate,recorded_seconds=sum(g['seconds']for g in games),seconds=time.perf_counter()-t,scope='Originalone1800cap/notextended; allmissing/UNKNOWNretained. Partialcompletedfamiliesdescriptiveonly: duration-dependentcensoring, fixedorder andfewfamiliespreclude full96gamequalityclaim. SamecommonfeaturebuilderforALLmodels; notcost-optimizedmaterialbaseline. GenericCoreAB vsNative2055notalignedperformancecontrol. No additionalgames/PN/search duringaudit.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
