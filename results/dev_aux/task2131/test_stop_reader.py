import json,os
from pathlib import Path
import pytest
from results.dev_aux.task2131.stop_reader import ParsedStopReader
from results.dev_aux.task109.adapter import stop_check,PersistentStop

def flags(tmp_path):
 root=tmp_path/'DEV_AUX';other=tmp_path/'GenericChess 2'
 for folder in(root,other):
  (folder/'.local_agent').mkdir(parents=True)
  for name in('rollout.json','advisor.json','slack.json'):
   (folder/'.local_agent'/name).write_text(json.dumps(dict(user_paused=False,stopped=False,history={'stopped':True},padding='x'*500)),encoding='utf-8')
 return root

def test_reads_every_flag_each_poll_but_decodes_identical_bytes_once(tmp_path):
 root=flags(tmp_path);r=ParsedStopReader(root)
 for _ in range(10):stop_check(root);r()
 assert r.reads==60 and r.parses==6 and r.bytes_read>30000

@pytest.mark.parametrize('owner',('DEV_AUX','GenericChess 2'))
@pytest.mark.parametrize('field',('user_paused','stopped'))
def test_same_size_same_mtime_content_change_stops_on_same_call(tmp_path,owner,field):
 root=flags(tmp_path);r=ParsedStopReader(root);r();path=tmp_path/owner/'.local_agent'/'rollout.json';before=path.stat();raw=path.read_bytes();needle=('"'+field+'": false').encode();changed=raw.replace(needle,('"'+field+'": true ').encode(),1);assert len(changed)==len(raw);path.write_bytes(changed);os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
 with pytest.raises(PersistentStop):stop_check(root)
 with pytest.raises(PersistentStop):r()

@pytest.mark.parametrize('failure',('missing','invalid'))
def test_cached_false_never_hides_new_read_or_parse_errors(tmp_path,failure):
 root=flags(tmp_path);r=ParsedStopReader(root);r();path=root/'.local_agent'/'advisor.json'
 if failure=='missing':path.unlink();error=FileNotFoundError
 else:path.write_bytes(b'{');error=json.JSONDecodeError
 with pytest.raises(error):stop_check(root)
 with pytest.raises(error):r()

def test_stop_then_resume_only_actual_new_bytes_reparsed(tmp_path):
 root=flags(tmp_path);r=ParsedStopReader(root);r();path=root/'.local_agent'/'slack.json';original=path.read_bytes();path.write_bytes(b'{"user_paused":true}')
 with pytest.raises(PersistentStop):r()
 path.write_bytes(original);r();stop_check(root);assert r.parses==8
