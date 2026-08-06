"""Native vs Python Core differential gate (corpus, targeted, fuzz)."""

import json
from pathlib import Path

import pytest

from generic_chess.native import native_available

pytestmark = pytest.mark.skipif(
    not native_available(), reason="native extension not built"
)

from generic_chess.native.adapter import (
    native_legal_actions,
    pack_native_position,
    to_python_action,
)
from generic_chess.native.compiler import compile_native_rules
from generic_chess.native.reference import canonical_action_set, python_perft


def _corpus():
    path = (
        Path(__file__).resolve().parent.parent
        / "tests"
        / "fixtures"
        / "native_correctness_corpus_v1.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))["fixtures"]


def _native_legal_set(compiled, rules, state):
    pos = pack_native_position(compiled, rules, state)
    actions = []
    for packed in native_legal_actions(rules, pos):
        actions.append(to_python_action(rules, packed))
    return set(canonical_action_set(actions))


def test_corpus_legal_sets_and_perft():
    from generic_chess.ai.benchmark.audit_suite import (
        build_session,
        standard_ruleset_specs,
    )
    from generic_chess.native.adapter import native_perft

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    for fixture in _corpus():
        spec = specs[fixture["ruleset_fixture_id"]]
        compiled, session = build_session(
            spec, tuple(fixture["action_prefix"])
        )
        rules = compile_native_rules(compiled)
        pos = pack_native_position(compiled, rules, session.state)
        native_actions = [
            to_python_action(rules, a)
            for a in native_legal_actions(rules, pos)
        ]
        stored = {
            json.dumps(d, sort_keys=True) for d in fixture["legal_actions"]
        }
        assert set(canonical_action_set(native_actions)) == stored
        for d in (1, 2, 3):
            native_count = native_perft(rules, pos, d)["nodes"]
            assert native_count == fixture["perft"][str(d)]


def test_targeted_fixtures_differential():
    from generic_chess.ai.benchmark.targeted_fixtures import (
        build_targeted_fixtures,
    )
    from generic_chess.native.adapter import native_make_unmake_roundtrip, native_perft
    from generic_chess.native.reference import python_legal_actions

    fixtures = build_targeted_fixtures()
    assert fixtures
    for fixture in fixtures:
        compiled = fixture.compiled
        rules = compile_native_rules(compiled)
        pos = pack_native_position(compiled, rules, fixture.state)
        nat = set(
            canonical_action_set(
                [to_python_action(rules, a) for a in native_legal_actions(rules, pos)]
            )
        )
        py = set(
            canonical_action_set(python_legal_actions(fixture.state, compiled))
        )
        assert nat == py, fixture.fixture_id
        for action in native_legal_actions(rules, pos):
            check = native_make_unmake_roundtrip(rules, pos, action)
            assert all(
                check[k]
                for k in ("make_ok", "hash_after_make_ok", "hash_restored_ok", "state_restored")
            )
        for d in (1, 2):
            assert native_perft(rules, pos, d)["nodes"] == python_perft(
                compiled, fixture.state, d
            )


def test_deterministic_fuzz_legal_sets():
    from generic_chess.ai.benchmark.audit_suite import (
        build_session,
        smoke_ruleset_specs,
    )
    from generic_chess.ai.benchmark.position_mining import mine_suite
    from generic_chess.native.reference import python_legal_actions

    specs = smoke_ruleset_specs()
    positions = mine_suite(
        specs, playout_seed=9, max_games=2, max_plies=24, max_positions=3
    )
    for pos in positions:
        spec = next(s for s in specs if s.fixture_id == pos.ruleset_fixture_id)
        compiled, session = build_session(spec, pos.action_prefix)
        rules = compile_native_rules(compiled)
        pos_capsule = pack_native_position(compiled, rules, session.state)
        nat = set(
            canonical_action_set(
                [to_python_action(rules, a) for a in native_legal_actions(rules, pos_capsule)]
            )
        )
        py = set(
            canonical_action_set(python_legal_actions(session.state, compiled))
        )
        assert nat == py, pos.fixture_id
