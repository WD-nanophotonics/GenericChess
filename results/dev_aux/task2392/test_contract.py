from pathlib import Path
import json,os,pytest
from results.dev_aux.task2392.reader import SharedDeleteStopReader as FreshFileIOStopReader
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader,StopObservationFailure
from results.dev_aux.task109.adapter import PersistentStop

def fixture_reader(tmp_path,cls):
 # Isolated control files only; every test first observes actual host authority.
 EvidenceStopReader(Path.cwd())();r=cls(tmp_path);r.paths=tuple(tmp_path/f'control{i}.json' for i in range(6));r.errors_dir=tmp_path/'private-errors'
 for p in r.paths:p.write_bytes(b'{"stopped":false}')
 return r

@pytest.mark.parametrize('cls',[FreshFileIOStopReader])
def test_every_call_reads_all_current_bytes_same_size_mtime(tmp_path,cls):
 r=fixture_reader(tmp_path,cls);r();before=r.paths[0].stat();r.paths[0].write_bytes(b'{"stopped":true }');os.utime(r.paths[0],ns=(before.st_atime_ns,before.st_mtime_ns))
 with pytest.raises(PersistentStop):r()
 assert r.reads==7 and r.parses==7

@pytest.mark.parametrize('cls',[FreshFileIOStopReader])
def test_atomic_replacement_not_held_descriptor(tmp_path,cls):
 r=fixture_reader(tmp_path,cls);r();p=r.paths[4];tmp=p.with_suffix('.replacement');tmp.write_bytes(b'{"user_paused":true}');tmp.replace(p)
 with pytest.raises(PersistentStop):r()
 assert r.reads==11

@pytest.mark.parametrize('raw',[b'',b'{bad',b'null',b'[]'])
@pytest.mark.parametrize('cls',[FreshFileIOStopReader])
def test_invalid_exact_original_preserved_and_error_propagates(tmp_path,cls,raw):
 r=fixture_reader(tmp_path,cls);r();r.paths[2].write_bytes(raw)
 with pytest.raises(StopObservationFailure):r()
 copies=list(r.errors_dir.glob('*.raw'));assert len(copies)==1 and copies[0].read_bytes()==raw;assert len(list(r.errors_dir.glob('*.json')))==1

@pytest.mark.parametrize('cls',[FreshFileIOStopReader])
def test_unreadable_missing_path_is_failure_not_cached_success(tmp_path,cls):
 r=fixture_reader(tmp_path,cls);r();r.paths[0].unlink()
 with pytest.raises(StopObservationFailure):r()
 assert len(list(r.errors_dir.glob('*.json')))==1

@pytest.mark.parametrize('cls',[FreshFileIOStopReader])
def test_repeated_current_content_only_memoizes_decode_not_reads(tmp_path,cls):
 r=fixture_reader(tmp_path,cls);r();r();assert r.reads==12 and r.parses==6;r.paths[5].write_bytes(b'{"stopped":"yes"}')
 with pytest.raises(PersistentStop):r()
 assert r.reads==18 and r.parses==7
