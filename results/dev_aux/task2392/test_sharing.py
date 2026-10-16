from pathlib import Path
from io import FileIO
import pytest
from results.dev_aux.task2392.reader import open_shared,close,read_fresh,SharedDeleteStopReader
from results.dev_aux.task2153.stop_evidence import StopObservationFailure,EvidenceStopReader
from results.dev_aux.task109.adapter import PersistentStop

def test_delete_access_sharing_conflict_is_reproduced_and_cooperated(tmp_path):
 EvidenceStopReader(Path.cwd())();p=tmp_path/'control.json';p.write_bytes(b'{"stopped":false}')
 handle=open_shared(p,access=0x00010000,share=7)
 try:
  with pytest.raises(PermissionError):
   with FileIO(p,'r')as f:f.readall()
  assert read_fresh(p)==b'{"stopped":false}'
 finally:assert close(handle)

def test_exclusive_other_handle_still_denies_no_bypass(tmp_path):
 EvidenceStopReader(Path.cwd())();p=tmp_path/'control.json';p.write_bytes(b'{}');handle=open_shared(p,access=0x80000000,share=0)
 try:
  with pytest.raises(OSError)as err:read_fresh(p)
  assert err.value.winerror==32
 finally:assert close(handle)

def test_production_reader_closes_before_next_atomic_replace(tmp_path):
 p=tmp_path/'control.json';p.write_bytes(b'old');assert read_fresh(p)==b'old';replacement=tmp_path/'new.json';replacement.write_bytes(b'new');replacement.replace(p);assert read_fresh(p)==b'new'


def test_reader_same_size_change_stop_and_invalid_are_immediate(tmp_path):
 EvidenceStopReader(Path.cwd())();r=SharedDeleteStopReader(tmp_path);r.paths=(tmp_path/'one.json',);r.errors_dir=tmp_path/'private-errors';p=r.paths[0];p.write_bytes(b'{"stopped":false}');r();p.write_bytes(b'{"stopped":true }')
 with pytest.raises(PersistentStop):r()
 p.write_bytes(b'')
 with pytest.raises(StopObservationFailure):r()
 assert next(r.errors_dir.glob('*.raw')).read_bytes()==b''
