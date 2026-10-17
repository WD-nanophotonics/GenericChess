"""Replay every new committed snapshot, closure and source-matrix mapping."""
from pathlib import Path
import json,hashlib,time
from collections import defaultdict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.generic_session_win_proof import SessionChoice,execute
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2392.reader import SharedDeleteStopReader as EvidenceStopReader
OUT=Path('results/dev_aux/task2464')
def run(task=2461):
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());f=Path(f'results/dev_aux/task{task}');read=lambda p:json.loads(Path(p).read_text());p=read(f/'plan.json');roots={r['index']:r for r in read(p['input'])};slots=read(f/'slots.json');commits=[json.loads(x)for x in(f/'commits.jsonl').read_text().splitlines()];games=[json.loads(x)for x in(f/'games.jsonl').read_text().splitlines()];decisions=[json.loads(x)for x in(f/'decisions.jsonl').read_text().splitlines()];by=defaultdict(list);db=defaultdict(list)
 for row in commits:by[row['slot']['slot']].append(row)
 for row in decisions:db[row['slot']].append(row)
 for slotid,rows in by.items():
  r=roots[slots[slotid]['root']];s=GameSession.replay(compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text())),deserialize_game_record(json.dumps(r['record'])))
  for i,row in enumerate(rows):
   stop();assert row['slot']==slots[slotid]and row['plies']==i+1;record=deserialize_game_record(json.dumps(row['record']));assert record.actions[:-1]==s.to_record().actions;a=record.actions[-1];d=db[slotid][i];assert d['ply']==i and d['root_record']==json.loads(serialize_game_record(s.to_record()))and d['choice']==choice_value(SessionChoice('ACTION',action=a));execute(s,SessionChoice('ACTION',action=a));assert row['state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()and row['actual_status']==s.result.status.value and row['winner']==s.result.winner
  g=next((g for g in games if g['slot']==slotid),None)
  if g is not None:assert len(rows)==g['plies']and rows[-1]['record']==g['record']
 failure=read(f/'failure.json')if(f/'failure.json').exists()else None
 if failure is not None and failure['partial']is not None:
  partial=failure['partial'];assert partial['plies']==0 or partial==by[partial['slot']['slot']][-1];assert failure['partial_reward']is None
 result=dict(status='PASS_ALL_NEW_COMMITTED_RECORDS_AND_PROVENANCE',new_games=len(games),new_committed_moves=len(commits),reuse=0,failure=None if failure is None else failure['error_type'],seconds=time.perf_counter()-t,scope='Eachjournaltransition executed withpublicCore andmatchedactualdecision/root/record/state/terminal. Committedsnapshotsnotassumedfromsearchreceipt. ALLnewreservedgames, no extra games/capreset. Faulttests separatefromscientificoutcomes.')
 with(OUT/f'task{task}-result.json').open('x')as fp:json.dump(result,fp,indent=2)
 print(json.dumps(result))
if __name__=='__main__':
 import sys
 run(int(sys.argv[1])if len(sys.argv)>1 else 2461)
