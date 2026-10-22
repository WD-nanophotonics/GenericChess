"""Actual full-state consumer routing for the maintained cost probe."""
import json
import sys
from dataclasses import replace

import pytest
from conftest import make_ruleset, king_type, T
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import castling_ruleset
from scripts.research_record import write_record, record_value
from scripts import semantic_probe_cost


@pytest.mark.parametrize('staged', [False, True])
@pytest.mark.parametrize('pvs', [False, True])
@pytest.mark.parametrize('semantic', [False, True])
@pytest.mark.parametrize('variant', ['core', 'all'])
def test_saved_semantic_and_legacy_inputs_use_actual_requested_services(tmp_path, monkeypatch, semantic, variant, pvs, staged):
    rules = (castling_ruleset() if semantic else make_ruleset(
        4, [king_type(), T('A', LeapAtom((1, 0)))],
        lines=['...k', '....', '....', 'KA..']))
    compiled = (compile_ruleset_for_execution(rules) if semantic
                else compile_legacy_ruleset_for_semantic_execution(rules))
    record = record_value(GameSession(compiled).to_record())
    source, output = tmp_path / 'input.json', tmp_path / 'output.json'
    write_record(source, {'worlds': [{'seed': 1, 'rule': ruleset_to_dict(rules),
        'roots': [{'target': 0, 'record': record}]}]})
    monkeypatch.setattr(sys, 'argv', ['semantic_probe_cost', '--input', str(source),
        '--output', str(output), '--seed-count', '1', '--prefixes', '0',
        '--variants', variant, '--depth', '1', '--qdepth', '0', '--nodes', '4096',
        '--seconds', '2', '--total-seconds', '10'])
    if pvs:
        sys.argv.append('--pvs')
    if staged:
        sys.argv.append('--staged-move-picker')
    semantic_probe_cost.main()
    result = json.loads(output.read_bytes())
    assert result['protocol']['pvs'] is pvs
    assert result['protocol']['staged_move_picker'] is staged
    assert not result['missing_slots']
    assert len(result['rows']) == 1
    assert result['worlds'][0]['roots'][0]['record'] == record
    assert result['worlds'][0]['rule'] == ruleset_to_dict(rules)
    row = result['rows'][0]
    assert row['decision']['completed_depth'] == 1
    assert row['decision']['runtime_depth_balanced']
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.search import reference_minimax
    player = AlphaBetaPlayer(compiled, use_disk_cache=False)
    score, _ = reference_minimax(GameSession(compiled).state, 1, player._evaluator, compiled)
    assert row['decision']['score'] == score
    if staged and row['decision']['result_source'] == 'main_iteration':
        assert row['decision']['move_picker_generated'] > 0
        assert row['decision']['move_picker_yielded'] > 0
    if pvs and row['decision']['result_source'] == 'main_iteration':
        assert row['decision']['pvs_null_window_searches'] > 0
    if variant == 'core':
        assert not row['provider_available']
        assert row['decision']['native_legality_calls'] == 0
        assert not row['check_metrics'] and not row['availability_metrics']
    elif row['provider_available']:
        assert row['decision']['native_legality_calls'] > 0


def test_invalid_semantic_input_is_retained_and_never_lowered_as_legacy(tmp_path, monkeypatch):
    rules = castling_ruleset()
    action = rules.semantic_actions[0]
    invalid = replace(rules, semantic_actions=(replace(action,
        effects=action.effects[:-1] + (replace(action.effects[-1], slot_name='missing'),)),))
    source, output = tmp_path / 'input.json', tmp_path / 'output.json'
    write_record(source, {'worlds': [{'seed': 1, 'rule': ruleset_to_dict(invalid), 'roots': []}]})
    monkeypatch.setattr(sys, 'argv', ['semantic_probe_cost', '--input', str(source),
        '--output', str(output), '--seed-count', '1', '--prefixes', '0', '--variants', 'core'])
    semantic_probe_cost.main()
    result = json.loads(output.read_bytes())
    assert not result['rows']
    assert len(result['missing_slots']) == 1
    assert 'missing' in result['worlds'][0]['setup_failure']


