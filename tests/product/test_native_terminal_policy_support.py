"""A legal-action kernel must not silently override no-move adjudication."""
import pytest
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.native.compiler import compile_native_semantic_rules,NativeUnsupportedRuleError
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.native.semantic import terminal_status,fixed_depth_search,probe_search,semantic_iterative_search,root_parallel_search
from generic_chess.session.session import GameSession
from native_test_helpers import requires_native

pytestmark=requires_native


@pytest.mark.parametrize('entry',[terminal_status,fixed_depth_search,probe_search,semantic_iterative_search,root_parallel_search])
def test_loss_terminal_policy_rejected_before_native_search_or_terminal(entry):
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))
    native=compile_native_semantic_rules(compiled)
    args=(native,None) if entry is terminal_status else (native,None,1)
    with pytest.raises(NativeUnsupportedRuleError,match='stalemate loss'):
        entry(*args)


def test_loss_policy_keeps_native_legality_but_rejects_persistent_search():
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))
    session=GameSession(compiled)
    provider=NativeSemanticLegalityProvider.try_create(compiled,strict=True)
    assert provider is not None
    assert {action for action,_ in provider(session.state.position,0)}==set(session.legal_actions())
    with pytest.raises(NativeUnsupportedRuleError,match='stalemate loss'):
        SemanticSearchEngine(compiled,provider.native_rules,tt_megabytes=0)


def test_draw_policy_keeps_existing_native_search_entry():
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    native=compile_native_semantic_rules(compiled)
    engine=SemanticSearchEngine(compiled,native,tt_megabytes=0)
    assert engine.ruleset_fingerprint==compiled.ruleset_fingerprint
