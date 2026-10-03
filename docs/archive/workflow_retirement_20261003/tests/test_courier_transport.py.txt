import json
from contextlib import contextmanager
from pathlib import Path
import pytest
from tools.local_agent import advice, courier
from tools.local_agent.common import LocalFlowError


CONFIG = {'transport': 'courier', 'project_id': 'g-p-project', 'thread_id': 'chat',
          'chat_url': 'https://chatgpt.com/g/g-p-project-generic-chess/c/chat'}


def test_fixed_url_refuses_other_chat_project_and_host():
    assert courier.bound_url(CONFIG) == CONFIG['chat_url']
    for url in ('https://chatgpt.com/c/chat', CONFIG['chat_url'] + '?other=1',
                CONFIG['chat_url'].replace('/c/chat', '/c/other'),
                CONFIG['chat_url'].replace('chatgpt.com', 'example.com')):
        with pytest.raises(LocalFlowError):
            courier.bound_url({**CONFIG, 'chat_url': url})


class RenderedTurns:
    def __init__(self, turns): self.turns = turns
    def evaluate_all(self, _): return self.turns
    def count(self): return 0


class Page:
    url = CONFIG['chat_url']
    def __init__(self, turns): self.turns = turns
    def locator(self, selector):
        return RenderedTurns(self.turns if selector.startswith('article') else [])


def test_reply_is_bound_to_exact_user_body_and_completed_rendered_turn(tmp_path, monkeypatch):
    monkeypatch.setattr(advice, 'configuration', lambda: CONFIG)
    message = tmp_path / 'message.txt'; message.write_text('REQUEST_ID=one\nquestion')
    request = {'message_file': str(message), 'thread_id': 'chat'}
    rows = [{'id': 'u', 'user': message.read_text()},
            {'id': 'a', 'user': None, 'reply': 'REQUEST_ID=one\nuseful', 'copy': True}]
    result = courier.snapshot(Page(rows), request)
    assert result['turns'][0]['status'] == 'completed'
    rows[1]['copy'] = False
    assert courier.snapshot(Page(rows), request)['turns'][0]['status'] == 'inProgress'
    rows[0]['user'] = 'REQUEST_ID=one\ndifferent body'
    assert not courier.snapshot(Page(rows), request)['turns']


def test_uncertain_send_never_clicks_or_resubmits(tmp_path, monkeypatch):
    state = tmp_path / 'state'; state.mkdir()
    message = state / 'message.txt'; message.write_text('REQUEST_ID=one\nquestion')
    request = {'request_id': 'one', 'state': 'SEND_UNCERTAIN', 'thread_id': 'chat',
               'transport': 'courier', 'message_file': str(message),
               'payload_sha256': advice.sha(message.read_text().encode())}
    monkeypatch.setattr(advice, 'STATE', state)
    monkeypatch.setattr(advice, 'LEDGER', state / 'ledger.json')
    advice.write_json(advice.LEDGER, {'requests': {'one': request}})
    monkeypatch.setattr(advice, 'configuration', lambda: {**CONFIG, 'enabled': True,
                         'quota_status': 'verified_no_extra_worker', 'courier_mode': 'ordinary_chat_verified'})
    @contextmanager
    def page(): yield Page([])
    monkeypatch.setattr(courier, 'browser_page', page)
    monkeypatch.setattr(courier, 'inspect_page', lambda *_: {'composer_ready': True, 'ordinary_mode_verified_now': True})
    result = courier.exchange('one', send=True)
    assert result['state'] == 'SEND_UNCERTAIN' and not result['resend_permitted']


def test_unverified_mode_cannot_submit(tmp_path, monkeypatch):
    state = tmp_path / 'state'; state.mkdir()
    monkeypatch.setattr(advice, 'STATE', state)
    monkeypatch.setattr(advice, 'LEDGER', state / 'ledger.json')
    advice.write_json(advice.LEDGER, {'requests': {'one': {'request_id': 'one',
                      'state': 'PREPARED', 'thread_id': 'chat', 'transport': 'courier'}}})
    monkeypatch.setattr(advice, 'configuration', lambda: CONFIG)
    @contextmanager
    def page(): yield Page([])
    monkeypatch.setattr(courier, 'browser_page', page)
    monkeypatch.setattr(courier, 'inspect_page', lambda *_: {'composer_ready': True, 'ordinary_mode_verified_now': False})
    assert courier.exchange('one', send=True)['action'] == 'CAPABILITY_PENDING'
    assert advice.read_json(advice.LEDGER)['requests']['one']['state'] == 'PREPARED'
