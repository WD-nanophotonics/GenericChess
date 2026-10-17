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
OUT=Path('results/dev_aux/task2450')
def run():
 stop=SharedDeleteStopReader(Path.cwd());t=time.perf_counter();panels=[]
 roots=json.loads(Path('results/dev_aux/task2439/inputs.json').read_text());assert len(roots)==12;seen=set()
 for root in roots:
  stop();rs=deserialize_ruleset(Path(root['rules']).read_text());c=compile_ruleset_for_execution(rs);s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));assert not root['record']['actions']and len([p for p in s.state.position.board if p is not None])==6 and not any(h.counts for h in s.state.position.hands);assert s.result.status is SessionStatus.ONGOING;assert hashlib.sha256(repr(s.state).encode()).hexdigest()==root['state_sha'];legal=s.legal_actions();assert [action_to_dict(a)for a in legal]==root['all_legal_actions'];caps={k:[]for k in('R','N')}
  for a in legal:
   if not hasattr(a,'from_square'):continue
   pc=s.state.position.board[a.to_square.rank*4+a.to_square.file]
   if pc is not None and pc.owner==1 and pc.current_type_id==pc.base_type_id and pc.current_type_id in caps:caps[pc.current_type_id].append(a)
  assert all(caps.values())and any(a.from_square==b.from_square for a in caps['R']for b in caps['N']);assert repr(s.state.position.board)not in seen;seen.add(repr(s.state.position.board))
 for family in range(4):
  folder=Path(f'results/dev_aux/task2440/family-{family}');assert json.loads((folder/'root.json').read_text())['record']==roots[family]['record'];source=Path('results/dev_aux/task2432/consume.py').read_text().replace("folder=Path('results/dev_aux/task2430')",'folder=Path('+repr(folder.as_posix())+')');ns={'__name__':'independent_closed_consumer'};exec(compile(source,'closed_consumer','exec'),ns);ns['OUT']=OUT/('family-'+str(family));ns['OUT'].mkdir();ns['SharedDeleteStopReader']=lambda ignored:stop;ns['run']()
 panels.append(dict(corpus=2439,design_roots=4,reserve_roots=8,reserve_fitness_queries=0,complete_tree_nodes=2686))
 result=dict(status='PASS_DUAL_CAPTURE_STRUCTURAL_ROOTS_AND_COMPLETE_DESIGN_TREES',panels=panels,seconds=time.perf_counter()-t,scope='ALL12initialhistories replayed,4DESIGNfiniteCoretrees independently checked. ReserveONLYsemanticinputvalidation/no search/pricefitness; thisisnotunseenrule/Coreholdout. Exactgenerationattempt/rejection/sourcecounts retained; no newgenerator/fitnessquery. SamepublicCore/verifier, notexternalimplementation.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print('SUMMARY='+json.dumps(result))
if __name__=='__main__':run()
