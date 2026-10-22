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
