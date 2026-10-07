from pathlib import Path
import subprocess
import pytest
from tools.local_agent import git_ops
from tools.local_agent.common import LocalFlowError

def test_publish_refuses_divergence_before_tests(monkeypatch):
    monkeypatch.setattr(git_ops, '_check_branch', lambda *_: None)
    monkeypatch.setattr(git_ops, '_tests', lambda *_: pytest.fail('must not run tests'))
    monkeypatch.setattr(git_ops, 'git', lambda *args, **_: ('a' * 40 if args == ('rev-parse', 'origin/sandbox') else 'b' * 40))
    monkeypatch.setattr(git_ops, 'run', lambda *_, **__: 'c' * 40)
    with pytest.raises(LocalFlowError, match='diverged'):
        git_ops.publish(['tests/test_session.py'])

def test_single_checkout_promotion_fast_forwards_local_origin(tmp_path, monkeypatch):
    origin = tmp_path / 'origin.git'; repo = tmp_path / 'new-checkout'; repo.mkdir()
    def run(*args, cwd=repo):
        return subprocess.check_output(['git', '-c', 'core.autocrlf=false', *args], cwd=cwd, stderr=subprocess.STDOUT).decode().strip()
    run('init', '--bare', str(origin)); run('init'); run('config', 'user.name', 'Transport test'); run('config', 'user.email', 'test@example.invalid')
    run('checkout', '-b', 'master'); (repo / 'a.txt').write_text('base'); run('add', '.'); run('commit', '-m', 'base'); run('remote', 'add', 'origin', str(origin)); run('push', 'origin', 'master')
    run('checkout', '-b', 'sandbox'); (repo / 'a.txt').write_text('candidate'); run('add', '.'); run('commit', '-m', 'candidate'); run('push', 'origin', 'sandbox'); candidate = run('rev-parse', 'HEAD')
    monkeypatch.setattr(git_ops, 'ROOT', repo)
    monkeypatch.setattr(git_ops, 'git', lambda *args, cwd=repo: run(*args, cwd=cwd))
    monkeypatch.setattr(git_ops, '_tests', lambda *_: None)
    assert git_ops.promote(candidate, ['bounded-test'])['promoted_sha'] == candidate
    assert run('rev-parse', 'master') == candidate and run('branch', '--show-current') == 'sandbox'
