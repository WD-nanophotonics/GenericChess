"""Integration check for the small reusable generated-search entry."""
import pytest
from scripts.unfamiliar_search import CountedEvaluator, ReferenceLimit, run, run_rule, profile_input_scope
from generic_chess.rules.schema import ruleset_to_dict
from rule_semantics_ir_fixtures import cannon_ruleset


def test_generated_search_preserves_all_cells_and_actual_parity(tmp_path):
    output = tmp_path / 'result.json'
    report = run(output)
    assert report['complete'] and len(report['cases']) == 4
    assert sum(len(c['searches']) for c in report['cases']) == 16
    assert all(c['profile_input_scope']['static_capability_source'] == 'legacy_movement_atoms'
               for c in report['cases'])
    assert all(c['reference']['complete'] for c in report['cases'])
    assert all(all(c['repeat_equal'].values()) for c in report['cases'])
    assert all(s['complete'] and s['reference_score_equal']
               for c in report['cases'] for s in c['searches'])
    with pytest.raises(FileExistsError):
        run(output)


def test_reference_fuse_cannot_supply_a_partial_score():
    class Leaf:
        def evaluate(self, state):
            return 7
    counted = CountedEvaluator(Leaf(), evaluations=1)
    assert counted.evaluate(None) == 7
    with pytest.raises(ReferenceLimit):
        counted.evaluate(None)


def test_supplied_semantic_rule_uses_product_boundary_and_core_reference(tmp_path):
    # Actual non-legacy capture mechanics, not an anchor-only no-op fixture.
    output = tmp_path / 'semantic.json'
    report = run_rule(output, ruleset_to_dict(cannon_ruleset()), depth=1)
    assert report['compiled_class'] == 'ExecutableSemanticRuleset'
    assert not report['profile_input_scope']['semantic_patterns_used_for_static_capability']
    assert report['reference']['complete']
    assert all(report['repeat_equal'].values())
    assert len(report['searches']) == 4
    assert all(s['complete'] and s['reference_score_equal'] for s in report['searches'])
    with pytest.raises(FileExistsError):
        run_rule(output, ruleset_to_dict(cannon_ruleset()), depth=1)


def test_semantic_only_movement_is_not_claimed_as_static_capability():
    from generic_chess.rules.western_chess import build_western_chess_ruleset
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.ai.evaluation.config import EvaluationConfig
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    scope = profile_input_scope(compiled)
    assert scope['semantic_moving_types_without_atoms'] == ['P']
    assert build_ruleset_profile(compiled, EvaluationConfig()).piece_profiles['P'].raw_capability_score == 0


def test_existing_benchmark_ruleset_option_executes_semantics(tmp_path, capsys):
    from generic_chess.rules.serialization import serialize_ruleset
    from generic_chess.ai.cli.benchmark_alphabeta import main
    path = tmp_path / 'cannon.json'
    path.write_text(serialize_ruleset(cannon_ruleset()), encoding='utf-8')
    assert main(['--ruleset', str(path), '--nodes', '64', '--max-depth', '1',
                 '--repeat', '2', '--fresh-tt', '--no-disk']) == 0
    output = capsys.readouterr().out
    assert 'run 1:' in output and 'run 2:' in output