@pytest.mark.parametrize('pvs', [False, True])
def test_explicit_unit_control_runs_rectangular_complete_semantic_input(tmp_path, monkeypatch, pvs):
    from rule_semantics_ir_fixtures import cannon_ruleset
    from generic_chess.core.pieces import Piece
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.search import reference_minimax

    rows = [[None] * 7 for _ in range(5)]
    rows[0][0], rows[-1][-1] = Piece(0, 'K', 'K'), Piece(1, 'K', 'K')
    rows[1][0], rows[1][-1] = Piece(0, 'C', 'C'), Piece(1, 'C', 'C')
    rows[1][3] = Piece(0, 'C', 'C')
    rules = replace(cannon_ruleset(), board_size=None, board_width=7,
        board_height=5, initial_position=tuple(map(tuple, rows)),
        drop_allowed={'C': ((False,) * 35,) * 2})
    compiled = compile_ruleset_for_execution(rules)
    assert not hasattr(compiled, 'piece_types')
    session = GameSession(compiled)
    session.submit(session.legal_actions()[0])
    record = record_value(session.to_record())
    source, output = tmp_path / 'rect.json', tmp_path / 'unit.json'
    write_record(source, {'worlds': [{'seed': 0, 'rule': ruleset_to_dict(rules),
        'roots': [{'target': 1, 'record': record}]}]})
    argv = ['semantic_probe_cost', '--input', str(source), '--output', str(output),
        '--seed-count', '1', '--prefixes', '1', '--variants', 'core',
        '--evaluation-backend', 'unit', '--depth', '2', '--qdepth', '0',
        '--nodes', '10000', '--seconds', '5', '--total-seconds', '15']
    if pvs:
        argv.append('--pvs')
    monkeypatch.setattr(sys, 'argv', argv)
    semantic_probe_cost.main()
    result = json.loads(output.read_bytes())
    assert result['worlds'][0]['roots'][0]['record'] == record
    assert not result['missing_slots']
    decision = result['rows'][0]['decision']
    assert decision['completed_depth'] == 2
    # Independent counting control, all declared metadata types, CURRENT board,
    # BASE hand. No legacy cache/profile analysis can be required by this route.
    class Unit:
        def evaluate(self, state):
            pos = state.position
            board = sum((1 if x.owner == pos.side_to_move else -1) * 1000
                for x in pos.board if x is not None
                and not compiled.support.type_metadata[x.current_type_id].is_anchor)
            hand = sum((1 if o == pos.side_to_move else -1) * 900 * n
                for o, stock in enumerate(pos.hands) for t, n in stock.counts
                if not compiled.support.type_metadata[t].is_anchor)
            return board + hand
    expected, _ = reference_minimax(session.state, 2, Unit(), compiled)
    assert decision['score'] == expected
    assert decision['native_legality_calls'] == 0
    assert decision['runtime_depth_balanced']
    for saved in decision['principal_variation']:
        action = next(a for a in session.legal_actions() if record_value(a) == saved)
        session.submit(action)
    assert GameSession.replay(compiled, session.to_record()).state == session.state


@pytest.mark.parametrize('delta', [50, 1000])
def test_aspiration_consumer_uses_real_depth_four_and_core_value(tmp_path, monkeypatch, delta):
    from generic_chess.ai.alphabeta import search
    from generic_chess.ai.alphabeta.search import reference_minimax
    rules = make_ruleset(4, [king_type(), T('A', LeapAtom((1, 0)))],
                         lines=['...k', '....', '....', 'KA..'])
    compiled = compile_legacy_ruleset_for_semantic_execution(rules)
    session = GameSession(compiled)
    source, output = tmp_path / 'input.json', tmp_path / 'asp.json'
    write_record(source, {'worlds': [{'seed': 1, 'rule': ruleset_to_dict(rules),
        'roots': [{'target': 0, 'record': record_value(session.to_record())}]}]})
    actual = []
    original = search._aspiration_iteration
    def observed(state, depth, previous, context):
        actual.append((depth, context.tuning.aspiration_delta))
        return original(state, depth, previous, context)
    monkeypatch.setattr(search, '_aspiration_iteration', observed)
    monkeypatch.setattr(sys, 'argv', ['probe', '--input', str(source), '--output', str(output),
        '--seed-count', '1', '--prefixes', '0', '--variants', 'core',
        '--evaluation-backend', 'unit', '--aspiration-delta', str(delta),
        '--depth', '4', '--qdepth', '0', '--nodes', '100000', '--seconds', '5',
        '--total-seconds', '10'])
    semantic_probe_cost.main()
    result = json.loads(output.read_bytes())
    assert actual == [(4, delta)]
    assert result['rows'][0]['decision']['completed_depth'] == 4
    expected, _ = reference_minimax(session.state, 4,
        semantic_probe_cost.unit_evaluator(compiled), compiled)
    assert result['rows'][0]['decision']['score'] == expected


