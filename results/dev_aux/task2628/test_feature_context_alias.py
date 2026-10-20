"""Replays both legal states in the supplemental guard-alias witness."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2511.generic import NonScoringTerminal
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

ROOT = Path(__file__).resolve().parents[3]


def test_guard_threshold_witness_replays_with_same_features_and_different_drop_availability():
    path = ROOT / "results/dev_aux/task2628/feature-context-alias-v2.json"
    witness = json.loads(path.read_text(encoding="utf-8"))["witness"]
    raw = json.loads((ROOT / witness["rule_path"]).read_text(encoding="utf-8"))
    compiled = compile_ruleset_for_execution(ruleset_from_dict(raw))
    states = []
    for row in witness["states"]:
        env = FixedScaleSessionEnv(GameSession.replay(compiled,
            deserialize_game_record(json.dumps(row["record"]))))
        try:
            terminal = env.terminal()
        except NonScoringTerminal:
            terminal = "UNKNOWN"
        assert terminal is None
        assert list(env.features()) == witness["features"]
        assert env.player() == witness["side_to_move"]
        drop_count = sum(getattr(getattr(choice, "action", None), "pattern_id", None)
                         == "sem_00_drop_zone_capacity_guard" for choice in env.actions())
        assert drop_count == row["legal_guarded_drop_count"]
        states.append((row["zone_count"], row["guard_open"], drop_count))
    assert {state[0] for state in states} == {0, 3}
    assert {state[1] for state in states} == {False, True}
    assert {state[2] for state in states} == {0, 9}


def test_context_alias_witness_manifest_binds_source_and_input_hashes():
    base = ROOT / "results/dev_aux/task2628"
    manifest = json.loads((base / "feature-context-alias-v2-manifest-final.json").read_text(encoding="utf-8"))
    files = {
        "result": base / "feature-context-alias-v2.json",
        "search_script": base / "feature_context_alias.py",
        "regression_test": base / "test_feature_context_alias.py",
        "inputs": ROOT / "results/dev_aux/task2411/inputs.json",
        "rules": ROOT / "results/dev_aux/task2411/rules-5.json",
        "fixed_scale": ROOT / "results/dev_aux/task2621/fixed_scale.py",
    }
    for name, path in files.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["sha256"][name]
