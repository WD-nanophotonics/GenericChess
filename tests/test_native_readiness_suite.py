"""Suite manifest, geometry classification and position mining tests."""

import json

from generic_chess.ai.benchmark.audit_schema import (
    manifest_from_json,
    manifest_to_json,
    validate_manifest,
)
from generic_chess.ai.benchmark.audit_suite import (
    build_compiled,
    build_manifest,
    build_session,
    classify_ruleset,
    movement_buckets,
    promotion_buckets,
    drop_buckets,
    smoke_ruleset_specs,
    standard_ruleset_specs,
)
from generic_chess.ai.benchmark.position_mining import mine_suite, position_features
from generic_chess.core.attacks import is_in_check


def test_smoke_manifest_roundtrip_and_unique_ids():
    specs = smoke_ruleset_specs()
    positions = mine_suite(specs, playout_seed=1, max_games=2, max_plies=40, max_positions=3)
    manifest = build_manifest("smoke", specs, positions, commit="abc123")
    text = manifest_to_json(manifest)
    back = manifest_from_json(text)
    assert back.suite_version == "smoke-v1"
    ids = [r.fixture_id for r in back.rulesets]
    assert len(ids) == len(set(ids))
    pos_ids = [p.fixture_id for p in back.positions]
    assert len(pos_ids) == len(set(pos_ids))
    validate_manifest(json.loads(text))


def test_same_seed_produces_same_ruleset():
    spec = smoke_ruleset_specs()[0]
    a = build_compiled(spec)
    b = build_compiled(spec)
    assert a.ruleset_fingerprint == b.ruleset_fingerprint
    assert a.board_size == 4


def test_action_prefix_replays_deterministically():
    specs = smoke_ruleset_specs()
    positions = mine_suite(specs, playout_seed=1, max_games=2, max_plies=40, max_positions=3)
    spec = specs[0]
    for pos in positions:
        if pos.ruleset_fixture_id != spec.fixture_id:
            continue
        compiled_a, session_a = build_session(spec, pos.action_prefix)
        compiled_b, session_b = build_session(spec, pos.action_prefix)
        assert compiled_a.ruleset_fingerprint == compiled_b.ruleset_fingerprint
        from generic_chess.core.keys import position_key

        assert position_key(session_a.state.position, compiled_a) == position_key(
            session_b.state.position, compiled_b
        )


def test_expected_categories_match_rebuilt_position():
    specs = smoke_ruleset_specs()
    positions = mine_suite(specs, playout_seed=1, max_games=3, max_plies=60, max_positions=3)
    spec = specs[0]
    compiled = build_compiled(spec)
    for pos in positions:
        if pos.ruleset_fixture_id != spec.fixture_id:
            continue
        _, session = build_session(spec, pos.action_prefix)
        if "opening" in pos.expected_categories:
            assert session.state.ply_count == 0
        if "in_check" in pos.expected_categories:
            side = session.state.position.side_to_move
            assert is_in_check(session.state.position, side, compiled)


def test_standard_suite_has_geometry_buckets():
    specs = standard_ruleset_specs()
    assert len(specs) >= 24
    sizes = {s.board_size for s in specs}
    assert {4, 6, 8, 9, 10}.issubset(sizes)
    all_movement = set()
    all_promo = set()
    all_drop = set()
    for spec in specs[:6]:
        compiled = build_compiled(spec)
        all_movement.update(movement_buckets(compiled))
        all_promo.update(promotion_buckets(compiled))
        all_drop.update(drop_buckets(compiled))
    assert all_movement  # geometry-derived, not type-id based
    assert "no_promotion" in all_promo or "forced" in all_promo
    assert "no_drop" in all_drop or "drop_all" in all_drop


def test_mining_never_fabricates_positions():
    specs = smoke_ruleset_specs()
    positions = mine_suite(specs, playout_seed=1, max_games=1, max_plies=20, max_positions=3)
    for pos in positions:
        spec = next(s for s in specs if s.fixture_id == pos.ruleset_fixture_id)
        _, session = build_session(spec, pos.action_prefix)
        # Every prefix is a legal replay: the rebuilt session must match the
        # mined ply count (opening prefix is empty).
        assert session.state.ply_count == len(pos.action_prefix)
        features = position_features(session, build_compiled(spec))
        assert features["ply"] == session.state.ply_count
