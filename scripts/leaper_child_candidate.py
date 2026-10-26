"""Research-only selected Semantic child constructor; no product activation.

The baseline is the untouched product SearchPathRuntime.  Only the candidate
subclass's selected transition call is derived; no engine method is replaced.
"""
from __future__ import annotations

import ast
import copy
from contextlib import contextmanager
from dataclasses import fields
import importlib
import inspect
import hashlib
import textwrap
import time

from generic_chess.core import search_runtime as runtime
from generic_chess.core.position import Hands, Position
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import SemanticAction, _ActionBinding


EMPTY_HANDS = (Hands(), Hands())
BASE_RUNTIME = runtime.SearchPathRuntime
_COUNTERS = {'runtime_count': 0, 'attempts': 0, 'successes': 0,
             'fallbacks': 0, 'certification_seconds': 0.0}


def selected_child(owner, engine, parent, action, binding, checkpoint=None):
    """Explicit unsupported fallback BEFORE effects; exceptions never retried."""
    pair = (action.pattern_id, action.geometry_id) if type(action) is SemanticAction else None
    patterns = owner.child_patterns
    source, target = getattr(action, 'source', None), getattr(action, 'target', None)
    supported = (
        patterns is not None and type(engine) is type(owner.child_engine)
        and engine.semantic is owner.child_engine.semantic
        and engine.ir is owner.child_engine.ir and engine.support is owner.child_engine.support
        and type(parent) is Position and type(action) is SemanticAction
        and type(binding) is _ActionBinding and pair in patterns
        and binding.pattern is owner.child_pattern_objects.get(action.pattern_id)
        and binding.geometry_id == action.geometry_id
        and binding.source == source and binding.target == target
        and binding.promotion_target_id is None and action.promotion_target_id is None
        and type(source) is int and type(target) is int and source != target
        and 0 <= source < len(parent.board) and 0 <= target < len(parent.board)
        and type(parent.board) is tuple and len(parent.board) == owner.compiled.board_size ** 2
        and type(parent.hands) is tuple and len(parent.hands) == 2
        and all(type(h) is Hands for h in parent.hands) and parent.hands == EMPTY_HANDS
        and parent.aux_state == ()
        and parent.ruleset_fingerprint == engine.support.ruleset_fingerprint
        and parent.side_to_move in (0, 1)
        and parent.board_width in (None, owner.compiled.board_size)
        and parent.board_height == parent.board_width
    )
    if supported:
        actor, victim = parent.board[source], parent.board[target]
        capture = len(binding.pattern.effects) == 2
        supported = (
            type(actor) is Piece and actor.owner == parent.side_to_move
            and binding.actor_owner == actor.owner
            and binding.actor_type == actor.current_type_id == action.actor_type
            and binding.actor_base == actor.base_type_id
            and binding.actor_current == actor.current_type_id
            and ((not capture and victim is None) or
                 (capture and type(victim) is Piece and victim.owner == 1 - actor.owner
                  and not getattr(engine.support.type_metadata.get(victim.current_type_id),
                                  'is_anchor', False)))
        )
    if not supported:
        owner.child_fallbacks += 1
        _COUNTERS['fallbacks'] += 1
        return engine._transition(parent, action, binding, checkpoint=checkpoint)
    owner.child_attempts += 1
    _COUNTERS['attempts'] += 1
    board = list(parent.board)
    if capture:
        if checkpoint is not None:
            checkpoint()
        board[target] = None
    if checkpoint is not None:
        checkpoint()
    board[source] = None
    board[target] = actor
    child = Position(tuple(board), EMPTY_HANDS, 1 - parent.side_to_move,
                     engine.support.ruleset_fingerprint, (), None, None)
    owner.child_successes += 1
    _COUNTERS['successes'] += 1
    return child


