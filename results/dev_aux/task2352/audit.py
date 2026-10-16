"""Independent replay of interrupted TRAIN prefix; never resumes its producer."""
from pathlib import Path
import json,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.generic_session_win_proof import SessionChoice,execute
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2352')
def run():
 stop=EvidenceStopReader(Path.cwd());stop();p=Path('results/dev_aux/task2340');read=lambda n:json.loads((p/n).read_text());diagnosis=json.loads(Path('results/dev_aux/task2352/result.json').read_text());partial=json.loads(Path('results/dev_aux/task2352/partial-record.json').read_text());done=read('completion.json');slots=read('slots.json');plan=read('plan.json');roots={r['index']:r for r in json.loads(Path(plan['input']).read_text())};games=[json.loads(x)for x in(p/'games.jsonl').read_text().splitlines()];ds=[json.loads(x)for x in(p/'decisions.jsonl').read_text().splitlines()]
 for name,digest in diagnosis['raw_stream_sha'].items():assert hashlib.sha256((p/name).read_bytes()).hexdigest()==digest
 assert len(games)==49 and done['missing']==47 and partial['slot']==slots[49]and partial['outcome']=='U'and partial['reward']is None
 r=roots[slots[49]['root']];s=GameSession.replay(compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text())),deserialize_game_record(json.dumps(r['record'])));orphan=[d for d in ds if d['slot']==49]
 for i,d in enumerate(orphan):
  stop();assert d['ply']==i and d['root_record']==json.loads(serialize_game_record(s.to_record()))and d['root_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()
  if i+1<len(orphan):
   a=deserialize_game_record(json.dumps(orphan[i+1]['root_record'])).actions[-1];assert d['choice']==choice_value(SessionChoice('ACTION',action=a));execute(s,SessionChoice('ACTION',action=a))
 assert len(orphan)==51 and partial['record']==json.loads(serialize_game_record(s.to_record()))and s.result.status.value=='ongoing'
 result=dict(status='PASS_INTERRUPTED_PREFIX_ORIGINAL_STREAMS_UNCHANGED',closed_games=49,verified_prefix_moves=50,interrupted_UNKNOWN=1,unstarted=46,scope='Last logged decision commit unknown. Frozen selector never_executed47 means no closed outcome47, corrected to one interrupted and46unstarted here. No price selection, cap reset, original stream edit or UNKNOWN-to-DRAW.')
 with(OUT/'audit.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':run()
