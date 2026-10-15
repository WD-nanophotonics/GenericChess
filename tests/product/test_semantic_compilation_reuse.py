"""Execution adapters retain the compiled product; changed rules rebuild it."""
from dataclasses import fields, replace

import pytest

from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.rules import compiler, ir as rules_ir
from generic_chess.rules.execution import ExecutableSemanticRuleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import castling_ruleset, uchifuzume_ruleset


@pytest.mark.parametrize("definition", [build_western_chess_ruleset(), castling_ruleset(), uchifuzume_ruleset()])
def test_adapter_preserves_full_compiled_product_and_replacement_rebuilds(definition):
    source = compiler.compile_semantic_ruleset(definition)
    adapted = ExecutableSemanticRuleset.from_compiled(source)
    for item in fields(rules_ir.CompiledSemanticRuleset):
        assert getattr(adapted, item.name) is getattr(source, item.name)
    direct = ExecutableSemanticRuleset(ir=source.ir, _legacy_compiled=source._legacy_compiled, support=source.support)
    a, b = GameSession(adapted), GameSession(direct)
    for _ in range(4):
        assert a.to_record() == b.to_record()
        assert tuple(a.legal_actions()) == tuple(b.legal_actions())
        if a.state.terminal_status.is_terminal:
            break
        action = sorted(a.legal_actions(), key=repr)[0]
        a.submit(action)
        b.submit(action)
    changed = replace(adapted, ir=replace(adapted.ir, patterns=()))
    assert changed._incoming_attack_paths is not source._incoming_attack_paths
    assert changed._incoming_attack_sources is not source._incoming_attack_sources
    assert not any(changed._incoming_attack_paths.values())
    assert not SemanticEngine(changed).is_square_attacked(a.state.position, 0, 0)


@pytest.mark.parametrize("mode", ["endpoints", "reference"])
def test_adapter_keeps_bounded_metadata_fallback(mode, monkeypatch):
    monkeypatch.setattr(rules_ir, "_incoming_attack_paths", lambda *args: None)
    if mode == "reference":
        monkeypatch.setattr(rules_ir, "_incoming_attack_endpoints", lambda *args: None)
    source = compiler.compile_semantic_ruleset(castling_ruleset())
    adapted = ExecutableSemanticRuleset.from_compiled(source)
    assert adapted._incoming_attack_paths is adapted._incoming_attack_sources is None
    assert adapted._incoming_attack_endpoints is source._incoming_attack_endpoints
    if mode == "reference":
        assert adapted._incoming_attack_endpoints is None
    a, b = GameSession(source), GameSession(adapted)
    assert a.to_record() == b.to_record()
    assert tuple(a.legal_actions()) == tuple(b.legal_actions())


def test_public_compile_still_validates_initial_position_and_builds_one_index(monkeypatch):
    calls = []
    original = rules_ir._incoming_attack_paths
    def counted(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)
    monkeypatch.setattr(rules_ir, "_incoming_attack_paths", counted)
    compiled = compiler.compile_ruleset_for_execution(castling_ruleset())
    assert len(calls) == 1
    assert compiled._incoming_attack_paths is not None
    def invalid(_):
        raise RuntimeError("semantic initial validation still required")
    monkeypatch.setattr(compiler, "_validate_semantic_initial_position", invalid)
    with pytest.raises(RuntimeError, match="semantic initial validation still required"):
        compiler.compile_ruleset_for_execution(castling_ruleset())
