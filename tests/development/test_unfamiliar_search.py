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


def test_repeat_signature_distinguishes_actionless_declaration_choices(monkeypatch):
    from types import SimpleNamespace
    from generic_chess.core.declarations import DeclarationAssessment
    from generic_chess.ai.decision import PlayerDecision
    import scripts.unfamiliar_search as unfamiliar_search

    class AlternatingDeclarationPlayer:
        calls = 0

        def __init__(self, *_args, **_kwargs):
            self.native_legality_provider = None

        def choose_action(self, _session, _limits):
            type(self).calls += 1
            return PlayerDecision(
                action=None,
                score=1_000_000,
                principal_variation=(),
                completed_depth=0,
                selective_depth=0,
                nodes=0,
                qnodes=0,
                elapsed_seconds=0.0,
                tt_probes=0,
                tt_hits=0,
                tt_cutoffs=0,
                beta_cutoffs=0,
                evaluation_profile_cache_hit=False,
                termination_reason="root_declaration_win",
                choice_kind="DECLARATION",
                declaration=DeclarationAssessment(
                    declaration_id=f"claim-{type(self).calls}", actor=0,
                    outcome="WIN", weighted_score=7,
                ),
            )

    monkeypatch.setattr(unfamiliar_search, "AlphaBetaPlayer", AlternatingDeclarationPlayer)
    monkeypatch.setattr(unfamiliar_search, "validate_pv", lambda *_args: None)
    case = {"searches": []}

    unfamiliar_search._compare_searches(
        session=SimpleNamespace(compiled=object()), evaluator=object(), cache=None, reference={},
        depth=1, case=case, save=lambda: None,
    )

    assert case["repeat_equal"] == {"python_plain": False, "public_bundle": False}


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


def test_semantic_only_movement_contributes_to_static_capability():
    from generic_chess.rules.western_chess import build_western_chess_ruleset
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.ai.evaluation.config import EvaluationConfig
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    scope = profile_input_scope(compiled)
    assert scope['semantic_moving_types_without_legacy_atoms'] == ['P']
    assert scope['semantic_geometry_profile_types'] == ['P']
    assert scope['semantic_patterns_used_for_static_capability']
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    assert profile.piece_profiles['P'].raw_capability_score > 0
    assert profile.board_value_by_type['P'] > 1


def test_existing_benchmark_ruleset_option_executes_semantics(tmp_path, capsys):
    from generic_chess.rules.serialization import serialize_ruleset
    from generic_chess.ai.cli.benchmark_alphabeta import main
    path = tmp_path / 'cannon.json'
    path.write_text(serialize_ruleset(cannon_ruleset()), encoding='utf-8')
    assert main(['--ruleset', str(path), '--nodes', '64', '--max-depth', '1',
                 '--repeat', '2', '--fresh-tt', '--no-disk']) == 0
    output = capsys.readouterr().out
    assert 'run 1:' in output and 'run 2:' in output


def test_generated_candidate_uses_legacy_execution_and_core_reference(tmp_path):
    from generic_chess.generation.config import GeneratorConfig
    from generic_chess.generation.generator import generate_game
    from generic_chess.ai.evaluation.config import EvaluationConfig
    generated = generate_game(GeneratorConfig(seed=21, board_size=4,
        setup_preset='bilateral_random', allow_hybrid=True))
    config = EvaluationConfig(dynamic_mobility_weight=0, anchor_escape_weight=0,
                              promotion_potential_weight=0)
    report = run_rule(tmp_path / 'candidate.json', ruleset_to_dict(generated.ruleset),
                      semantic_candidate=True, evaluation_config=config)
    assert report['compiled_class'] == 'CompiledRuleSet'
    assert report['candidate_scope']['ir_source'] == 'existing_legacy_lowering'
    assert report['reference']['complete'] and all(report['repeat_equal'].values())
    assert all(s['complete'] and s['reference_score_equal'] for s in report['searches'])


@pytest.mark.parametrize('authority', ['core', 'native'])
def test_supplied_semantic_rule_can_fix_attack_authority_separately(tmp_path, authority):
    if authority == 'native':
        from generic_chess.native import native_available
        if not native_available():
            pytest.skip('Native extension unavailable')
    report = run_rule(tmp_path / 'semantic-attacks.json', ruleset_to_dict(cannon_ruleset()),
                      semantic_candidate=True, attack_authority=authority)
    assert report['declaration']['attack_authority'] == authority
    assert report['candidate_scope']['candidate'] == 'semantic-opportunity-v4-inert-hand'
    assert report['candidate_scope']['hand_policy'] == 'zero_proved_inert'
    assert report['evaluator_version'] == report['candidate_scope']['candidate']
    assert report['reference']['complete']
    assert all(report['repeat_equal'].values())
    assert all(s['complete'] and s['reference_score_equal'] for s in report['searches'])


def test_explicit_candidate_does_not_build_unused_default_profile(tmp_path, monkeypatch):
    from generic_chess.ai.evaluation.cache import EvaluationProfileCache
    def unused(*args):
        raise AssertionError('explicit candidate built an unused default profile')
    monkeypatch.setattr(EvaluationProfileCache, 'get_or_build', unused)
    report = run_rule(tmp_path / 'candidate-only.json', ruleset_to_dict(cannon_ruleset()),
                      depth=1, semantic_candidate=True, attack_authority='core')
    assert report['complete'] and report['reference']['complete']
    assert report['evaluator_version'] == 'semantic-opportunity-v4-inert-hand'
    assert report['evaluator_version'] in report['declaration']['evaluator']


def test_rectangular_opt_in_candidate_crosses_supported_core_boundary(tmp_path):
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from tests.product.test_rectangular_search_override import rectangular_cannon
    config = EvaluationConfig(dynamic_mobility_weight=2, anchor_escape_weight=0,
                              promotion_potential_weight=0)
    report = run_rule(tmp_path / 'rectangle-candidate.json',
        ruleset_to_dict(rectangular_cannon(7, 5)), semantic_candidate=True,
        evaluation_config=config, attack_authority='core')
    assert report['complete'] and report['reference']['complete']
    assert report['evaluator_version'] == 'semantic-opportunity-v4-inert-hand'
    assert all(cell['complete'] and cell['reference_score_equal'] for cell in report['searches'])
    with pytest.raises(ValueError, match='disabled anchor escape and promotion'):
        run_rule(tmp_path / 'unsupported-dynamics.json',
            ruleset_to_dict(rectangular_cannon(7, 5)), semantic_candidate=True,
            attack_authority='core')
