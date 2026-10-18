"""Offline behavior checks: no model calls, real flags or unrelated processes."""
from pathlib import Path
from unittest.mock import patch
import pytest
from tools.local_agent import deepseek_runner as r, git_ops
from tools.local_agent.common import read_json, write_json, LocalFlowError


def fixture(tmp_path, monkeypatch):
    main = tmp_path / 'main'; aux = main / '.local_agent/worktrees/deepseek-aux'
    home = main / '.local_agent/deepseek-runtime'
    home.mkdir(parents=True); (aux / '.local_agent').mkdir(parents=True)
    monkeypatch.setattr(r, 'MAIN_ROOT', main); monkeypatch.setattr(r, 'ROOT', aux)
    monkeypatch.setattr(r, 'HERE', home); monkeypatch.setattr(r, 'CONTROL', home/'control.json')
    for root in (main, aux):
        for name in ('rollout', 'advisor', 'slack'):
            write_json(root/'.local_agent'/f'{name}.json', {'owner':str(root), 'user_paused':False,'stopped':False})
    (aux/'.local_agent/NEXT_WORK.md').write_text('State: fixture\n')
    write_json(home/'automation.json', {'id':'existing-ds-timer'})
    return main, aux, home


def main_bytes(main):
    return {p.name:p.read_bytes() for p in (main/'.local_agent').glob('*.json')}


def test_aux_stop_does_not_change_mainline(tmp_path, monkeypatch):
    main, aux, home = fixture(tmp_path, monkeypatch); before = main_bytes(main)
    r.stop()
    assert read_json(home/'stop.json')['stopped']
    assert read_json(aux/'.local_agent/rollout.json')['user_paused']
    assert main_bytes(main)==before


def test_aux_arm_ignores_active_mainline_and_keeps_own_clock(tmp_path, monkeypatch):
    main, aux, home = fixture(tmp_path, monkeypatch)
    write_json(main/'.local_agent/session.json', {'state':'active','id':'main-clock'})
    write_json(aux/'.local_agent/session.json', {'state':'active','id':'aux-clock','thread_id':r.SUPERVISOR,'started_at':'fixed-UTC'})
    before=main_bytes(main); session=(aux/'.local_agent/session.json').read_bytes()
    monkeypatch.setattr(r,'preflight',lambda:None);monkeypatch.setattr(r,'credential_saved',lambda:True)
    r.arm()
    assert read_json(home/'control.json')['armed']
    assert main_bytes(main)==before and (aux/'.local_agent/session.json').read_bytes()==session


def test_mainline_pause_is_not_aux_pause(tmp_path, monkeypatch):
    main,aux,home=fixture(tmp_path,monkeypatch)
    write_json(main/'.local_agent/rollout.json', {'user_paused':True})
    assert not r.should_stop()
    write_json(aux/'.local_agent/rollout.json', {'user_paused':True})
    assert r.should_stop()


def test_one_api_lock_across_execution_directories(tmp_path, monkeypatch):
    main,aux,home=fixture(tmp_path,monkeypatch)
    with r.locked():
        monkeypatch.setattr(r,'ROOT',tmp_path/'another-directory')
        with pytest.raises(RuntimeError,match='already owns'):
            with r.locked(): pass


@pytest.mark.parametrize('activity,explicit,conflicts,allowed',[
    ('paused',False,[],True),('running',False,[],False),
    ('running',True,[],True),('running',True,['same.py'],False),('unknown',False,[],False)])
def test_default_aux_alternation_and_explicit_parallel(tmp_path,monkeypatch,activity,explicit,conflicts,allowed):
    _,_,home=fixture(tmp_path,monkeypatch)
    write_json(home/'coordination.json',dict(dev_aux_state=activity,explicit_parallel=explicit,
        parallel_authorization='direct-user-reference' if explicit else None,file_claim_conflicts=conflicts))
    if allowed:r.auxiliary_admission()
    else:
        with pytest.raises(RuntimeError,match='overlap/state'):r.auxiliary_admission()


@pytest.mark.parametrize('agent,branch',[('PRIMARY_SANDBOX','codex/deepseek-aux'),('DEEPSEEK_AUX','sandbox'),('DEEPSEEK_AUX','arbitrary')])
def test_publication_rejects_role_mismatch_before_tests(tmp_path,monkeypatch,agent,branch):
    monkeypatch.setattr(git_ops,'ROOT',tmp_path)
    write_json(tmp_path/'.local_agent/role.json',dict(agent_id=agent))
    monkeypatch.setattr(git_ops,'_tests',lambda *_:pytest.fail('must not test or push mismatched role'))
    with pytest.raises(LocalFlowError,match='match this checkout role'):git_ops.publish(['irrelevant'],branch)


