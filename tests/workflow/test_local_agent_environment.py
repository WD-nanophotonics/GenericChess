import json
from pathlib import Path
import pytest
from tools.local_agent import environment as e, cli
from tools.local_agent.common import LocalFlowError


@pytest.fixture
def checkout(tmp_path, monkeypatch):
    root=tmp_path/'aux'; (root/'.local_agent').mkdir(parents=True)
    role=dict(role='DEV_AUX', branch='sidemission', checkout=str(root))
    (root/'.local_agent/role.json').write_text(json.dumps(role))
    (root/'.local_agent/rollout.json').write_text(json.dumps(dict(thread_id='aux-chat')))
    monkeypatch.setattr(e,'ROOT',root)
    def git(*args, **kwargs):
        assert kwargs.get('cwd') == root
        if args == ('rev-parse','--show-toplevel'): return str(root)
        if args == ('branch','--show-current'): return 'sidemission'
        if args == ('rev-parse','HEAD'): return 'a'*40
        if args == ('ls-remote','origin','refs/heads/sidemission'): return 'a'*40+' refs/heads/sidemission'
        raise AssertionError(args)
    monkeypatch.setattr(e,'git',git)
    return root, role


def test_primary_default_cwd_does_not_override_aux_identity(checkout,tmp_path,monkeypatch):
    root,_=checkout
    primary=tmp_path/'primary'; (primary/'.local_agent').mkdir(parents=True)
    (primary/'.local_agent/role.json').write_text(json.dumps(dict(role='PRIMARY_SANDBOX')))
    monkeypatch.chdir(primary)
    report=e.require_identity()
    assert report['identity']=='MATCH' and report['code']=='READY'
    assert report['cwd_differs'] and report['observed_role']=='DEV_AUX'
    assert report['checkout']==str(root)


@pytest.mark.parametrize('change,code',[(dict(role='PRIMARY_SANDBOX'),'ROLE_MISMATCH'),
    (dict(branch='sandbox'),'BRANCH_MISMATCH'),(dict(checkout='/other'),'CHECKOUT_MISMATCH')])
def test_actual_role_record_mismatch_is_specific(checkout,change,code):
    root,role=checkout;role.update(change)
    (root/'.local_agent/role.json').write_text(json.dumps(role))
    assert e.identity()['code']==code
    with pytest.raises(LocalFlowError,match=code): e.require_identity()


def test_actual_git_branch_mismatch_is_detected(checkout,monkeypatch):
    root,_=checkout; original=e.git
    monkeypatch.setattr(e,'git',lambda *a,**k:'sandbox' if a[0]=='branch' else original(*a,**k))
    assert e.identity()['code']=='BRANCH_MISMATCH'


def test_permission_failure_is_unknown_not_primary_or_bad_heartbeat(checkout,monkeypatch):
    def denied(*a,**k): raise PermissionError('Permission denied')
    monkeypatch.setattr(e,'read_json',denied)
    report=e.identity()
    assert report['identity']=='UNKNOWN' and report['code']=='LOCAL_ACCESS_DENIED'
    assert report['phase']=='role_read' and 'heartbeat' not in report


def test_supported_access_recovery_clears_previous_error(checkout,monkeypatch):
    original=e.git
    def denied(*a,**k): raise LocalFlowError('fatal: cannot change directory: Permission denied')
    monkeypatch.setattr(e,'git',denied)
    assert e.identity()['identity']=='UNKNOWN'
    monkeypatch.setattr(e,'git',original)
    assert e.identity()['code']=='READY'


def test_missing_role_is_unverified_and_never_inferred_from_cwd(checkout):
    root,_=checkout;(root/'.local_agent/role.json').unlink()
    assert e.identity()['code']=='IDENTITY_UNVERIFIED'


def test_remote_check_success_and_failure_do_not_reassign_role(checkout,monkeypatch):
    assert e.doctor(check_remote=True)['remote']['status']=='MATCH'
    original=e.git
    def fail(*a,**k):
        if a[0]=='ls-remote': raise LocalFlowError('Authentication failed')
        return original(*a,**k)
    monkeypatch.setattr(e,'git',fail)
    report=e.doctor(check_remote=True)
    assert report['identity']=='MATCH'
    assert report['remote']['code']=='REMOTE_AUTHENTICATION_FAILED'


@pytest.mark.parametrize('phase,text,code',[
    ('local_index','index.lock: Permission denied','LOCAL_INDEX_ACCESS_DENIED'),
    ('remote','Could not resolve host','REMOTE_NETWORK_FAILED'),
    ('remote','rejected non-fast-forward','REMOTE_HISTORY_DIVERGED')])
def test_git_failure_keeps_the_actual_failure_phase(phase,text,code):
    assert e.git_failure(phase,text)['code']==code


def test_heartbeat_is_separate_and_read_failure_is_unknown(checkout,tmp_path):
    root,_=checkout;config=tmp_path/'automation.toml'
    assert e.heartbeat_check(root,config)['status']=='UNKNOWN'
    config.write_text('id="dev-aux"\ntarget_thread_id="aux-chat"\nstatus="ACTIVE"\n')
    assert e.heartbeat_check(root,config)['status']=='MATCH'
    config.write_text('id="dev-aux"\ntarget_thread_id="other-chat"\n')
    assert e.heartbeat_check(root,config)['status']=='MISMATCH'
    assert e.identity()['identity']=='MATCH'


def test_unset_codex_home_does_not_search_filesystem_root(checkout,tmp_path,monkeypatch):
    root,_=checkout;monkeypatch.delenv('CODEX_HOME',raising=False)
    monkeypatch.setattr(e.Path,'home',lambda:tmp_path/'user')
    assert e.heartbeat_check(root)['status']=='UNKNOWN'


def test_aux_status_uses_own_origin_ref_without_legacy_consultation(checkout,monkeypatch):
    root,_=checkout
    monkeypatch.setattr(cli,'STATE',root/'.local_agent')
    def git(*a):
        assert 'origin/sandbox' not in a
        return '' if a[0]=='status' else 'a'*40
    monkeypatch.setattr(cli,'git',git)
    monkeypatch.setattr(cli,'consult_status',lambda:pytest.fail('must not consult Dot ledger'))
    report=cli.status()
    assert report['origin_ref']=='origin/sidemission'
    assert 'origin_sandbox' not in report


def test_direct_aux_publish_is_explicitly_rejected(checkout,monkeypatch,capsys):
    root,_=checkout;monkeypatch.setattr(cli,'STATE',root/'.local_agent')
    monkeypatch.setattr(cli,'publish',lambda *a:pytest.fail('must not invoke PRIMARY publisher'))
    assert cli.main(['publish','--tests','bounded-target'])==2
    assert 'DEV_AUX_ROUTE_ERROR' in capsys.readouterr().err


def test_cli_write_denial_does_not_infer_branch_or_mutate(checkout,monkeypatch,capsys):
    root,_=checkout;monkeypatch.setattr(cli,'STATE',root/'.local_agent')
    def fail(): raise LocalFlowError('LOCAL_ACCESS_DENIED: role unknown; use supported escalation')
    monkeypatch.setattr(e,'require_identity',fail)
    monkeypatch.setattr(cli,'note',lambda *a:pytest.fail('must not write'))
    assert cli.main(['note','--summary','specific enough diagnostic finding'])==2
    err=capsys.readouterr().err
    assert 'LOCAL_ACCESS_DENIED' in err and 'BRANCH_MISMATCH' not in err
