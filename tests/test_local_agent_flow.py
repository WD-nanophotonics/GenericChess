from pathlib import Path

import pytest

from tools.local_agent import advice
from tools.local_agent import git_ops
from tools.local_agent.common import LocalFlowError


def test_daily_consultation_is_reserved_before_transport_and_cannot_duplicate(
        tmp_path, monkeypatch):
    monkeypatch.setattr(advice, "STATE", tmp_path)
    monkeypatch.setattr(advice, "LEDGER", tmp_path / "consultations.json")
    calls = []

    def courier(*args):
        calls.append(args)
        if args[0] == "courier_prepare":
            return {"request_directory": str(tmp_path / "one-request")}
        return {"event": "response_received", "ok": True}

    monkeypatch.setattr(advice, "_courier", courier)
    question = tmp_path / "question.txt"
    question.write_text("What primary literature supports a generic context-selection principle?",
                        encoding="utf-8")
    first = advice.consult(question)
    assert first["state"] == "COMPLETED"
    assert len(calls) == 2
    with pytest.raises(LocalFlowError, match="already reserved"):
        advice.consult(question)
    assert len(calls) == 2
    payload = Path(first["message_file"]).read_text(encoding="utf-8")
    assert "primary" in payload.lower()
    assert "not a work-order issuer" in payload
    assert "literal full URLs" in payload


def test_pending_consultation_blocks_next_day_until_reconciled(tmp_path, monkeypatch):
    monkeypatch.setattr(advice, "STATE", tmp_path)
    monkeypatch.setattr(advice, "LEDGER", tmp_path / "consultations.json")
    advice.write_json(advice.LEDGER, {
        "days": {"2026-09-27": {"state": "PENDING", "request_directory": "old"}}
    })
    question = tmp_path / "question.txt"
    question.write_text("Please find the original paper.", encoding="utf-8")
    with pytest.raises(LocalFlowError, match="needs reconciliation"):
        advice.consult(question)


def test_publish_refuses_diverged_remote_before_tests_or_push(monkeypatch):
    monkeypatch.setattr(git_ops, "_check_branch", lambda *_: None)
    monkeypatch.setattr(git_ops, "_tests", lambda *_: pytest.fail("tests should not run"))
    monkeypatch.setattr(git_ops, "_push", lambda *_: pytest.fail("push should not run"))

    def fake_git(*args, **_kwargs):
        if args == ("rev-parse", "origin/sandbox"):
            return "a" * 40
        if args == ("rev-parse", "HEAD"):
            return "b" * 40
        return ""

    monkeypatch.setattr(git_ops, "git", fake_git)
    monkeypatch.setattr(git_ops, "run", lambda *_args, **_kwargs: "c" * 40)
    with pytest.raises(LocalFlowError, match="diverged"):
        git_ops.publish(["tests/test_session.py"])


def test_promote_refuses_candidate_that_is_not_published(monkeypatch):
    monkeypatch.setattr(git_ops, "_check_branch", lambda *_: None)
    monkeypatch.setattr(git_ops, "_tests", lambda *_: pytest.fail("tests should not run"))

    def fake_git(*args, **_kwargs):
        if args == ("rev-parse", "HEAD"):
            return "a" * 40
        if args == ("rev-parse", "origin/sandbox"):
            return "b" * 40
        return ""

    monkeypatch.setattr(git_ops, "git", fake_git)
    with pytest.raises(LocalFlowError, match="published sandbox HEAD"):
        git_ops.promote("a" * 40, ["tests/test_session.py"])
