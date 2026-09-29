import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.local_agent import advice
from tools.local_agent import cli
from tools.local_agent import git_ops
from tools.local_agent.common import LocalFlowError


@pytest.mark.skipif(sys.platform != "win32", reason="Windows schedule runner")
@pytest.mark.parametrize("missing_patrol", [False, True])
def test_scheduled_turn_dry_run_recovers_missing_patrol(tmp_path, missing_patrol):
    shell = shutil.which("powershell.exe")
    if shell is None:
        pytest.skip("Windows PowerShell unavailable")
    local = tmp_path / ".local_agent"
    local.mkdir()
    runner = tmp_path / "tools" / "local_agent" / "run_scheduled_turn.ps1"
    runner.parent.mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / "tools" / "local_agent" / "run_scheduled_turn.ps1"
    runner.write_bytes(source.read_bytes())
    (local / "windows_schedule.json").write_text(json.dumps({
        "codex_path": sys.executable,
        "thread_id": "11111111-1111-1111-1111-111111111111",
    }), encoding="utf-8")
    (local / "scheduled-last-enqueue.json").write_text(json.dumps({
        "slot": "19990101-00",
        "patrol_at_before": "same-patrol" if missing_patrol else "prior-patrol",
    }), encoding="utf-8")
    (local / "patrol.json").write_text(json.dumps({"at": "same-patrol"}), encoding="utf-8")
    result = subprocess.run(
        [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(runner), "-DryRun"],
        capture_output=True, text=True, timeout=10, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert f"recovery={str(missing_patrol)}" in result.stdout


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


def test_recorded_patrol_detects_repeated_snapshot_without_treating_it_as_proof_of_idle(
        tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ACTIVITY", tmp_path / "activity.json")
    monkeypatch.setattr(cli, "PATROLS", tmp_path / "patrol.json")

    def fake_git(*args):
        if args == ("rev-parse", "HEAD"):
            return "a" * 40
        if args == ("show", "-s", "--format=%cI", "HEAD"):
            return "2026-09-01T00:00:00+00:00"
        raise AssertionError(args)

    monkeypatch.setattr(cli, "git", fake_git)
    first = cli.patrol(record=True)
    second = cli.patrol(record=True)
    assert first["consecutive_same_snapshot"] == 0
    assert second["consecutive_same_snapshot"] == 1
    assert second["health"] == "progress_unverified"
    assert "does not prove" in second["interpretation"]
    cli.write_json(cli.ACTIVITY, {"at": "2026-09-28T00:00:00+00:00",
                                  "summary": "A different bounded check was recorded."})
    third = cli.patrol(record=True)
    assert third["same_snapshot_as_previous_patrol"] is False
    assert third["consecutive_same_snapshot"] == 0


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
