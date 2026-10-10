"""Thin lexical-AB adapter over full Native state, for backend attribution.

This is a diagnostic adapter, not a player or an algorithm replacement. It
uses the existing generic C rules/state/history and public action conversions.
Unsupported terminal policies are rejected before search. Compilation and root
packing happen at construction, outside warm-search timing. Python owns the AB
stack/order; C owns each immutable position and semantic history. No TT, qsearch,
learned ordering, dynamic features or game-specific Native rule implementation.
"""
from generic_chess.ai.evaluation.config import MATE_SCORE
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import (
    evaluate, guarded_actions, make_checked, public_action, snapshot, terminal_status,
)
from generic_chess.session.session import GameSession


class NativeBoard:
    def __init__(self, core_board, values):
        self.compiled = core_board.compiled
        self.native = compile_native_semantic_rules(self.compiled)
        self.native.require_terminal_policy_support()
        session = GameSession(self.compiled)
        session._state = core_board.initial
        session._search_history_witnesses = core_board.witnesses
        root = pack_semantic_search_position(self.compiled, self.native, session)
        self.stack = [root]
        self.root_snapshot = snapshot(self.native, root)
        self.label = core_board.label
        self.values = tuple(values[tid] for tid in self.native.type_ids)
        self.checkpoint = None

    @property
    def position(self):
        return self.stack[-1]

    def actions(self):
        return sorted(
            ((self.label(public_action(self.native, raw)), raw)
             for raw in guarded_actions(self.native, self.position)),
            key=lambda entry: entry[0],
        )

    def push(self, raw):
        self.stack.append(make_checked(self.native, self.position, raw))

    def pop(self):
        if len(self.stack) == 1:
            raise ValueError('cannot pop the diagnostic root')
        self.stack.pop()

    def terminal(self, ply):
        result = terminal_status(self.native, self.position)
        if result['status'] == 'ongoing':
            return None
        if result['winner'] is None:
            return 0
        side = snapshot(self.native, self.position)['side']
        return MATE_SCORE-ply if result['winner'] == side else -MATE_SCORE+ply

    def evaluate(self):
        return evaluate(self.native, self.position,
                        board_values=self.values, hand_values=self.values)

    def restored(self):
        return len(self.stack) == 1 and snapshot(self.native, self.position) == self.root_snapshot


def audit_native_tree(core, native, depth):
    """Untimed every-child state/history, authority, evaluation and frontier audit."""
    checked = 0
    from types import SimpleNamespace
    witnesses = list(core.witnesses)
    def walk(left, ply):
        nonlocal checked
        checked += 1
        session = GameSession(core.compiled)
        session._state = SimpleNamespace(position=core.runtime.position,
            ply_count=core.runtime.ply_count, history=tuple(core.runtime.history))
        session._search_history_witnesses = tuple(witnesses)
        expected = pack_semantic_search_position(core.compiled, native.native, session)
        assert snapshot(native.native, expected) == snapshot(native.native, native.position), ('state/history', ply)
        assert core.terminal(ply) == native.terminal(ply), ('terminal', ply)
        assert core.evaluate() == native.evaluate(), ('material', ply)
        if core.terminal(ply) is not None:
            return
        a, b = core.actions(), native.actions()
        assert [x[0] for x in a] == [x[0] for x in b], ('frontier', ply)
        if left:
            for (_, am), (_, bm) in zip(a, b):
                core.push(am)
                native.push(bm)
                witnesses.append(core.runtime.position)
                try:
                    walk(left-1, ply+1)
                finally:
                    witnesses.pop()
                    native.pop()
                    core.pop()
    walk(depth, 0)
    assert core.restored() and native.restored()
    return checked
