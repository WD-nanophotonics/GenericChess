
"""Closed execution/source provenance and conservative reserved-board projection exposure."""
from pathlib import Path
from collections import Counter
from copy import copy
import json,hashlib,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.generic_session_win_proof import SessionChoice,execute
from scripts.generic_proof_rnb_bridge import orbit,actor_state
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2491')
def run():
 t=time.perf_counter();stop=SharedDeleteStopReader(Path.cwd());read=lambda p:json.loads(Path(p).read_text());held={}
 for r in read('results/dev_aux/task2460/inputs.json'):
  s=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text())));held[min(map(repr,orbit(actor_state(s.state))))]=r['index']
 counts=Counter();hits=[];initial_hits=[];totalcommits=0;totalcerts=0;partialcommits=0;all_game_ids=set()
 for task in(2474,2479,2481):
  f=Path(f'results/dev_aux/task{task}');p=read(f/'plan.json');done=read(f/'completion.json');roots={r['index']:r for r in read(p['input'])};games=[json.loads(x)for x in(f/'games.jsonl').read_text().splitlines()];certs=[json.loads(x)for x in(f/'certificates.jsonl').read_text().splitlines()];totalcerts+=len(certs)
  assert len(games)==done['games']
  for g in games:
   stop();uid=(task,g['slot']);assert uid not in all_game_ids;all_game_ids.add(uid);counts[g['outcome']]+=1
   root=roots[g['root']];s=GameSession.replay(compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text())),deserialize_game_record(json.dumps(root['record'])));prefix=len(s.to_record().actions);record=deserialize_game_record(json.dumps(g['record']))
   for ply in range(g['plies']+1):
    key=min(map(repr,orbit(actor_state(s.state))))
    if key in held:
     row=dict(task=task,slot=g['slot'],ply=ply,reserve_initial_index=held[key],full_state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest(),board_count=sum(x is not None for x in s.state.position.board),hand_count=sum(n for h in s.state.position.hands for _,n in h.counts),projection_only=True)
     hits.append(row)
     if ply==0:initial_hits.append(row)
    if ply<g['plies']:execute(s,SessionChoice('ACTION',action=record.actions[prefix+ply]));totalcommits+=1
   assert json.loads(serialize_game_record(s.to_record()))==g['record']
  journal=[json.loads(x)for x in(f/'commits.jsonl').read_text().splitlines()]
  # A preserved interrupted producer may have a partial journal not represented in a returned game.
  assert len(journal)>=sum(g['plies']for g in games)
  partialcommits+=len(journal)-sum(g['plies']for g in games)
 assert not initial_hits
 qf=Path('results/dev_aux/task2490');qresult=read(qf/'result.json')if(qf/'result.json').exists()else None;queries=[]if not(qf/'queries.jsonl').exists()else[json.loads(x)for x in(qf/'queries.jsonl').read_text().splitlines()]
 if qresult is not None:
  assert qresult['actual_queries']==len(queries) and qresult['missing']==96-len(queries)
  for row in queries:
   stop();d4=row['D4_saved_receipt'];d5=row['D5_new_receipt'];assert d5['nodes']<=131072 and 0<=d5['completed_depth']<=5
   comparable=d4 is not None and d4['completed_depth']==4 and d5['completed_depth']==5
   assert row['choice_changed_from_actual_D4']==(d4['choice']!=d5['choice']if comparable else None)
  for ctl in qresult['controls']:
   if not ctl['complete_D5']:continue
   rr=read(f"results/dev_aux/task{ctl['task']}/result.json");point=ctl['price']+([ctl['Nhand']]if ctl['task']==2472 else[]);ref=next(x for x in rr['rows']if x['depth']==5 and x['price']==point);assert ctl['actual_receipt']['choice']==ref['choice']and ctl['actual_receipt']['score']==ref['score']
 r=dict(status='PASS_CLOSED_NEW_GAME_IDS_ALL_HISTORY_AND_RESERVED_INITIAL_SEPARATION',new_executed_games=len(all_game_ids),actual_outcomes=dict(counts),returned_game_commits=totalcommits,preserved_unreturned_partial_commits=partialcommits,all_committed_snapshots=totalcommits+partialcommits,saved_game_certificates=totalcerts,reserve_explicit_initial_root_collisions=initial_hits,conservative_reserved_board_projection_occurrences=hits,D5_probe_result=qresult,D5_queries=len(queries),seconds=time.perf_counter()-t,scope='Allnewactualexecutions separatelyidentified, NOTindependenttrajectories/familyreplicates. Allgamehistoriesreconstructed; proofvalidation/cursors separate2483/2476. No fresh2460initialorbit usedasstudyroot. Existingorbith helperincludesBOARDcurrentIDs+side ONLY: sufficientforinitial6actors/zero-hands/base=current/noauxfrozenruletemplate, NOTfullPosition/historyequivalence. Trajectoryprojectionhits explicitlyreported, notautomaticallysameSessionorzeroexposure. No8reservedfitnessquery/fit/humanlabels. NormalD5budget/depthcurve isnotactualW-L/newgenericproof.')
 (OUT/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items()if k not in('D5_probe_result','conservative_reserved_board_projection_occurrences')}))
if __name__=='__main__':run()
