"""F24H product-boundary contracts for the certified Western RuleSet."""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from generic_chess import (
    build_builtin_ruleset,
    build_western_chess_ruleset,
    compile_ruleset,
    compile_ruleset_for_execution,
)
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.cli.play import _resolve_action_input, visible_action_alias
from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.coordinates import Square
from generic_chess.rules.schema import compute_fingerprint
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.session.serialization import deserialize_game_record, serialize_game_record
from generic_chess.session.session import GameSession


ROOT = Path(__file__).resolve().parents[1]


def _run_cli(args, input_text="quit\n"):
    return subprocess.run(
        [sys.executable, "-m", *args],
        cwd=ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_production_builder_is_semantically_identical_to_f24f_definition():
    from scripts.audit_f24f_western_chess_perft import western_chess_ruleset
    from scripts.audit_f24g_canonical_western_perft import f24f_artifact_sha256

    production = build_western_chess_ruleset()
    certified = western_chess_ruleset()
    assert serialize_ruleset(production) == serialize_ruleset(certified)
    assert compute_fingerprint(production) == compute_fingerprint(certified)
    assert f24f_artifact_sha256(ROOT) == {
        "scripts/audit_f24f_western_chess_perft.py": "5739cee5d3c8c618575e93e3b6ca11a0f5bd251387a9a70de1587387884362f4",
        "tests/test_f24f_western_chess_perft.py": "45a7329cda11fcffb23281cc148e43de1e10a3f06f76d3c4fa26cbf758395575",
        "tests/fixtures/f24f_western_chess_perft.json": "2c8fefbb22eb061123f2e40b379f9fc95dff0dd6154e3b7dfbd6363972cee4c2",
        "docs/architecture/ADR-082-western-chess-perft-certification.md": "f24b2149c576a2dd64b8fca1fffad9da07ca2563e5dce1b38abd7fe0329db8c5",
    }


def test_generic_dispatcher_preserves_legacy_compile_contract():
    from generic_chess.generation.config import GeneratorConfig
    from generic_chess.generation.generator import generate_game

    ruleset = generate_game(GeneratorConfig(seed=42)).ruleset
    legacy = compile_ruleset(ruleset)
    dispatched = compile_ruleset_for_execution(ruleset)
    assert type(dispatched) is type(legacy)
    assert dispatched.ruleset_fingerprint == legacy.ruleset_fingerprint
    assert GameSession(dispatched).legal_actions() == GameSession(legacy).legal_actions()


def test_dispatcher_selects_semantic_path_without_legacy_fallback():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    from generic_chess.rules.ir import CompiledSemanticRuleset

    assert isinstance(compiled, CompiledSemanticRuleset)
    assert type(compiled).__name__ == "ExecutableSemanticRuleset"
    assert len(GameSession(compiled).legal_actions()) == 20


def test_builtin_catalog_is_exact_and_unknown_names_fail():
    assert build_builtin_ruleset("western_chess") == build_western_chess_ruleset()
    with pytest.raises(ValueError, match="unknown built-in ruleset"):
        build_builtin_ruleset("western")


def test_semantic_ruleset_json_reloads_through_cli_and_alias_submits():
    path = ROOT / f".gc_f24h_rules_{uuid.uuid4().hex}.json"
    try:
        path.write_text(serialize_ruleset(build_western_chess_ruleset()), encoding="utf-8")
        proc = _run_cli(["generic_chess.cli.play", "--ruleset", str(path)], "e2-e4\nquit\n")
        assert proc.returncode == 0, proc.stderr
        assert "unknown input" not in proc.stdout
        assert "ply 1" in proc.stdout
    finally:
        path.unlink(missing_ok=True)


def test_builtin_ruleset_out_round_trips_to_ruleset_path():
    path = ROOT / f".gc_f24h_rules_{uuid.uuid4().hex}.json"
    try:
        first = _run_cli(
            ["generic_chess.cli.play", "--builtin-ruleset", "western_chess", "--ruleset-out", str(path)]
        )
        assert first.returncode == 0, first.stderr
        second = _run_cli(["generic_chess.cli.play", "--ruleset", str(path)])
        assert second.returncode == 0, second.stderr
        assert "legal actions:" in second.stdout
        assert first.stdout.splitlines()[0] == second.stdout.splitlines()[0]
    finally:
        path.unlink(missing_ok=True)


def test_builtin_cli_rejects_generator_options():
    proc = _run_cli(
        ["generic_chess.cli.play", "--builtin-ruleset", "western_chess", "--seed", "7"]
    )
    assert proc.returncode == 2
    assert "cannot be combined" in proc.stderr


def test_visible_alias_resolution_is_ambiguity_safe():
    left = SemanticBoardMove("p1", "g1", "R", Square(0, 0), Square(1, 0))
    right = SemanticBoardMove("p2", "g2", "R", Square(0, 0), Square(1, 0))
    chosen, error = _resolve_action_input("a1-b1", (left, right))
    assert chosen is None
    assert "ambiguous" in error
    exact, error = _resolve_action_input(str(right), (left, right))
    assert exact == right and error is None


def test_session_record_replay_preserves_semantic_action_identity():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    session = GameSession(compiled)
    for alias in ("e2-e4", "e7-e5"):
        action, error = _resolve_action_input(alias, session.legal_actions())
        assert error is None and action is not None
        session.submit(action)
    record_text = serialize_game_record(session.to_record())
    replayed = GameSession.replay(compiled, deserialize_game_record(record_text))
    assert replayed.state == session.state
    assert tuple(r.action for r in replayed.history) == tuple(r.action for r in session.history)
    assert replayed.compiled.ruleset_fingerprint == compiled.ruleset_fingerprint
    assert all(visible_action_alias(r.action) in {"e2-e4", "e7-e5"} for r in session.history)


def test_public_alphabeta_reaches_builtin_session():
    compiled = compile_ruleset_for_execution(build_builtin_ruleset("western_chess"))
    session = GameSession(compiled)
    decision = AlphaBetaPlayer(
        compiled, use_disk_cache=False, use_native_semantic_legality=True
    ).choose_action(
        session,
        SearchLimits(max_nodes=512, max_depth=8, quiescence_max_depth=4,
                     quiescence_hard_max_depth=8),
    )
    assert decision.action in session.legal_actions()
    before = session.state
    session.submit(decision.action)
    assert session.state != before
    assert session.history[-1].action == decision.action