@pytest.mark.parametrize('failure_phase', ['player_setup', 'query'])
def test_cost_probe_preserves_prepared_input_and_real_failure(tmp_path, monkeypatch, failure_phase):
    from rule_semantics_ir_fixtures import cannon_ruleset
    from generic_chess.core.pieces import Piece
    from generic_chess.ai.evaluation.evaluator import Evaluator
    rows = [[None] * 7 for _ in range(5)]
    rows[0][0], rows[-1][-1] = Piece(0, 'K', 'K'), Piece(1, 'K', 'K')
    rows[1][0], rows[1][-1] = Piece(0, 'C', 'C'), Piece(1, 'C', 'C')
    rules = replace(cannon_ruleset(), board_size=None, board_width=7,
        board_height=5, initial_position=tuple(map(tuple, rows)),
        drop_allowed={'C': ((False,) * 35,) * 2})
    compiled = compile_ruleset_for_execution(rules)
    record = record_value(GameSession(compiled).to_record())
    source, output = tmp_path / 'rect.json', tmp_path / 'failure.json'
    write_record(source, {'worlds': [{'seed': 0, 'rule': ruleset_to_dict(rules),
        'roots': [{'target': 0, 'record': record}]}]})
    argv = ['probe', '--input', str(source), '--output', str(output),
        '--seed-count', '1', '--prefixes', '0', '--variants', 'core',
        '--depth', '2', '--qdepth', '0', '--seconds', '2', '--total-seconds', '10']
    expected = ValueError
    if failure_phase == 'query':
        expected = RuntimeError
        argv.extend(['--evaluation-backend', 'unit'])
        def fail_after_input_preparation(self, state):
            raise RuntimeError('injected evaluator failure after input preparation')
        monkeypatch.setattr(Evaluator, 'evaluate', fail_after_input_preparation)
    monkeypatch.setattr(sys, 'argv', argv)
    with pytest.raises(expected):
        semantic_probe_cost.main()
    result = json.loads(output.read_bytes())
    assert result['worlds'][0]['rule'] == ruleset_to_dict(rules)
    assert result['worlds'][0]['roots'][0]['record'] == record
    assert result['rows'] == []
    assert len(result['failures']) == 1
    failure = result['failures'][0]
    assert failure['phase'] == failure_phase
    assert failure['error_type'] == expected.__name__
    assert failure['seed'] == 0 and failure['prefix'] == 0
    assert result['missing_slots'] == [[0, 0, 0, 'core']]


def test_unit_uses_metadata_anchor_future_current_and_real_base_hand_history():
    from conftest import sq
    from generic_chess.rules.ir import CompiledSemanticRuleset
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.search import reference_minimax
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    from generic_chess.core.actions import SemanticDropMove
    anchor = replace(king_type(), type_id='X', name='anchor')
    actor = T('K', LeapAtom((1, 0)), is_promotable=True, targets=('Z',))
    future = T('Z', LeapAtom((0, 1)))
    rules = make_ruleset(4, [anchor, actor, future],
        lines=['...x', '....', '....', 'XKk.'],
        promotion={'K': ([(sq(1, 0), sq(2, 0))], [])})
    c = compile_legacy_ruleset_for_semantic_execution(rules)
    compiled = CompiledSemanticRuleset(ir=c.ir, support=c.support)
    assert not hasattr(compiled, 'piece_types')
    evaluator = semantic_probe_cost.unit_evaluator(compiled)
    assert evaluator.type_value('X') == 0
    assert evaluator.type_value('K') == evaluator.type_value('Z') == 1000
    session = GameSession(compiled)
    assert evaluator.evaluate(session.state) == 0
    promotion = next(a for a in session.legal_actions()
        if getattr(a, 'promotion_target_id', None) == 'Z')
    session.submit(promotion)
    assert session.state.position.hands[0].count('K') == 1
    assert evaluator.evaluate(session.state) == -1900
    session.submit(session.legal_actions()[0])
    assert evaluator.evaluate(session.state) == 1900
    drop = next(a for a in session.legal_actions() if isinstance(a, SemanticDropMove))
    session.submit(drop)
    assert session.state.position.hands[0].count('K') == 0
    assert evaluator.evaluate(session.state) == -2000
    before = session.state, session.to_record(), session._search_witnesses
    assert GameSession.replay(compiled, session.to_record()).state == session.state
    expected, _ = reference_minimax(session.state, 2, evaluator, compiled)
    decision = AlphaBetaPlayer(compiled, evaluator_override=evaluator,
        use_disk_cache=False, use_native_semantic_legality=False,
        tuning=SearchTuning(use_pvs=True, use_staged_move_picker=True)).choose_action(
            session, SearchLimits(max_depth=2, max_nodes=10000, max_time_seconds=2,
                quiescence_max_depth=0, quiescence_hard_max_depth=0))
    assert decision.completed_depth == 2 and decision.score == expected
    assert before == (session.state, session.to_record(), session._search_witnesses)
