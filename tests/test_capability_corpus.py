from dataclasses import replace
import json
from pathlib import Path

import pytest

from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for, iter_semantic_public_actions
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_post_capture_scope import state_evidence, capture_key
from scripts.audit_secured_exchange_common_context import Budget
from scripts.generate_capability_corpus import generate, own_counts


@pytest.fixture(scope='module')
def result():
    return generate()


def test_exact_frozen_partial_corpus_is_preserved_without_qualification(result):
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/capability_corpus_20261004.json').read_text())
    for key in ('protocol_sha256', 'program_sha256', 'complete', 'scope', 'games', 'failure', 'materialized_capture_transitions'):
        assert recorded[key] == result[key]
    assert not result['complete'] and result['failure'] == 'shogi: incomplete R deployment stratum'
    assert result['materialized_capture_transitions'] == 35
    assert len(result['games']['chess']['deployment']) == 5
    assert sum(d['selected'] is not None for d in result['games']['shogi']['deployment']) == 5
    failed = result['games']['shogi']['deployment'][-1]
    assert failed['victim_type'] == 'R' and failed['selected'] is None and failed['proposals'] == 128
    assert failed['rejected'] == {'Q:dead_nonpawn_placement': 109, 'Q:actual_anchor_check': 17, 'no_ongoing_type_capture': 2}


def test_proposal_accounting_and_reference_deployment_separation(result):
    for row in result['games'].values():
        assert len(row['reference']) == 4
        assert row['reference_proposals'] == len(row['reference']) + sum(row['reference_rejected'].values())
        refs = {json.dumps(r['physical_board']) for r in row['reference']}
        for d in row['deployment']:
            assert d['proposals'] == sum(d['rejected'].values()) + int(d['selected'] is not None)
            if d['selected']:
                assert json.dumps(d['selected']['parent']['physical_board']) not in refs


def test_real_children_inventory_and_complete_capture_choices_match_public_api(result):
    for game, row in result['games'].items():
        compiled = standard_engine()[0] if game == 'chess' else compile_ruleset_for_execution(build_standard_shogi_ruleset())
        template = position_from_fen('8/8/8/8/8/8/8/8 b - - 0 1', compiled) if game == 'chess' else initial_state(compiled).position
        for d in row['deployment']:
            selected = d['selected']
            if selected is None:
                continue
            position = replace(template, board=tuple(None if p is None else Piece(*p) for p in selected['parent']['physical_board']), side_to_move=1)
            parent = synthetic_state(compiled, position)
            assert state_evidence(parent, compiled) == selected['parent']
            choices = []
            for action in iter_semantic_public_actions(semantic_engine_for(compiled), position):
                target = getattr(action, 'to_square', None)
                victim = None if target is None else position.board[target.rank * compiled.board_size + target.file]
                if victim and victim.owner == 0 and victim.current_type_id == d['victim_type']:
                    child = apply_action(parent, action, compiled)
                    if not child.terminal_status.is_terminal:
                        choices.append(capture_key(action_to_dict(action)))
            assert len(set(choices)) == len(choices) == selected['capture_candidates']
            assert capture_key(selected['selected_action']) in choices
            child = apply_action(parent, action_from_dict(selected['selected_action']), compiled)
            assert state_evidence(child, compiled) == selected['child']
            expected = row['initial_counts'].copy(); expected[d['victim_type']] -= 1
            assert dict(own_counts(compiled, child.position)) == {k: v for k, v in expected.items() if v}


def test_unlabelled_corpus_contains_no_task_score_or_candidate_vector(result):
    forbidden = {'actor_success_count', 'actors', 'scores', 'coefficients', 'success'}
    def inspect(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            for item in value.values():
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
    inspect(result)


def test_stricter_failure_does_not_trigger_extra_roots_or_budgets():
    result = generate(reference_limit=1)
    assert not result['complete'] and len(result['games']) == 1
    assert result['games']['chess']['deployment'] == []
    with pytest.raises(ValueError, match='at most 128'):
        generate(stratum_limit=129)
    with pytest.raises(RuntimeError, match='transition cap'):
        generate(Budget(seconds=25, transitions_limit=1))
