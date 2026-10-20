"""Role-local diagnostics: a default cwd or access failure is not an identity."""
from __future__ import annotations
import json
import os
from pathlib import Path
import tomllib
from .common import ROOT, LocalFlowError, git, read_json


def git_failure(phase, error):
    text = str(error)
    lower = text.lower()
    if any(x in lower for x in ('permission denied', 'access is denied', 'access denied')):
        code = 'LOCAL_INDEX_ACCESS_DENIED' if phase == 'local_index' else (
            'REMOTE_ACCESS_DENIED' if phase == 'remote' else 'LOCAL_ACCESS_DENIED')
    elif phase == 'remote' and any(x in lower for x in ('authentication failed', 'could not read username')):
        code = 'REMOTE_AUTHENTICATION_FAILED'
    elif phase == 'remote' and any(x in lower for x in ('could not resolve host', 'failed to connect')):
        code = 'REMOTE_NETWORK_FAILED'
    elif phase == 'remote' and any(x in lower for x in ('non-fast-forward', 'fetch first')):
        code = 'REMOTE_HISTORY_DIVERGED'
    else:
        code = 'COMMAND_FAILED'
    return dict(phase=phase, code=code, error=text)


def identity(root=None):
    root = Path(root if root is not None else ROOT).resolve()
    report = dict(expected_role='DEV_AUX', expected_branch='sidemission',
        checkout=str(root), calling_cwd=str(Path.cwd()),
        cwd_differs=Path.cwd().resolve() != root, identity='UNKNOWN', code='IDENTITY_UNVERIFIED')
    phase = 'role_read'
    try:
        role = read_json(root/'.local_agent'/'role.json')
        report['observed_role'] = role.get('role')
        if not all(role.get(k) for k in ('role', 'branch', 'checkout')):
            return report
        phase = 'git_root'
        top = git('rev-parse', '--show-toplevel', cwd=root)
        phase = 'git_branch'
        branch = git('branch', '--show-current', cwd=root)
        report.update(repo_root=top, observed_branch=branch)
        mismatch = ('ROLE_MISMATCH' if role['role'] != 'DEV_AUX' else
            'BRANCH_MISMATCH' if role['branch'] != 'sidemission' or branch != 'sidemission' else
            'CHECKOUT_MISMATCH' if Path(role['checkout']).resolve() != root else
            'GIT_ROOT_MISMATCH' if Path(top).resolve() != root else None)
        report.update(identity='MISMATCH' if mismatch else 'MATCH', code=mismatch or 'READY')
    except PermissionError as error:
        report.update(code='LOCAL_ACCESS_DENIED', phase=phase, error=str(error))
    except (LocalFlowError, OSError) as error:
        report.update(git_failure(phase, error))
    except (ValueError, TypeError, KeyError) as error:
        report.update(code='CONFIG_INVALID', phase=phase, error=str(error))
    return report


def require_identity():
    result = identity()
    if result['identity'] != 'MATCH':
        raise LocalFlowError(json.dumps(result, ensure_ascii=False))
    return result


def heartbeat_check(root, path=None):
    root = Path(root)
    # Never recurse or treat an unset CODEX_HOME as the filesystem root.
    config_root = Path(os.environ.get('CODEX_HOME') or Path.home()/'.codex')
    target = Path(path) if path is not None else config_root/'automations'/'dev-aux'/'automation.toml'
    result = dict(status='UNKNOWN')
    try:
        expected = read_json(root/'.local_agent'/'rollout.json').get('thread_id')
        actual = tomllib.loads(target.read_text(encoding='utf-8-sig'))
        result.update(expected_thread_id=expected, observed_thread_id=actual.get('target_thread_id'),
            automation_id=actual.get('id'), automation_status=actual.get('status'))
        if not expected or not actual.get('target_thread_id'):
            return result
        result['status'] = 'MATCH' if actual.get('id') == 'dev-aux' and actual['target_thread_id'] == expected else 'MISMATCH'
    except (OSError, ValueError, LocalFlowError) as error:
        result['error'] = str(error)
    return result


def doctor(check_remote=False, check_heartbeat=False):
    result = identity()
    if check_heartbeat:
        result['heartbeat'] = heartbeat_check(ROOT)
    if check_remote and result['identity'] == 'MATCH':
        try:
            local = git('rev-parse', 'HEAD', cwd=ROOT)
            lines = git('ls-remote', 'origin', 'refs/heads/sidemission', cwd=ROOT).splitlines()
            remote = lines[0].split()[0] if lines else None
            result['remote'] = dict(status='MATCH' if local == remote else 'DIFFERENT',
                local_sha=local, remote_sha=remote, branch='sidemission')
        except (LocalFlowError, OSError) as error:
            result['remote'] = dict(status='UNKNOWN', **git_failure('remote', error))
    return result
