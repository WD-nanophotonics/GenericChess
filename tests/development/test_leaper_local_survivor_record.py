"""Regression for the observed GameRecord/JSON boundary; no search or Core query."""
import gzip,json
from pathlib import Path
import pytest
import scripts.leaper_local_survivor_witness as witness
from generic_chess.session.serialization import deserialize_game_record
from scripts.research_record import record_value

@pytest.mark.parametrize('as_record',[False,True])
def test_existing_replay_contract_receives_json_record(monkeypatch,as_record):
 packet=json.loads(gzip.decompress(Path('docs/research/data/leaper_quiet_source_20261028/inputs.json.gz').read_bytes()))
 raw=packet['rows'][0]['record'];value=deserialize_game_record(json.dumps(raw)) if as_record else raw
 def json_boundary(compiled,actual):
  # This is the real failing boundary: JSON must accept the supplied value,
  # then the public record parser must reconstruct the complete history.
  restored=deserialize_game_record(json.dumps(actual))
  assert record_value(restored)==raw
  return 'restored-record'
 monkeypatch.setattr(witness,'replay',json_boundary)
 assert witness.record_session(object(),value)=='restored-record'
