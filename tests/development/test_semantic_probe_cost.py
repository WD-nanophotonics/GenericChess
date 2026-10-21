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


@pytest.mark.parametrize('semantic', [False, True])
@pytest.mark.parametrize('variant', ['core', 'all'])
def test_saved_semantic_and_legacy_inputs_use_actual_requested_services(tmp_path, monkeypatch, semantic, variant):
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
    semantic_probe_cost.main()
    result = json.loads(output.read_bytes())
    assert not result['missing_slots']
    assert len(result['rows']) == 1
    assert result['worlds'][0]['roots'][0]['record'] == record
    assert result['worlds'][0]['rule'] == ruleset_to_dict(rules)
    row = result['rows'][0]
    assert row['decision']['completed_depth'] == 1
    assert row['decision']['runtime_depth_balanced']
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
