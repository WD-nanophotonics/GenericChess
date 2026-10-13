"""Large-metadata fallback keeps complete guards, ownership and reference escape."""
from dataclasses import replace
import pickle
import pytest
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.errors import RuleSetMismatchError
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules import ir as rules_ir
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import (
    cannon_ruleset, castling_ruleset, en_passant_ruleset, nifu_ruleset,
    uchifuzume_ruleset, weird_rulesets,
)

DEFINITIONS = [build_western_chess_ruleset(), build_standard_shogi_ruleset(),
    cannon_ruleset(), castling_ruleset(), en_passant_ruleset(), nifu_ruleset(),
    uchifuzume_ruleset(), *weird_rulesets()]


@pytest.mark.parametrize("definition", DEFINITIONS)
def test_endpoint_fallback_matches_reference_frontier_and_bulk_through_play(definition, monkeypatch):
    compiled = compile_ruleset_for_execution(definition)
    assert compiled._incoming_attack_endpoints is None
    monkeypatch.setattr(rules_ir, "_incoming_attack_paths", lambda *args: None)
    fallback = replace(compiled)
    assert fallback._incoming_attack_endpoints is not None
    reference = replace(fallback)
    object.__setattr__(reference, "_incoming_attack_endpoints", None)
    fast, slow = SemanticEngine(fallback), SemanticEngine(reference)
    session = GameSession(compiled)
    for ply in range(4):
        position = session.state.position
        for owner in (0, 1):
            bulk = slow.attacked_squares(position, owner)
            for square in range(-1, len(position.board) + 1):
                assert fast.is_square_attacked(position, square, owner) == (
                    slow.is_square_attacked(position, square, owner))
                assert fast.is_square_attacked(position, square, owner) == (square in bulk)
        assert fast.legal_actions(position) == slow.legal_actions(position)
        assert fallback.ir.serialized() == compiled.ir.serialized()
        if session.state.terminal_status.is_terminal or ply == 3:
            break
        session.submit(sorted(session.legal_actions(), key=repr)[0])


def test_endpoint_schedule_ownership_pickle_rebuild_and_reference_escape(monkeypatch):
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    monkeypatch.setattr(rules_ir, "_incoming_attack_paths", lambda *args: None)
    fallback = replace(compiled)
    schedule = fallback._incoming_attack_endpoints
    assert SemanticEngine(fallback).semantic._incoming_attack_endpoints is schedule
    rebuilt = replace(fallback)
    assert rebuilt._incoming_attack_endpoints == schedule
    assert rebuilt._incoming_attack_endpoints is not schedule
    object.__setattr__(rebuilt, "_incoming_attack_endpoints", pickle.loads(pickle.dumps(schedule)))
    changed = replace(fallback, ir=replace(fallback.ir, patterns=()))
    assert changed._incoming_attack_endpoints == {}
    position = GameSession(compiled).state.position
    assert not SemanticEngine(changed).is_square_attacked(position, 0, 0)
    assert rules_ir._incoming_attack_endpoints(compiled.ir, 64, max_paths=0) is None
    monkeypatch.setattr(rules_ir, "_incoming_attack_endpoints", lambda *args: None)
    escaped = replace(compiled)
    assert escaped._incoming_attack_paths is escaped._incoming_attack_endpoints is None
    for owner in (0, 1):
        for square in range(64):
            assert SemanticEngine(escaped).is_square_attacked(position, square, owner) == (
                SemanticEngine(rebuilt).is_square_attacked(position, square, owner))


def test_endpoint_stop_match_and_guard_error_propagation(monkeypatch):
    compiled = compile_ruleset_for_execution(cannon_ruleset())
    monkeypatch.setattr(rules_ir, "_incoming_attack_paths", lambda *args: None)
    fallback = replace(compiled)
    engine = SemanticEngine(fallback)
    position = GameSession(compiled).state.position
    for target in (-1, 0, len(position.board)):
        def stopped():
            raise InterruptedError("endpoint stop")
        with pytest.raises(InterruptedError, match="endpoint stop"):
            engine.is_square_attacked(position, target, 0, stopped)
    with pytest.raises(RuleSetMismatchError):
        engine.is_square_attacked(replace(position, ruleset_fingerprint="different"), 0, 0)
    calls = 0
    def first_source():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise InterruptedError("source stop")
    key = next(key for key, sources in fallback._incoming_attack_endpoints.items() if sources)
    with pytest.raises(InterruptedError, match="source stop"):
        engine.is_square_attacked(position, key[1], int(key[0]), first_source)
    assert calls == 2
    # A required binding/guard failure must not be turned into a negative attack.
    def broken_binding(*args, **kwargs):
        raise RuntimeError("required binding")
    monkeypatch.setattr(SemanticEngine, "_make_binding", broken_binding)
    occupied = [(owner, target) for (owner, target), sources in
        fallback._incoming_attack_endpoints.items() if any(
            (piece := position.board[source]) is not None and str(piece.owner) == owner
            and piece.current_type_id in typed for source, typed in sources.items())]
    assert occupied
    owner, target = occupied[0]
    with pytest.raises(RuntimeError, match="required binding"):
        engine.is_square_attacked(position, target, int(owner))


def test_endpoint_builder_honors_limit_without_copying_ray_prefixes():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    pattern = next(p for p in compiled.ir.patterns if p.target.kind == "target_enemy"
        and any(compiled.ir.geometry[g].kind == "ray" for g in p.geometry_ids))
    gid = next(g for g in pattern.geometry_ids if compiled.ir.geometry[g].kind == "ray")
    class BoundedPath:
        def __len__(self):
            return 1000000
        def __getitem__(self, index):
            assert not isinstance(index, slice), "compile copied a ray prefix"
            assert index < 4
            return index + 1
    geometry = replace(compiled.ir.geometry[gid], atom_source=None, min_steps=1,
        paths={"0": {0: BoundedPath()}})
    ir = replace(compiled.ir, patterns=(replace(pattern, geometry_ids=(gid,),
        type_ids=(pattern.type_ids[0],)),), geometry={gid: geometry})
    assert rules_ir._incoming_attack_endpoints(ir, 64, max_paths=4) is None
