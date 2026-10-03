"""Fixed-URL browser courier. No model/API calls, global queue or old runtime."""
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlsplit

from . import advice
from .common import STATE, LocalFlowError, read_json, write_json

PROFILE = STATE / 'courier' / 'profile'
EVIDENCE = STATE / 'courier' / 'preflight.json'


def bound_url(config):
    url = config.get('chat_url', '')
    parsed = urlsplit(url)
    expected = f"/g/{config['project_id']}-generic-chess/c/{config['thread_id']}"
    if (parsed.scheme != 'https' or parsed.netloc != 'chatgpt.com'
            or parsed.path != expected or parsed.query or parsed.fragment):
        raise LocalFlowError('Courier requires the exact verified fixed project/chat URL')
    return url


def open_browser():
    config = advice.configuration()
    url = bound_url(config)
    PROFILE.mkdir(parents=True, exist_ok=True)
    # This is a fresh project-owned profile, never normal Chrome User Data,
    # archived authentication, an old Courier queue or another project's browser.
    port = PROFILE / 'DevToolsActivePort'
    if port.exists():
        try:
            with browser_page(login_inspection=True) as page:
                return inspect_page(page, config)
        except Exception as exc:
            raise LocalFlowError('Existing Courier endpoint unavailable; inspect its process before reopening') from exc
    chrome = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Google/Chrome/Application/chrome.exe'
    if not chrome.is_file():
        raise LocalFlowError('Google Chrome is unavailable')
    subprocess.Popen([str(chrome), f'--user-data-dir={PROFILE.resolve()}',
                      '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0',
                      '--no-first-run', '--no-default-browser-check', url],
                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    deadline = time.monotonic() + 20
    while not port.exists() and time.monotonic() < deadline:
        time.sleep(.2)
    if not port.exists():
        raise LocalFlowError('Dedicated Courier browser did not start within 20 seconds')
    with browser_page(login_inspection=True) as page:
        return inspect_page(page, config)


@contextmanager
def browser_page(login_inspection=False):
    from playwright.sync_api import sync_playwright
    config = advice.configuration()
    expected = bound_url(config)
    port = int((PROFILE / 'DevToolsActivePort').read_text().splitlines()[0])
    if not 1 <= port <= 65535:
        raise LocalFlowError('Invalid dedicated browser endpoint')
    with sync_playwright() as runtime:
        browser = runtime.chromium.connect_over_cdp(f'http://127.0.0.1:{port}', timeout=10000)
        pages = [p for c in browser.contexts for p in c.pages if p.url == expected]
        if not pages and login_inspection:
            pages = [p for c in browser.contexts for p in c.pages
                     if urlsplit(p.url).hostname in {'chatgpt.com', 'auth.openai.com'}]
        if len(pages) != 1:
            raise LocalFlowError('Fixed chat URL is absent or ambiguous; no draft or send attempted')
        yield pages[0]
        # Disconnecting Playwright leaves the owned Chrome profile open for login.


def inspect_page(page, config):
    if page.url != bound_url(config):
        parsed = urlsplit(page.url)
        if parsed.hostname == 'auth.openai.com' or (parsed.hostname == 'chatgpt.com' and parsed.path in {'/', '/auth/login', '/auth/login/'}):
            result = {'state': 'LOGIN_REQUIRED', 'expected_url': bound_url(config), 'send_attempted': False}
            write_json(EVIDENCE, result)
            return result
        raise LocalFlowError('Wrong conversation; Courier refuses to operate')
    composer = page.locator('#prompt-textarea')
    ready = composer.count() == 1 and composer.is_visible() and composer.is_editable()
    buttons = page.get_by_role('button').all_inner_texts()
    mode_selector = config.get('courier_chat_mode_selector')
    expected_mode = config.get('courier_chat_mode_text')
    mode = page.locator(mode_selector) if mode_selector else None
    mode_verified = bool(mode and mode.count() == 1 and mode.inner_text().strip() == expected_mode)
    result = {'url': page.url, 'thread_id': config['thread_id'],
              'composer_ready': ready, 'visible_button_labels': buttons,
              'transport_model_calls': 0, 'extra_work_launches': 0,
              'ordinary_mode_verified_now': mode_verified,
              'state': 'MODE_QUALIFICATION_REQUIRED' if ready else 'LOGIN_OR_COMPOSER_REQUIRED',
              'at': advice.now().isoformat()}
    write_json(EVIDENCE, result)
    return result


def snapshot(page, request):
    config = advice.configuration()
    if page.url != bound_url(config) or request['thread_id'] != config['thread_id']:
        raise LocalFlowError('Wrong conversation')
    # Read rendered turns only; no private endpoints, network interception,
    # authentication-store reads, hidden state or billing assumptions.
    turns = page.locator('article[data-testid^="conversation-turn-"]').evaluate_all(
        "els => els.map(el => ({id:el.getAttribute('data-testid'), "
        "user:el.querySelector('[data-message-author-role=user]')?.innerText, "
        "reply:el.querySelector('[data-message-author-role=assistant]')?.innerText, "
        "copy:!!el.querySelector('button[data-testid=copy-turn-action-button]')}))")
    message = Path(request['message_file']).read_text(encoding='utf-8')
    result = {'thread': {'id': request['thread_id'], 'kind': 'chatgpt'}, 'turns': []}
    active = page.locator('button[data-testid="stop-button"],button[data-testid="stop-generating-button"]').count() > 0
    for i, turn in enumerate(turns):
        if (turn.get('user') or '').strip() != message.strip():
            continue
        item = {'type': 'userMessage', 'content': [{'type': 'text', 'text': message}]}
        record = {'id': turn['id'], 'status': 'inProgress', 'items': [item]}
        if i + 1 < len(turns):
            following = turns[i + 1]
            if following.get('reply') and following['copy'] and not active:
                text = following['reply']
                errors = ('something went wrong', 'usage limit', 'rate limit', '达到上限', '请求过多')
                if any(marker in text.casefold() for marker in errors):
                    record['error'] = 'visible Chat UI error; read only'
                else:
                    record['status'] = 'completed'
                    record['items'].append({'type': 'agentMessage', 'id': following['id'], 'text': text})
        result['turns'].append(record)
    return result


def exchange(request_id, *, send=False):
    config = advice.configuration()
    if config['transport'] != 'courier':
        raise LocalFlowError('Courier is not the selected transport')
    with advice.locked():
        ledger = read_json(advice.LEDGER)
        request = advice.select(ledger, request_id)
        if not request or request['transport'] != 'courier':
            raise LocalFlowError('Request belongs to another transport')
        with browser_page() as page:
            result = inspect_page(page, config)
            if send:
                if (not config.get('enabled') or config.get('quota_status') != 'verified_no_extra_worker'
                        or config.get('courier_mode') != 'ordinary_chat_verified'
                        or not result.get('ordinary_mode_verified_now')):
                    return {**result, 'action': 'CAPABILITY_PENDING'}
                if request['state'] != 'PREPARED':
                    send = False  # An uncertain send is always read-only, never resent.
                elif not result['composer_ready']:
                    return result
                else:
                    message = Path(request['message_file']).read_text(encoding='utf-8')
                    if advice.sha(message.encode()) != request['payload_sha256']:
                        raise LocalFlowError('Immutable payload changed')
                    if snapshot(page, request)['turns']:
                        send = False
                    else:
                        composer = page.locator('#prompt-textarea')
                        if composer.inner_text().strip():
                            raise LocalFlowError('Existing draft retained; no overwrite')
                        request.update(state='SEND_UNCERTAIN', send_started_at=advice.now().isoformat())
                        write_json(advice.LEDGER, ledger)  # Durable before any possible submission.
                        composer.fill(message)
                        page.locator('button[data-testid="send-button"]').click(timeout=5000)
                        # No automatic retry even when click or acknowledgement fails.
            evidence = snapshot(page, request)
            path = Path(request['message_file']).with_name('courier-snapshot.json')
            write_json(path, evidence)
    return advice.reconcile_snapshot(request_id, path)
