"""Integration check for the small reusable generated-search entry."""
import pytest
from scripts.unfamiliar_search import CountedEvaluator, ReferenceLimit, run, run_rule
from generic_chess.rules.schema import ruleset_to_dict
from rule_semantics_ir_fixtures import cannon_ruleset


def test_generated_search_preserves_all_cells_and_actual_parity(tmp_path):
    output = tmp_path / 'result.json'
    report = run(output)
    assert report['complete'] and len(report['cases']) == 4
    assert sum(len(c['searches']) for c in report['cases']) == 16
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
    assert report['reference']['complete']
    assert all(report['repeat_equal'].values())
    assert len(report['searches']) == 4
    assert all(s['complete'] and s['reference_score_equal'] for s in report['searches'])
    with pytest.raises(FileExistsError):
        run_rule(output, ruleset_to_dict(cannon_ruleset()), depth=1)
