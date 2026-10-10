"""Duplicate launches reuse only the matching local game service."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import sys

import pytest
import run_web
from generic_chess.ui.web.identity import APPLICATION, instance_id


@pytest.fixture
def occupied_port():
    payload = {}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_port, payload
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.mark.parametrize("no_browser", [False, True])
def test_duplicate_launch_opens_existing_service(occupied_port, tmp_path, monkeypatch, no_browser):
    port, payload = occupied_port
    payload.update(ok=True, application=APPLICATION, instance_id=instance_id(tmp_path))
    opened = []
    monkeypatch.setattr(run_web.webbrowser, "open", opened.append)
    argv = ["run_web.py", "--port", str(port), "--state-dir", str(tmp_path)]
    if no_browser:
        argv.append("--no-browser")
    monkeypatch.setattr(sys, "argv", argv)
    assert run_web.main() == 0
    assert opened == ([] if no_browser else [f"http://127.0.0.1:{port}"])


@pytest.mark.parametrize("mismatch", ["application", "instance_id", "ok"])
def test_port_conflict_does_not_open_unrelated_service(occupied_port, tmp_path, monkeypatch, capsys, mismatch):
    port, payload = occupied_port
    payload.update(ok=True, application=APPLICATION, instance_id=instance_id(tmp_path))
    payload[mismatch] = False if mismatch == "ok" else "other"
    opened = []
    monkeypatch.setattr(run_web.webbrowser, "open", opened.append)
    monkeypatch.setattr(sys, "argv", ["run_web.py", "--port", str(port), "--state-dir", str(tmp_path)])
    assert run_web.main() == 1
    assert not opened
    assert "--port" in capsys.readouterr().err


def test_invalid_health_response_is_not_reused(monkeypatch, tmp_path):
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit): return b"not json"
    monkeypatch.setattr(run_web.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    assert not run_web.running_game("http://127.0.0.1:8765", tmp_path)


def test_health_identifies_save_directory(tmp_path):
    from fastapi.testclient import TestClient
    from generic_chess.ui.web.app import create_app
    with TestClient(create_app(tmp_path)) as client:
        health = client.get("/api/health").json()
        assert health["application"] == APPLICATION
        assert health["instance_id"] == instance_id(tmp_path)
        assert health["instance_id"] != instance_id(tmp_path / "other")
