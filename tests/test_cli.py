"""CLI play/replay: subprocess smoke tests and injectable-stream unit tests."""

import json
import os
import shutil
import subprocess
import sys
import uuid
from io import StringIO
from pathlib import Path

import pytest

from generic_chess.cli import play as play_mod
from generic_chess.cli import replay as replay_mod
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.serialization import serialize_ruleset


@pytest.fixture()
def cli_tmp_dir():
    """Workspace-local temp dir (pytest's tmp_path is blocked by the sandbox)."""
    base = Path(__file__).resolve().parent.parent
    tmp = base / f".gc_cli_tmp_{uuid.uuid4().hex}"
    os.makedirs(tmp, mode=0o777)
    yield tmp
    resolved = tmp.resolve()
    if tmp.exists() and resolved.is_relative_to(base.resolve()):
        shutil.rmtree(resolved)


def _run(args, input_text):
    return subprocess.run(
        [sys.executable, "-m", *args],
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_play_smoke_fixed_seed():
    proc = _run(["generic_chess.cli.play", "--seed", "42"], "1\nhistory\nresign\n")
    assert proc.returncode == 0
    assert "legal actions:" in proc.stdout
    assert "resigned" in proc.stdout
    assert "Traceback" not in proc.stdout + proc.stderr


def test_play_invalid_input_continues():
    proc = _run(["generic_chess.cli.play", "--seed", "42"], "zzz\nquit\n")
    assert proc.returncode == 0
    assert "unknown input" in proc.stdout


def test_play_quit_exits_cleanly():
    proc = _run(["generic_chess.cli.play", "--seed", "42"], "quit\n")
    assert proc.returncode == 0
    assert "final result: ongoing" in proc.stdout


def test_play_record_out_and_replay(cli_tmp_dir: Path):
    ruleset = cli_tmp_dir / "rules.json"
    ruleset.write_text(
        serialize_ruleset(
            generate_game(GeneratorConfig(seed=42)).ruleset
        ),
        encoding="utf-8",
    )
    record = cli_tmp_dir / "game.json"
    proc = _run(
        ["generic_chess.cli.play", "--ruleset", str(ruleset), "--record-out", str(record)],
        "1\nresign\n",
    )
    assert proc.returncode == 0, proc.stderr
    assert record.exists()
    data = json.loads(record.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["actions"]

    replay = _run(
        ["generic_chess.cli.replay", "--ruleset", str(ruleset), "--record", str(record)],
        "",
    )
    assert replay.returncode == 0, replay.stderr
    assert "final result: resignation" in replay.stdout


def test_replay_fingerprint_mismatch_fails(cli_tmp_dir: Path):
    ruleset_a = cli_tmp_dir / "a.json"
    ruleset_b = cli_tmp_dir / "b.json"
    ruleset_a.write_text(
        serialize_ruleset(generate_game(GeneratorConfig(seed=42)).ruleset), encoding="utf-8"
    )
    ruleset_b.write_text(
        serialize_ruleset(generate_game(GeneratorConfig(seed=43)).ruleset), encoding="utf-8"
    )
    record = cli_tmp_dir / "game.json"
    proc = _run(
        ["generic_chess.cli.play", "--ruleset", str(ruleset_a), "--record-out", str(record)],
        "1\nresign\n",
    )
    assert proc.returncode == 0
    replay = _run(
        ["generic_chess.cli.replay", "--ruleset", str(ruleset_b), "--record", str(record)],
        "",
    )
    assert replay.returncode != 0
    assert "fingerprint" in replay.stderr
    assert "Traceback" not in replay.stderr


def test_play_ruleset_conflict_rejected():
    proc = _run(["generic_chess.cli.play", "--ruleset", "x.json", "--seed", "1"], "")
    assert proc.returncode == 2
    assert "cannot be combined" in proc.stderr


def test_replay_final_only(cli_tmp_dir: Path):
    ruleset = cli_tmp_dir / "rules.json"
    ruleset.write_text(
        serialize_ruleset(generate_game(GeneratorConfig(seed=42)).ruleset), encoding="utf-8"
    )
    record = cli_tmp_dir / "game.json"
    _run(
        ["generic_chess.cli.play", "--ruleset", str(ruleset), "--record-out", str(record)],
        "1\nresign\n",
    )
    replay = _run(
        [
            "generic_chess.cli.replay",
            "--ruleset",
            str(ruleset),
            "--record",
            str(record),
            "--final-only",
        ],
        "",
    )
    assert replay.returncode == 0
    assert "1. player" not in replay.stdout
    assert "final result" in replay.stdout


def test_record_write_failure_returns_nonzero(cli_tmp_dir: Path):
    proc = _run(
        ["generic_chess.cli.play", "--seed", "42", "--record-out", str(cli_tmp_dir)],
        "quit\n",
    )
    assert proc.returncode == 1
    assert "cannot write record file" in proc.stderr


def test_play_main_injectable_streams():
    out = StringIO()
    code = play_mod.main(["--seed", "42"], stdin=StringIO("1\nresign\n"), stdout=out)
    assert code == 0
    assert "resigned" in out.getvalue()


def test_replay_main_injectable_streams(cli_tmp_dir: Path):
    ruleset = cli_tmp_dir / "rules.json"
    ruleset.write_text(
        serialize_ruleset(generate_game(GeneratorConfig(seed=42)).ruleset), encoding="utf-8"
    )
    record = cli_tmp_dir / "game.json"
    play_mod.main(
        ["--ruleset", str(ruleset), "--record-out", str(record)],
        stdin=StringIO("1\nresign\n"),
        stdout=StringIO(),
    )
    out = StringIO()
    code = replay_mod.main(
        ["--ruleset", str(ruleset), "--record", str(record), "--final-only"],
        stdout=out,
    )
    assert code == 0
    assert "final result" in out.getvalue()
