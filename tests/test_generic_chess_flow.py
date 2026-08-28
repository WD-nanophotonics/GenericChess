from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generic_chess_flow", ROOT / "tools" / "generic_chess_flow.py"
)
assert SPEC and SPEC.loader
flow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flow)


def test_chat_control_footer_is_explicit_and_last_value_wins():
    text = """Work order body.
GENERICCHESS_STATUS=CONTINUE
GENERICCHESS_PROMOTION=HOLD
IGNORED=value
GENERICCHESS_STATUS=COMPLETE
GENERICCHESS_CANDIDATE_SHA=0123456789abcdef0123456789abcdef01234567
"""
    assert flow.parse_control_footer(text) == {
        "GENERICCHESS_STATUS": "COMPLETE",
        "GENERICCHESS_PROMOTION": "HOLD",
        "GENERICCHESS_CANDIDATE_SHA": "0123456789abcdef0123456789abcdef01234567",
    }


def test_local_start_never_requires_courier(monkeypatch, tmp_path):
    master = tmp_path / "master"
    sandbox = tmp_path / "sandbox"
    master.mkdir()
    sandbox.mkdir()
    monkeypatch.setattr(flow, "install_hooks", lambda _root: None)
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda _root, _branch: None)
    monkeypatch.setattr(flow, "sha", lambda path, ref="HEAD": "a" * 40 if path == master else "b" * 40)
    saved = {}
    monkeypatch.setattr(flow, "save_state", lambda _root, state: saved.update(state))
    monkeypatch.setattr(flow, "load_state", lambda _root, required=False: {})
    monkeypatch.setattr(
        flow, "courier_capabilities",
        lambda _root: pytest.fail("local mode must not inspect Courier"),
    )

    flow.command_start(tmp_path, SimpleNamespace(mode="local", message_file=None))

    assert saved["active"] is True
    assert saved["mode"] == "local"


def test_active_session_cannot_change_authority_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(
        flow, "load_state", lambda _root, required=False: {"active": True, "mode": "courier"}
    )
    with pytest.raises(flow.FlowError, match="cannot change authority mode"):
        flow.command_start(tmp_path, SimpleNamespace(mode="local", message_file=None))


def test_courier_promotion_requires_exact_approved_sha(monkeypatch, tmp_path):
    candidate = "c" * 40
    state = {
        "mode": "courier",
        "tested_shas": {candidate: ["tests/test_session.py"]},
        "chat_control": {
            "GENERICCHESS_PROMOTION": "APPROVE",
            "GENERICCHESS_CANDIDATE_SHA": "d" * 40,
        },
    }
    master = tmp_path / "master"
    sandbox = tmp_path / "sandbox"
    master.mkdir()
    sandbox.mkdir()
    monkeypatch.setattr(flow, "load_state", lambda _root: state)
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda _root, _branch: None)
    monkeypatch.setattr(flow, "sha", lambda path, ref="HEAD": candidate if path == sandbox else "a" * 40)
    monkeypatch.setattr(flow, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))

    with pytest.raises(flow.FlowError, match="not bound"):
        flow.command_promote(tmp_path, SimpleNamespace(candidate=candidate))


def test_promotion_rejects_unpublished_or_untested_candidate(monkeypatch, tmp_path):
    candidate = "c" * 40
    master = tmp_path / "master"
    sandbox = tmp_path / "sandbox"
    master.mkdir()
    sandbox.mkdir()
    monkeypatch.setattr(flow, "load_state", lambda _root: {"mode": "local", "tested_shas": {}})
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda _root, _branch: None)
    monkeypatch.setattr(flow, "sha", lambda path, ref="HEAD": candidate if path == sandbox else "a" * 40)

    with pytest.raises(flow.FlowError, match="has not passed publish tests"):
        flow.command_promote(tmp_path, SimpleNamespace(candidate=candidate))
