"""One DeepSeek executor; native desktop GPT heartbeat supplies supervision."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import msvcrt
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tomllib
import uuid
import urllib.error
import urllib.request

CODE_ROOT = Path(__file__).resolve().parents[2]
_local_role_file = CODE_ROOT / '.local_agent/role.json'
_local_role = json.loads(_local_role_file.read_text(encoding='utf-8')) if _local_role_file.exists() else {}
MAIN_ROOT = Path(_local_role.get('project_root', str(CODE_ROOT))).resolve()
HERE = MAIN_ROOT / '.local_agent/deepseek-runtime'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(CODE_ROOT))
from tools.local_agent.common import read_json, write_json

PATHS = read_json(HERE / 'paths.json')
ROOT = Path(PATHS.get('worktree', str(MAIN_ROOT / '.local_agent/worktrees/deepseek-aux'))).resolve()
CONTROL = HERE / 'control.json'
MIN_SECONDS, MAX_SECONDS, MAX_TURNS = 3601, 4800, 16
SUPERVISOR = '01a14ade-739d-7172-97a4-183ace749529'


def utc():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def locked():
    with (HERE / 'executor.lock').open('a+b') as handle:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError('One executor already owns the lock; no duplicate launched.')
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def git(*args):
    return subprocess.run([git_path(), *args], cwd=ROOT, capture_output=True,
                          text=True, encoding='utf-8', errors='replace', check=True).stdout


def stopped():
    return any(read_json(ROOT / '.local_agent' / name).get(key, False)
               for name in ('rollout.json', 'advisor.json', 'slack.json')
               for key in ('user_paused', 'stopped'))


def codex_path():
    candidate = os.environ.get('CODEX_CLI_PATH')
    if candidate and Path(candidate).is_file():
        return candidate
    # Desktop sets CODEX_CLI_PATH internally; ordinary terminals often do not.
    # Discover the installed desktop binary without changing global PATH/config.
    local_roots = [Path.home() / 'AppData/Local']
    if os.environ.get('LOCALAPPDATA'):
        local_roots.append(Path(os.environ['LOCALAPPDATA']))
    candidates = [path for base in local_roots
                  for path in (base / 'OpenAI/Codex/bin').glob('*/codex.exe')
                  if path.is_file() and path.stat().st_size > 1]
    if candidates:
        return str(max(candidates, key=lambda path: path.stat().st_mtime))
    return shutil.which('codex')


def git_path():
    candidate = shutil.which('git')
    if candidate:
        return candidate
    for base in (Path(os.environ.get('ProgramFiles', 'C:/Program Files')),
                 Path.home() / 'AppData/Local/Programs'):
        candidate = base / 'Git/cmd/git.exe'
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError('Git executable not found; no work started.')


def toml_value(value):
    if isinstance(value, dict):
        return '{' + ', '.join(json.dumps(k) + '=' + toml_value(v) for k, v in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ', '.join(toml_value(v) for v in value) + ']'
    return json.dumps(value, ensure_ascii=False)


def config_args():
    # Reuse the installed user's sandbox/state, without loading or modifying
    # their global provider/plugin configuration. All overrides are process-local.
    config = tomllib.loads((HERE / 'config.toml').read_text(encoding='utf-8'))
    args = ['--ignore-user-config']
    for name, value in config.items():
        args += ['-c', name + '=' + toml_value(value)]
    return args


def preflight():
    config = tomllib.loads((HERE / 'config.toml').read_text(encoding='utf-8'))
    assert config['model_provider'] == 'genericchess_deepseek'
    assert config['model_providers']['genericchess_deepseek']['base_url'] == 'https://api.deepseek.com'
    assert config['sandbox_mode'] == 'workspace-write'
    assert not config['features']['multi_agent']
    assert codex_path(), 'Codex CLI not found'
    assert ROOT != MAIN_ROOT and ROOT.is_relative_to(MAIN_ROOT / '.local_agent/worktrees'), 'Expected isolated project worktree'
    assert git('branch', '--show-current').strip() == 'codex/deepseek-aux', 'Expected DeepSeek auxiliary branch'
    role = read_json(ROOT / '.local_agent/role.json')
    assert role.get('agent_id') == 'DEEPSEEK_AUX' and role.get('branch') == 'codex/deepseek-aux', 'Wrong checkout role'
    for secret in ('key.clixml', 'key.dpapi'):
        ignored = subprocess.run([git_path(), 'check-ignore', str(HERE / secret)],
                                 cwd=MAIN_ROOT, capture_output=True, text=True, check=True).stdout.strip()
        assert ignored, 'Credential destination is not Git-ignored'
    for name in ('worker.md', 'final.schema.json', 'supervisor.md'):
        assert (HERE / name).is_file(), f'Missing {name}'
    print('Preflight OK: isolated DEEPSEEK_AUX branch/state, sole API executor, ignored secrets; no API call.')


def arm():
    with locked():
        preflight()
        registration = read_json(HERE / 'automation.json')
        if not registration.get('id'):
            raise RuntimeError('Native heartbeat has not been configured.')
        state = read_json(CONTROL)
        if state.get('armed'):
            print('Already armed; clock, review and progress preserved.')
            return
        if state.get('cycle_status') in ('running', 'pending_review', 'needs_attention'):
            raise RuntimeError('Unreviewed or interrupted work exists; supervisor must reconcile it before resuming.')
        session = read_json(ROOT / '.local_agent/session.json')
        if session.get('state') == 'active' and session.get('thread_id') != SUPERVISOR:
            raise RuntimeError('Auxiliary session belongs to another control chat; preserve it.')
        if not credential_saved():
            raise RuntimeError('Enter the key with deepseek-control.cmd Start first.')
        backup = HERE / 'activation' / uuid.uuid4().hex
        backup.mkdir(parents=True)
        if (HERE / 'stop.json').exists():
            shutil.copy2(HERE / 'stop.json', backup / 'stop.json')
        # Only this explicit user Start may revoke an earlier scoped stop.
        write_json(HERE / 'stop.json', {'stopped': False, 'at': utc(),
                                      'instruction': 'User invoked Start'})
        for name in ('rollout', 'advisor', 'slack'):
            path = ROOT / '.local_agent' / (name + '.json')
            shutil.copy2(path, backup / path.name)
            data = read_json(path)
            data.setdefault('explicit_resume_history', []).append({
                'at': utc(), 'instruction': 'User invoked deepseek-control Start',
                'scope': 'Resume ONLY DEEPSEEK_AUX; PRIMARY_SANDBOX and DEV_AUX untouched',
                'prior_user_paused': data.get('user_paused'), 'prior_stopped': data.get('stopped')})
            if name == 'rollout':
                data.update(user_paused=False, thread_id=SUPERVISOR, agent_id='DEEPSEEK_AUX')
            elif name == 'advisor':
                data.update(enabled=True)
            else:
                data.update(stopped=False, dispatch_enabled=True, resumed_at=utc())
            write_json(path, data)
        memo_path = ROOT / '.local_agent/NEXT_WORK.md'
        shutil.copy2(memo_path, backup / memo_path.name)
        lines = memo_path.read_text(encoding='utf-8').splitlines()
        lines = [('State: DEEPSEEK_AUX only; independent PRIMARY GPT and DEV_AUX; PUBLIC; latest scoped stop wins; no mainline takeover.'
                  if line.startswith('State:') else line) for line in lines]
        temporary = memo_path.with_suffix('.deepseek.tmp')
        temporary.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        os.replace(temporary, memo_path)
        state.update(armed=True, activated_at=utc(), cycle_status='ready', supervisor=SUPERVISOR)
        write_json(CONTROL, state)
        print('Explicit DEEPSEEK_AUX resume recorded; mainline state unchanged.')


def pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        api.OpenProcess.restype = wintypes.HANDLE
        api.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        api.GetExitCodeProcess.restype = wintypes.BOOL
        api.CloseHandle.argtypes = (wintypes.HANDLE,)
        api.CloseHandle.restype = wintypes.BOOL
        handle = api.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            return bool(api.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            api.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def status():
    state = read_json(CONTROL)
    print(json.dumps({'armed': state.get('armed', False), 'shared_stop': stopped(),
                      'credential_saved': credential_saved(),
                      'cycle_status': state.get('cycle_status', 'not_started'),
                      'observed_status': 'interrupted' if state.get('cycle_status') == 'running' and not pid_alive(state.get('pid')) else state.get('cycle_status', 'not_started'),
                      'cycle': state.get('cycle'), 'pid': state.get('pid'),
                      'last_review': {k: v for k, v in state.get('review', {}).items() if k != 'notes'},
                      'agent_id': 'DEEPSEEK_AUX', 'worktree': str(ROOT),
                      'heartbeat': read_json(HERE / 'automation.json').get('id'),
                      'supervisor': SUPERVISOR}, ensure_ascii=False))


def stop():
    # This operation must not wait for the long-held executor lock.
    # The separate stop sentinel is atomic and never overwritten by cycle updates.
    write_json(HERE / 'stop.json', {'stopped': True, 'at': utc(), 'instruction': 'User invoked Stop'})
    for name in ('rollout', 'slack'):
        path = ROOT / '.local_agent' / (name + '.json')
        data = read_json(path)
        if name == 'rollout':
            data['user_paused'] = True
        else:
            data.update(stopped=True, dispatch_enabled=False, stopped_at=utc())
        write_json(path, data)
    print('Stop recorded. Owned worker is cancelled within the polling interval; supervisor will pause its heartbeat.')


def should_stop():
    return read_json(HERE / 'stop.json').get('stopped', False) or stopped()


def credential_saved():
    return any((HERE / name).exists() for name in ('key.dpapi', 'key.clixml'))


def decrypt_key():
    if (HERE / 'key.dpapi').exists():
        import key_store
        return key_store.load(HERE / 'key.dpapi')
    # Secret stays in a pipe/environment; never in argv, config, request logs or stdout.
    code = "$ErrorActionPreference='Stop';$s=Import-Clixml -LiteralPath '" + str(HERE / 'key.clixml').replace("'", "''") + "';Write-Output ([System.Net.NetworkCredential]::new('', $s).Password)"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', code],
                            capture_output=True, text=True, check=True, timeout=15)
    if not result.stdout.strip():
        raise RuntimeError('Saved credential could not be decrypted.')
    return result.stdout.strip()


def probe():
    # Authentication/model listing only, invoked by the user Start AFTER key entry.
    request = urllib.request.Request('https://api.deepseek.com/models',
              headers={'Authorization': 'Bearer ' + decrypt_key()})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            models = json.load(response)
        if 'deepseek-flash' not in {m.get('id') for m in models.get('data', [])}:
            raise RuntimeError('Authenticated model list does not include deepseek-flash.')
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'DeepSeek authentication/model-list check failed: HTTP {exc.code}; no automatic retry.') from None
    except urllib.error.URLError:
        raise RuntimeError('DeepSeek connection failed; no automatic retry. Check network access.') from None
    print('DeepSeek key/model-list check passed; no generation task was requested.')


def kill_owned(proc):
    if proc.poll() is None:
        # proc.pid comes only from the Popen object created by this runner.
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                       capture_output=True, timeout=15, check=False)
        proc.wait(timeout=15)


def auxiliary_admission():
    """Default alternation, not a lock on mainline or on explicit safe parallelism."""
    state = read_json(HERE / 'coordination.json')
    activity = state.get('dev_aux_state', 'unknown')
    if activity in ('paused', 'idle', 'completed'):
        return
    if (activity == 'running' and state.get('parallel_authorization')
            and state.get('explicit_parallel') is True
            and state.get('file_claim_conflicts') == []):
        return
    raise RuntimeError('Auxiliary overlap/state unresolved: inspect task claims; mainline is unaffected.')


def launch():
    # No ad-hoc scheduler: this launches one bounded cycle for the native heartbeat.
    with locked():
        state = read_json(CONTROL)
        if not state.get('armed') or should_stop():
            print('Disarmed/stopped; nothing launched.')
            return
        if state.get('cycle_status') not in ('ready', 'reviewed'):
            raise RuntimeError('Review/reconcile previous cycle before starting another.')
        if state.get('review', {}).get('decision') == 'hold':
            raise RuntimeError('Supervisor hold; no automatic restart.')
        preflight()
        auxiliary_admission()
        state.update(cycle_status='running', pid=os.getpid(), launched_at=utc())
        write_json(CONTROL, state)
        # Keep the supported exec tool session alive. A detached grandchild can
        # be terminated when its short-lived launcher/tool job exits on Windows.
        print(f'One bounded DeepSeek cycle starting in tracked tool session; pid={os.getpid()}.', flush=True)
        return run_locked()


def duration_decision(active_seconds, final, commands):
    disposition = final.get('disposition')
    if disposition in ('exception', 'objective_complete'):
        return 'needs_review_exception'
    if not commands:
        return 'needs_review_no_tool_evidence'
    if active_seconds >= MIN_SECONDS and disposition == 'checkpoint':
        return 'pending_review'
    return 'continue'


def run():
    # Launch releases the lock after writing PID; acquire once, without a second writer.
    deadline = time.monotonic() + 10
    while True:
        try:
            with locked():
                return run_locked()
        except RuntimeError as exc:
            if 'already owns' not in str(exc) or time.monotonic() >= deadline:
                raise
            time.sleep(0.2)


def run_locked():
    state = read_json(CONTROL)
    if state.get('pid') != os.getpid() or not state.get('armed') or should_stop():
        return
    cycle = HERE / 'cycles' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    cycle.mkdir(parents=True)
    starting_session = read_json(ROOT / '.local_agent/session.json')
    receipt = {'resumed_session_id': starting_session.get('id') if starting_session.get('state') == 'active' else None,
               'started_at': utc(), 'active_seconds': 0, 'turns': 0, 'tool_commands': 0,
               'base_sha': git('rev-parse', 'HEAD').strip(), 'status': 'running'}
    (cycle / 'baseline.diff').write_text(git('diff', 'HEAD', '--'), encoding='utf-8')
    state.update(cycle=str(cycle.resolve()), cycle_status='running')
    write_json(CONTROL, state)
    thread_id = state.get('worker_thread_id')
    proc = None
    try:
        env = os.environ.copy()
        env['CODEX_HOME'] = str(Path.home() / '.codex')
        env['DEEPSEEK_API_KEY'] = decrypt_key()
        env['PATH'] = os.pathsep.join([str(Path(codex_path()).parent),
                                      str(Path(git_path()).parent), env.get('PATH', '')])
        # Parent desktop thread/tool pipes must not be impersonated by the executor.
        for key in ('CODEX_THREAD_ID', 'CODEX_SESSION_ID', 'CODEX_APP_TOOLS_PIPE_PATH'):
            env.pop(key, None)
        prompt = (HERE / 'worker.md').read_text(encoding='utf-8')
        if state.get('review'):
            prompt += '\nLatest authoritative supervisor review: ' + json.dumps(state['review'], ensure_ascii=False)
        while receipt['turns'] < MAX_TURNS and receipt['active_seconds'] < MAX_SECONDS:
            if should_stop():
                receipt['status'] = 'user_stop'
                break
            receipt['turns'] += 1
            turn = receipt['turns']
            args = [codex_path(), 'exec']
            if thread_id:
                args += ['resume', thread_id]
            else:
                args += ['-C', str(ROOT)]
            args += config_args()
            args += ['--json', '--output-schema', str(HERE / 'final.schema.json'),
                     '-o', str(cycle / f'final-{turn}.json'), '-']
            (cycle / f'prompt-{turn}.txt').write_text(prompt, encoding='utf-8')
            began = time.monotonic()
            with (cycle / f'events-{turn}.jsonl').open('wb') as out, (cycle / f'stderr-{turn}.txt').open('wb') as err:
                proc = subprocess.Popen(args, cwd=ROOT, env=env, stdin=subprocess.PIPE,
                                        stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
                proc.stdin.write(prompt.encode('utf-8'))
                proc.stdin.close()
                while proc.poll() is None:
                    if should_stop() or receipt['active_seconds'] + time.monotonic() - began >= MAX_SECONDS:
                        receipt['status'] = 'user_stop' if should_stop() else 'runtime_limit'
                        kill_owned(proc)
                        break
                    time.sleep(2)
            receipt['active_seconds'] += time.monotonic() - began
            events = []
            for line in (cycle / f'events-{turn}.jsonl').read_text(encoding='utf-8', errors='replace').splitlines():
                try:
                    events.append(json.loads(line))
                except ValueError:
                    pass
            turn_commands = 0
            for event in events:
                if event.get('type') == 'thread.started':
                    thread_id = event.get('thread_id') or thread_id
                if event.get('type') == 'item.completed' and event.get('item', {}).get('type') == 'command_execution':
                    receipt['tool_commands'] += 1
                    turn_commands += 1
            receipt['worker_thread_id'] = thread_id
            write_json(cycle / 'receipt.json', receipt)
            if receipt['status'] != 'running':
                break
            if proc.returncode != 0:
                receipt.update(status='tool_or_api_failure', exit_code=proc.returncode)
                break
            final = read_json(cycle / f'final-{turn}.json')
            receipt['final'] = final
            decision = duration_decision(receipt['active_seconds'], final, turn_commands)
            if decision != 'continue':
                receipt['status'] = decision
                break
            if not thread_id:
                receipt['status'] = 'missing_resume_id'
                break
            prompt = (f'Continue the same DEEPSEEK_AUX segment. Actual active runtime {receipt["active_seconds"]/60:.1f}min; '
                      'normal finish requires >60min and useful evidence, safe close by 75min (hard cap80). '
                      'Execute the next decision-changing step; no padding/restarts. Obey latest stop and supervisor review.')
        else:
            receipt['status'] = 'runtime_limit' if receipt['active_seconds'] >= MAX_SECONDS else 'continuation_limit'
    except BaseException as exc:
        receipt.update(status='runner_failure', failure_type=type(exc).__name__)
        if proc is not None:
            kill_owned(proc)
        raise
    finally:
        receipt.update(ended_at=utc(), duration_gate_passed=receipt['active_seconds'] >= MIN_SECONDS,
                       end_sha=git('rev-parse', 'HEAD').strip())
        (cycle / 'final.diff').write_text(git('diff', receipt['base_sha'], '--'), encoding='utf-8')
        (cycle / 'git-status.txt').write_text(git('status', '--short'), encoding='utf-8')
        write_json(cycle / 'receipt.json', receipt)
        state = read_json(CONTROL)
        state.update(cycle_status='pending_review', worker_thread_id=thread_id, pid=None)
        if receipt['status'] == 'user_stop':
            state['armed'] = False
        write_json(CONTROL, state)


def matching_session(receipt, session):
    # A migrated active segment retains its original UUID/UTC start. A newly
    # created segment must instead begin in this cycle; neither permits an old
    # unrelated completed session to count as this cycle's evidence.
    resumed = receipt.get('resumed_session_id')
    if resumed:
        return session.get('id') == resumed
    return bool(session.get('started_at') and
                session['started_at'] >= receipt.get('started_at', ''))


def review(decision, notes_file):
    with locked():
        state = read_json(CONTROL)
        if state.get('cycle_status') != 'pending_review':
            raise RuntimeError('No finished cycle is pending review.')
        notes = Path(notes_file).read_text(encoding='utf-8').strip()
        if not notes:
            raise RuntimeError('Review needs concrete evidence-based findings/next direction.')
        receipt = read_json(ROOT / state['cycle'] / 'receipt.json')
        if decision == 'accept':
            if receipt.get('status') == 'pending_review':
                session = read_json(ROOT / '.local_agent/session.json')
                if (receipt.get('active_seconds', 0) < MIN_SECONDS
                        or not session.get('duration_gate_passed')
                        or session.get('state') != 'ended'
                        or not matching_session(receipt, session)):
                    raise RuntimeError('Normal acceptance requires >60min and a matching closed validated session.')
            elif receipt.get('status') == 'needs_review_exception':
                final = receipt.get('final', {})
                if not final.get('reason') or not final.get('evidence'):
                    raise RuntimeError('Exception acceptance requires a concrete reason and evidence.')
            else:
                raise RuntimeError('Failed/interrupted/no-evidence cycles cannot be accepted as completed work.')
        state.update(cycle_status='reviewed', review={'decision': decision, 'notes': notes,
                     'at': utc(), 'cycle': state['cycle'], 'model': 'gpt-6.1-sol'})
        if decision == 'hold':
            state['armed'] = False
        write_json(CONTROL, state)
        write_json(ROOT / state['cycle'] / 'supervisor-review.json', state['review'])
        print(f'Review recorded: {decision}. DeepSeek performs any implementation/fixes.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['preflight', 'probe', 'arm', 'status', 'stop', 'launch', 'run', 'review'])
    parser.add_argument('--decision', choices=['accept', 'revise', 'hold'])
    parser.add_argument('--notes-file')
    options = parser.parse_args()
    if options.action == 'review':
        if not options.decision or not options.notes_file:
            parser.error('review requires --decision and --notes-file')
        review(options.decision, options.notes_file)
    else:
        globals()[options.action]()
