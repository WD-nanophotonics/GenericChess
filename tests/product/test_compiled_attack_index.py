"""Derived incoming geometry ownership, serialization and exact fallback."""
from dataclasses import replace
import pickle

import pytest

from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.errors import RuleSetMismatchError
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.ir import _incoming_attack_paths, geometry_paths_to
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


def test_repeated_engines_share_compile_owned_data_and_index_pickle_preserves_execution():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    index = compiled._incoming_attack_paths
    assert index is not None
    first, second = SemanticEngine(compiled), SemanticEngine(compiled)
    assert first.semantic._incoming_attack_paths is second.semantic._incoming_attack_paths is index
    # The existing compiled inspection/support handles can contain mappingproxy;
    # whole-object pickle is not promised. This derived mapping is pickleable.
    restored = replace(compiled)
    object.__setattr__(restored, '_incoming_attack_paths', pickle.loads(pickle.dumps(index)))
    assert restored.ir.serialized() == compiled.ir.serialized()
    assert restored.ruleset_fingerprint == compiled.ruleset_fingerprint
    position = GameSession(compiled).state.position
    expected = tuple(first.is_square_attacked(position, square, owner)
        for owner in (0, 1) for square in range(len(position.board)))
    observed = tuple(SemanticEngine(restored).is_square_attacked(position, square, owner)
        for owner in (0, 1) for square in range(len(position.board)))
    assert observed == expected


def test_replacing_ir_rebuilds_derived_paths_instead_of_reusing_stale_index():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    changed = replace(compiled, ir=replace(compiled.ir, patterns=()))
    assert changed._incoming_attack_paths is not compiled._incoming_attack_paths
    assert not any(changed._incoming_attack_paths.values())
    position = GameSession(compiled).state.position
    assert not SemanticEngine(changed).is_square_attacked(position, 0, 0)


def test_bounded_metadata_fallback_keeps_full_attack_semantics():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    assert _incoming_attack_paths(compiled.ir, compiled.board_shape.area, max_paths=0) is None
    session = GameSession(compiled)
    for _ in range(3):
        position = session.state.position
        indexed = SemanticEngine(compiled)
        fallback = replace(compiled)
        object.__setattr__(fallback, '_incoming_attack_paths', None)
        reference = SemanticEngine(fallback)
        for owner in (0, 1):
            for square in range(len(position.board)):
                assert indexed.is_square_attacked(position, square, owner) == reference.is_square_attacked(position, square, owner)
        session.submit(sorted(session.legal_actions(), key=str)[0])


def test_indexed_empty_query_still_polls_and_preserves_match_check():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    engine = SemanticEngine(compiled)
    position = GameSession(compiled).state.position
    assert not engine.is_square_attacked(position, -1, 0)
    assert not engine.is_square_attacked(position, 64, 0)
    assert not engine.is_square_attacked(position, 0, 99)
    def stopped():
        raise InterruptedError('stopped inside geometry')
    with pytest.raises(InterruptedError, match='stopped inside geometry'):
        engine.is_square_attacked(position, -1, 0, stopped)
    with pytest.raises(RuleSetMismatchError, match='fingerprint'):
        engine.is_square_attacked(replace(position, ruleset_fingerprint='different'), 0, 0)


def test_index_contains_complete_old_static_sequence_including_shared_geometry():
    from rule_semantics_ir_fixtures import weird_rulesets

    for rules in weird_rulesets():
        compiled = compile_ruleset_for_execution(rules)
        for owner in (0, 1):
            for target in range(compiled.board_shape.area):
                expected = []
                for pattern in compiled.ir.patterns:
                    if pattern.target.kind != 'target_enemy':
                        continue
                    for tid in pattern.type_ids:
                        for source in range(compiled.board_shape.area):
                            for gid in pattern.geometry_ids:
                                geometry = compiled.ir.geometry.get(gid)
                                if geometry is None or geometry.kind == 'drop':
                                    continue
                                if geometry.atom_source is not None and geometry.atom_source[0] != tid:
                                    continue
                                for path in geometry_paths_to(geometry, str(owner), source, target):
                                    expected.append((pattern, tid, source, gid, path))
                assert compiled._incoming_attack_paths[(str(owner), target)] == tuple(expected)


def test_metadata_cap_stops_before_constructing_remaining_ray_prefixes():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    pattern = next(p for p in compiled.ir.patterns if p.target.kind == 'target_enemy'
                   and any(compiled.ir.geometry[g].kind == 'ray' for g in p.geometry_ids))
    gid = next(g for g in pattern.geometry_ids if compiled.ir.geometry[g].kind == 'ray')

    class BoundedPath:
        def __len__(self):
            return 1000000

        def __getitem__(self, index):
            if isinstance(index, slice):
                assert index.stop <= 3
                return tuple(range(index.stop))
            assert index <= 3
            return index + 1

    geometry = replace(compiled.ir.geometry[gid], atom_source=None, min_steps=1,
                       paths={'0': {0: BoundedPath()}})
    ir = replace(compiled.ir, patterns=(replace(pattern, geometry_ids=(gid,),
                                               type_ids=(pattern.type_ids[0],)),),
                 geometry={gid: geometry})
    # A long precompiled path may be supplied to this helper. Do not materialize
    # geometry_candidates' whole endpoint/prefix tuple before honoring the cap.
    assert _incoming_attack_paths(ir, compiled.board_shape.area, max_paths=4) is None
