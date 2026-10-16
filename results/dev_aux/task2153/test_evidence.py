from pathlib import Path
import json,hashlib
import pytest
from results.dev_aux.task2131.stop_reader import ParsedStopReader
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader,StopObservationFailure
from results.dev_aux.task109.adapter import PersistentStop
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn

def flags(tmp_path):
 root=tmp_path/'DEV_AUX';other=tmp_path/'GenericChess 2'
 for owner in(root,other):
  d=owner/'.local_agent';d.mkdir(parents=True)
  for name in('rollout.json','advisor.json','slack.json'):(d/name).write_text('{"stopped":false}',encoding='utf-8')
 return root,other

def fixture_session():
 return GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2139/rules-25.json').read_text(encoding='utf-8'))))

def test_real_empty_flag_window_was_hidden_as_unsupported_and_new_reader_exposes_it(tmp_path):
 root,other=flags(tmp_path);old=ParsedStopReader(root);new=EvidenceStopReader(root);old();new();s=fixture_session();before=s.to_record();flag=other/'.local_agent/rollout.json'
 # An actual in-place writer has opened/truncated its OWN fixture file.
 # This is not an actual primary write or a monkeypatched read.
 with flag.open('wb')as writer:
  r=prove_session_win_batch_pn(s,target=1,max_nodes=1024,seconds=1.,max_depth=96,cancel=old)
  assert r.status=='UNKNOWN'and r.reason=='unsupported_or_unreplayable_session'
  with pytest.raises(StopObservationFailure):prove_session_win_batch_pn(s,target=1,max_nodes=1024,seconds=1.,max_depth=96,cancel=new)
  raw=list(new.errors_dir.glob('*.raw'));meta=list(new.errors_dir.glob('*.json'))
  assert len(raw)==len(meta)==1 and raw[0].read_bytes()==b''
  m=json.loads(meta[0].read_text(encoding='utf-8'));assert m['owner']=='PRIMARY_READ_ONLY'and m['error_type']=='JSONDecodeError'and m['raw_sha256']==hashlib.sha256(b'').hexdigest()
  writer.write(b'{"stopped":false}');writer.flush()
 assert s.to_record()==before
 # Explicit next call after an actual new valid observation succeeds; no auto retry.
 new()

@pytest.mark.parametrize('bad',[b'{',b'[]',b'{"stopped":'])
def test_invalid_bytes_saved_exact_before_failure_not_retried(tmp_path,bad):
 root,other=flags(tmp_path);reader=EvidenceStopReader(root);reader();path=root/'.local_agent/slack.json';path.write_bytes(bad)
 with pytest.raises(StopObservationFailure):reader()
 assert next(reader.errors_dir.glob('*.raw')).read_bytes()==bad
 assert path.read_bytes()==bad

def test_actual_stop_truthiness_still_raises_original_persistent_stop(tmp_path):
 root,other=flags(tmp_path);reader=EvidenceStopReader(root);reader();path=other/'.local_agent/advisor.json';path.write_text('{"user_paused":true}',encoding='utf-8')
 with pytest.raises(PersistentStop):reader()
 assert not reader.errors_dir.exists()

def test_same_bytes_every_poll_still_read_and_decode_only_once(tmp_path):
 root,other=flags(tmp_path);reader=EvidenceStopReader(root)
 for _ in range(10):reader()
 assert reader.reads==60 and reader.parses==6 and not reader.errors_dir.exists()
