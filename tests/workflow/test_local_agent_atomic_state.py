"""The existing atomic state writer keeps stop/configuration reads intact."""
import json
import threading
import pytest
from tools.local_agent import common

def test_atomic_state_write_keeps_complete_old_json_until_commit(tmp_path, monkeypatch):
    target = tmp_path / 'rollout.json'
    old = {'user_paused': True, 'generation': 0, 'padding': 'x' * 16384}
    new = dict(old, generation=1)
    common.write_json(target, old)
    temporary_ready = threading.Event()
    read_done = threading.Event()
    observed = []
    errors = []
    original_replace = common.os.replace
    def replace_after_read(source, destination):
        if destination == target:
            temporary_ready.set()
            assert read_done.wait(5)
        return original_replace(source, destination)
    def reader():
        try:
            assert temporary_ready.wait(5)
            raw = target.read_bytes()
            assert raw
            observed.append(json.loads(raw))
        except BaseException as exc:
            errors.append(exc)
        finally:
            read_done.set()
    monkeypatch.setattr(common.os, 'replace', replace_after_read)
    thread = threading.Thread(target=reader)
    thread.start()
    try:
        common.write_json(target, new)
    finally:
        thread.join(5)
    assert not thread.is_alive() and not errors
    assert observed == [old]
    assert json.loads(target.read_bytes()) == new

def test_failed_atomic_state_replace_preserves_previous_stop_flags(tmp_path, monkeypatch):
    target = tmp_path / 'rollout.json'
    old = {'user_paused': True, 'stopped': True, 'generation': 0}
    common.write_json(target, old)
    original = target.read_bytes()
    def interrupted(*args):
        raise PermissionError('controlled replacement failure')
    monkeypatch.setattr(common.os, 'replace', interrupted)
    with pytest.raises(PermissionError, match='controlled replacement failure'):
        common.write_json(target, dict(old, generation=1))
    assert target.read_bytes() == original
    assert json.loads(target.read_bytes()) == old

def test_transient_windows_replace_retries_same_complete_temporary(tmp_path,monkeypatch):
    target=tmp_path/'rollout.json';old=dict(user_paused=True,stopped=True,generation=0)
    new=dict(old,generation=1);common.write_json(target,old);original=target.read_bytes();replace=common.os.replace;attempts=[]
    def once_locked(source,destination):
        attempts.append(source)
        assert target.read_bytes()==original and json.loads(source.read_bytes())==new
        if len(attempts)==1:
            error=PermissionError('temporary Windows denial');error.winerror=5;raise error
        return replace(source,destination)
    monkeypatch.setattr(common.os,'replace',once_locked)
    common.write_json(target,new)
    assert len(attempts)==2 and attempts[0]==attempts[1]
    assert json.loads(target.read_bytes())==new


def test_permanent_windows_replace_failure_stays_bounded_and_keeps_stops(tmp_path,monkeypatch):
    target=tmp_path/'rollout.json';old=dict(user_paused=True,stopped=True,generation=0)
    common.write_json(target,old);original=target.read_bytes();attempts=[]
    def always_locked(source,destination):
        attempts.append(source);error=PermissionError('persistent Windows denial');error.winerror=32;raise error
    monkeypatch.setattr(common.os,'replace',always_locked)
    with pytest.raises(PermissionError,match='persistent Windows denial'):
        common.write_json(target,dict(old,generation=1))
    assert 1<=len(attempts)<=3 and len(set(attempts))==1
    assert target.read_bytes()==original and json.loads(target.read_bytes())==old
