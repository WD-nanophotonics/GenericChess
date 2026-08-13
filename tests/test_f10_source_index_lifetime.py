from scripts.audit_f4_runtime_cost import corpus_specs, make_session
from generic_chess.core import semantic_executor as semantic_executor_module
from generic_chess.core.semantic_executor import SemanticEngine, semantic_engine_for


def test_f10_operation_local_index_is_shared_across_board_patterns(monkeypatch):
    spec = next(item for item in corpus_specs() if item["id"] == "semantic_prefix_0")
    session = make_session(spec)
    engine = semantic_engine_for(session.compiled)
    position = session.state.position
    original = SemanticEngine._iter_board_candidates
    seen = []

    def wrapped(self, pattern, position, checkpoint=None, sources_by_owner_type=None):
        if sources_by_owner_type is not None:
            seen.append(id(sources_by_owner_type))
        yield from original(
            self,
            pattern,
            position,
            checkpoint=checkpoint,
            sources_by_owner_type=sources_by_owner_type,
        )

    monkeypatch.setattr(SemanticEngine, "_iter_board_candidates", wrapped)
    tuple(engine.iter_legal_action_bindings(position))
    assert len(seen) > 1
    assert len(set(seen)) == 1


def test_f10_default_source_index_fallback_remains_self_contained():
    spec = next(item for item in corpus_specs() if item["id"] == "semantic_prefix_0")
    session = make_session(spec)
    engine = semantic_engine_for(session.compiled)
    position = session.state.position
    assert tuple(engine.iter_legal_actions(position))
    assert semantic_executor_module._sources_by_owner_type(position)
