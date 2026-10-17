"""Observed depth mismatch must censor BEFORE commit, on either side."""
from pathlib import Path
from dataclasses import replace
import json,hashlib
import pytest
from results.dev_aux.task2479 import pilot
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
@pytest.mark.parametrize('incomplete_call',[0,1])
def test_actual_core_depth_fallback_is_uncommitted_unknown(tmp_path,monkeypatch,incomplete_call):
 folder=tmp_path/'strict';folder.mkdir();base=Path('results/dev_aux/task2479');p=json.loads((base/'plan.json').read_text());roots=json.loads((base/'inputs.json').read_text());ip=folder/'inputs.json';ip.write_text(json.dumps(roots));slot=json.loads((base/'slots.json').read_text())[0];sp=folder/'slots.json';sp.write_text(json.dumps([slot]));p.update(input=str(ip),input_sha=hashlib.sha256(ip.read_bytes()).hexdigest(),slots_sha=hashlib.sha256(sp.read_bytes()).hexdigest(),expected_games=1,pins={},one_cap_seconds=30,scope='Controlled regression only, not sciencegame');(folder/'plan.json').write_text(json.dumps(p));monkeypatch.setattr(pilot,'OUT',folder);original=pilot.PaidGraphPhasePlayer.choose;seen=[]
 def choose(self,s,**kw):
  kw['allow_new_proof']=False;d=original(self,s,**kw);assert d.normal_receipt is not None;index=len(seen);seen.append(index)
  return replace(d,normal_receipt=replace(d.normal_receipt,completed_depth=(3 if index==0 else 2)))if index==incomplete_call else d
 monkeypatch.setattr(pilot.PaidGraphPhasePlayer,'choose',choose);pilot.run();g=json.loads((folder/'games.jsonl').read_text().splitlines()[0]);ds=[json.loads(x)for x in(folder/'decisions.jsonl').read_text().splitlines()];commits=[json.loads(x)for x in(folder/'commits.jsonl').read_text().splitlines()];assert g['outcome']=='U'and g['reward']is None and g['ending']=='INCOMPLETE_ROLE_DEPTH_UNFINISHED';assert len(ds)==incomplete_call+1 and len(commits)==g['plies']==incomplete_call;assert g['actual_status']=='ongoing';r=roots[slot['root']];s=GameSession.replay(compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text())),deserialize_game_record(json.dumps(g['record'])));assert s.result.status.value=='ongoing';assert ds[-1]['root_record']==g['record']and ds[-1]['normal_receipt']['completed_depth']==(3 if incomplete_call==0 else 2);assert not(folder/'failure.json').exists()
