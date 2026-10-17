"""Independent semantic corpus and complete finite-tree audit; never regenerate."""
from pathlib import Path
from copy import copy
from collections import Counter
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from generic_chess.core.actions import action_to_dict
from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2432 import consume
OUT=Path('results/dev_aux/task2438')
def run():
 stop=SharedDeleteStopReader(Path.cwd());t=time.perf_counter();panels=[]
 for corpus,tree_task in((2433,2434),(2435,2436)):
  f=Path(f'results/dev_aux/task{corpus}');roots=json.loads((f/'inputs.json').read_text());attempts=json.loads((f/'generation-attempts.json').read_text());done=json.loads((f/'completion.json').read_text());assert len(roots)==16 and[ r['partition']for r in roots]==['TRAIN']*8+['RESERVE']*8;assert[ r['attempt']for r in roots]==[r['attempt']for r in attempts if'admitted_index'in r];seen=set();captures=0;boardRs=[]
  for root in roots:
   stop();rs=deserialize_ruleset(Path(root['rules']).read_text());c=compile_ruleset_for_execution(rs);record=deserialize_game_record(json.dumps(root['record']));s=GameSession(c);assert all(not x for masks in rs.drop_allowed.values()for mask in masks for x in mask);expected_actors=5 if corpus==2433 else 6;assert sum(x is not None for row in rs.initial_position for x in row)==expected_actors;assert all(pc.base_type_id==pc.current_type_id for row in rs.initial_position for pc in row if pc is not None)
   # Reconstruct actual stock from legal action transitions, never injecting hands.
   attempt=next(a for a in attempts if a['attempt']==root['attempt']);assert attempt['prefix']==[action_to_dict(a)for a in record.actions]
   for a in record.actions:
    stop();assert a in s.legal_actions();before=sum(h.total()for h in s.state.position.hands);s.submit(a);after=sum(h.total()for h in s.state.position.hands);captures+=max(0,after-before)
   assert s.result.status is SessionStatus.ONGOING and len(s.legal_actions())>=2 and any(dict(h.counts).get('R',0)for h in s.state.position.hands);assert hashlib.sha256(repr(s.state).encode()).hexdigest()==root['state_sha'];assert json.loads(serialize_game_record(s.to_record()))==root['record'];assert len(record.actions)==(12 if corpus==2433 else 6)
   key=repr((s.state.position.board,s.state.position.hands,s.state.position.side_to_move,s.state.position.aux_state));assert key==root['structural_key']and key not in seen;seen.add(key);n=sum(pc is not None and pc.current_type_id=='R'for pc in s.state.position.board);boardRs.append(n)
   if corpus==2435:assert n>=1
  for family in range(8):
   folder=Path(f'results/dev_aux/task{tree_task}/family-{family}');assert json.loads((folder/'root.json').read_text())['record']==roots[family]['record'];consume.OUT=OUT/f'{tree_task}-{family}';consume.OUT.mkdir();
   # Consumer's source folder is fixed; load an isolated source with ONLY folder binding changed.
   source=Path('results/dev_aux/task2432/consume.py').read_text().replace("folder=Path('results/dev_aux/task2430')",'folder=Path('+repr(folder.as_posix())+')');ns={'__name__':'independent_closed_consumer'};exec(compile(source,'closed_consumer','exec'),ns);ns['OUT']=consume.OUT;ns['SharedDeleteStopReader']=lambda ignored:stop;ns['run']()
  panels.append(dict(corpus=corpus,trees=tree_task,roots=len(roots),reserve8_fitness_queries=0,actual_capture_increments=captures,boardR_counts=boardRs,tree_nodes=json.loads(Path(f'results/dev_aux/task{tree_task}/result.json').read_text())['nodes']))
 result=dict(status='PASS_PREFIT_RULE_ONLY_GENERATION_AND_ALL_TRAIN_CORE_TREES',panels=panels,seconds=time.perf_counter()-t,scope='ALL32initialhistories replayed,16TRAINfiniteCoretrees independently checked. ReserveONLYsemanticinputvalidation/no search/pricefitness; thisisnotunseenrule/Coreholdout. Exactgenerationattempt/rejection/sourcecounts retained; no newgenerator/fitnessquery. SamepublicCore/verifier, notexternalimplementation.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print('SUMMARY='+json.dumps(result))
if __name__=='__main__':run()