def _derive_selected_push():
    tree = ast.parse(textwrap.dedent(inspect.getsource(BASE_RUNTIME._push_impl)))
    original_tree = copy.deepcopy(tree)
    class ReplaceSelected(ast.NodeTransformer):
        count = 0
        def visit_Call(self, node):
            self.generic_visit(node)
            f = node.func
            if (isinstance(f, ast.Attribute) and f.attr == '_transition'
                    and isinstance(f.value, ast.Name) and f.value.id == 'engine'):
                assert len(node.args) == 3
                assert [k.arg for k in node.keywords] == ['checkpoint']
                self.count += 1
                node.func = ast.Name('_selected_child', ast.Load())
                node.args = [ast.Name('self', ast.Load()), ast.Name('engine', ast.Load()), *node.args]
            return node
    transformer = ReplaceSelected()
    tree = transformer.visit(tree)
    assert transformer.count == 1, 'selected-consumer source drift'
    class RestoreSelected(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            if isinstance(node.func, ast.Name) and node.func.id == '_selected_child':
                assert [x.id for x in node.args[:2]] == ['self', 'engine']
                node.func = ast.Attribute(ast.Name('engine', ast.Load()), '_transition', ast.Load())
                node.args = node.args[2:]
            return node
    restored = RestoreSelected().visit(copy.deepcopy(tree))
    assert ast.dump(restored) == ast.dump(original_tree), 'transaction body changed outside selected call'
    ast.fix_missing_locations(tree)
    namespace = dict(BASE_RUNTIME._push_impl.__globals__, _selected_child=selected_child)
    exec(compile(tree, '<research selected-child push>', 'exec'), namespace)
    fn = namespace['_push_impl']
    fn.research_derivation = {
        'original_ast_sha256': hashlib.sha256(ast.dump(original_tree).encode()).hexdigest(),
        'candidate_ast_sha256': hashlib.sha256(ast.dump(tree).encode()).hexdigest(),
        'only_selected_call_replaced': True,
        'site_count': transformer.count,
        'original_code_filename': BASE_RUNTIME._push_impl.__code__.co_filename,
    }
    return fn


_setup_tick = time.perf_counter()


class ChildRuntime(BASE_RUNTIME):
    """Exact base runtime, one selected child seam, per-runtime admission cost."""
    _push_impl = _derive_selected_push()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tick = time.perf_counter()
        self.child_engine = runtime.semantic_engine_for(self.compiled)
        # Fail closed on dataclass schema extension as well as the existing IR cert.
        schema_ok = (
            {f.name for f in fields(Piece)} == {'owner', 'base_type_id', 'current_type_id', 'promoted'}
            and {f.name for f in fields(Hands)} == {'counts'}
        )
        self.child_patterns = runtime._plain_leaper_hash_patterns(self.compiled) if schema_ok else None
        self.child_pattern_objects = ({p.pattern_id: p for p in self.child_engine.ir.patterns}
                                      if self.child_engine is not None else {})
        self.child_certification_seconds = time.perf_counter() - tick
        self.child_attempts = self.child_successes = self.child_fallbacks = 0
        _COUNTERS['runtime_count'] += 1
        _COUNTERS['certification_seconds'] += self.child_certification_seconds


DERIVATION_SECONDS = time.perf_counter() - _setup_tick


@contextmanager
def candidate_arm(enabled):
    """Sequential research factory selection; baseline receives no guard tax."""
    search = importlib.import_module('generic_chess.ai.alphabeta.search')
    original = search.SearchPathRuntime
    assert original is BASE_RUNTIME, 'unexpected concurrent runtime patch'
    _COUNTERS.update(runtime_count=0, attempts=0, successes=0, fallbacks=0,
                     certification_seconds=0.0)
    if enabled:
        search.SearchPathRuntime = ChildRuntime
    try:
        yield
    finally:
        search.SearchPathRuntime = original


def metrics():
    return dict(_COUNTERS, derivation_seconds=DERIVATION_SECONDS)
