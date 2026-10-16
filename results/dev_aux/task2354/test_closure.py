from pathlib import Path
import json,hashlib
import pytest
from results.dev_aux.task2354 import pilot
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader,StopObservationFailure
from results.dev_aux.task109.adapter import PersistentStop
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record

def setup_case(tmp_path,monkeypatch):
 out=tmp_path/'run';out.mkdir();old=Path('results/dev_aux/task2340');p=json.loads((old/'plan.json').read_text());inputs=json.loads((old/'inputs.json').read_text());inp=out/'inputs.json';inp.write_text(json.dumps([inputs[0]]));slot=json.loads((old/'slots.json').read_text())[0];sp=out/'slots.json';sp.write_text(json.dumps([slot]));p.update(input=str(inp),input_sha=hashlib.sha256(inp.read_bytes()).hexdigest(),slots_sha=hashlib.sha256(sp.read_bytes()).hexdigest(),expected_games=1,one_cap_seconds=30,pins={},scope='Regression of actual observed exception closure, not learning evidence');(out/'plan.json').write_text(json.dumps(p));monkeypatch.setattr(pilot,'OUT',out);return out,slot,inputs[0]

def test_actual_game_closes_with_every_commit_replayable(tmp_path,monkeypatch):
 out,slot,root=setup_case(tmp_path,monkeypatch);pilot.run();done=json.loads((out/'completion.json').read_text());games=[json.loads(x)for x in(out/'games.jsonl').read_text().splitlines()];commits=[json.loads(x)for x in(out/'commits.jsonl').read_text().splitlines()];assert done['status']=='COMPLETE'and done['games']==1 and games[0]['outcome']=='L';assert len(commits)==games[0]['plies']==9 and commits[-1]['record']==games[0]['record'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()))
 for row in commits:
  s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));assert row['state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()
 assert not(out/'failure.json').exists()and not list(out.glob('*.tmp'))

@pytest.mark.parametrize('kind',['invalid_observation','user_stop'])
def test_exception_after_real_commit_is_saved_and_propagated(tmp_path,monkeypatch,kind):
 out,slot,root=setup_case(tmp_path,monkeypatch);real=EvidenceStopReader(Path.cwd());raised=[]
 def injected():
  real()
  if(out/'commits.jsonl').exists()and(out/'commits.jsonl').stat().st_size:
   raised.append(True)
   if kind=='user_stop':raise PersistentStop('test controlled stop after real commit')
   raise StopObservationFailure('test controlled invalid observation after real commit')
 monkeypatch.setattr(pilot,'EvidenceStopReader',lambda root:injected)
 expected=PersistentStop if kind=='user_stop'else StopObservationFailure
 with pytest.raises(expected):pilot.run()
 assert len(raised)==1;done=json.loads((out/'completion.json').read_text());failed=json.loads((out/'failure.json').read_text());journal=[json.loads(x)for x in(out/'commits.jsonl').read_text().splitlines()];assert done['games']==0 and done['missing']==1 and done['interrupted_outcome']=='U'and failed['partial_reward']is None;assert failed['partial']==journal[-1]and failed['partial']['plies']==1;assert failed['action']=='FAIL_CLOSED_PROPAGATED_NO_RETRY';assert not list(out.glob('*.tmp'))

def test_invalid_observation_before_any_slot_has_no_invented_partial(tmp_path,monkeypatch):
 out,_,_=setup_case(tmp_path,monkeypatch)
 def injected():raise StopObservationFailure('test controlled invalid observation before slot')
 monkeypatch.setattr(pilot,'EvidenceStopReader',lambda root:injected)
 with pytest.raises(StopObservationFailure):pilot.run()
 assert json.loads((out/'failure.json').read_text())['partial']is None;done=json.loads((out/'completion.json').read_text());assert done['games']==0 and done['interrupted_slot']is None