def test_aux_publication_runs_tests_and_verifies_full_sha(tmp_path,monkeypatch):
    monkeypatch.setattr(git_ops,'ROOT',tmp_path)
    branch='codex/deepseek-aux';sha='a'*40;calls=[]
    write_json(tmp_path/'.local_agent/role.json',dict(agent_id='DEEPSEEK_AUX',branch=branch))
    monkeypatch.setattr(git_ops,'_check_branch',lambda _,b:calls.append(('branch',b)))
    monkeypatch.setattr(git_ops,'_tests',lambda t:calls.append(('tests',t)))
    monkeypatch.setattr(git_ops,'_push',lambda p,b,m:calls.append(('push',b,m)))
    monkeypatch.setattr(git_ops,'git',lambda *a,**_: '' if a[0]=='ls-remote' else sha)
    assert git_ops.publish(['related'],branch)==dict(published_sha=sha,branch=branch)
    assert calls.index(('tests',['related']))<calls.index(('push',branch,'publish'))


def test_status_reports_dead_launcher_as_interrupted_without_state_reset(tmp_path,monkeypatch,capsys):
    _,_,home=fixture(tmp_path,monkeypatch)
    write_json(home/'control.json',dict(armed=True,cycle_status='running',pid=12345))
    before=(home/'control.json').read_bytes()
    monkeypatch.setattr(r,'pid_alive',lambda _:False)
    r.status()
    assert '"observed_status": "interrupted"' in capsys.readouterr().out
    assert (home/'control.json').read_bytes()==before


def test_pid_alive_handles_current_windows_process_without_mutation():
    import os
    assert r.pid_alive(os.getpid())
    assert not r.pid_alive(None)


def test_real_aux_branch_hook_and_publisher(tmp_path,monkeypatch):
    import os,subprocess
    origin=tmp_path/'origin.git';repo=tmp_path/'ds-checkout';repo.mkdir()
    def command(*args,check=True,env=None):
        result=subprocess.run(['git','-c','core.autocrlf=false',*args],cwd=repo,
            capture_output=True,text=True,check=False,env=env)
        if check and result.returncode: raise AssertionError(result.stderr)
        return result
    command('init','--bare',str(origin));command('init');command('checkout','-b','codex/deepseek-aux')
    command('config','user.name','Agent fixture');command('config','user.email','agent@example.invalid')
    (repo/'.gitignore').write_text('.local_agent/\n');(repo/'a.txt').write_text('base')
    command('add','.');command('commit','-m','base');command('remote','add','origin',str(origin))
    hook=Path(__file__).resolve().parents[2]/'.githooks'
    command('config','core.hooksPath',str(hook))
    no_grant=dict(os.environ);no_grant.pop('GENERIC_CHESS_LOCAL_PUSH',None)
    refused=command('push','origin','codex/deepseek-aux',check=False,env=no_grant)
    assert refused.returncode!=0 and 'role-bound' in refused.stderr
    write_json(repo/'.local_agent/role.json',dict(agent_id='DEEPSEEK_AUX',branch='codex/deepseek-aux'))
    monkeypatch.setattr(git_ops,'ROOT',repo)
    monkeypatch.setattr(git_ops,'git',lambda *a,**_:command(*a).stdout.strip())
    monkeypatch.setattr(git_ops,'run',lambda *a,**_:command(*a[1:]).stdout.strip())
    tested=[];monkeypatch.setattr(git_ops,'_tests',lambda targets:tested.append(targets))
    result=git_ops.publish(['bounded-fixture'],'codex/deepseek-aux')
    assert tested==[['bounded-fixture']]
    assert result['published_sha']==command('rev-parse','HEAD').stdout.strip()
    # Even the publisher's hook mode must not authorize a non-fast-forward.
    old=command('rev-parse','HEAD').stdout.strip()
    (repo/'a.txt').write_text('advance');command('commit','-am','advance')
    git_ops.publish(['bounded-fixture'],'codex/deepseek-aux')
    env=dict(os.environ,GENERIC_CHESS_LOCAL_PUSH='publish')
    rejected=command('push','--force','origin',old+':refs/heads/codex/deepseek-aux',check=False,env=env)
    assert rejected.returncode!=0 and 'Non-fast-forward' in rejected.stderr


def test_review_matches_resumed_session_without_resetting_clock():
    receipt = dict(resumed_session_id='preserved', started_at='2026-10-18T12:00:00Z')
    assert r.matching_session(receipt, dict(id='preserved', started_at='2026-10-18T03:00:00Z'))
    assert not r.matching_session(receipt, dict(id='unrelated', started_at='2026-10-18T13:00:00Z'))
    assert not r.matching_session(dict(started_at='2026-10-18T12:00:00Z'), dict(started_at='2026-10-18T03:00:00Z'))
    assert r.matching_session(dict(started_at='2026-10-18T12:00:00Z'), dict(started_at='2026-10-18T13:00:00Z'))
