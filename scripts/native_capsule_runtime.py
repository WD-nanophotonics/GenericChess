"""Opt-in research DFS adapter, not the AlphaBeta runtime or a GameState.

C owns complete history/terminal state. Readonly Python projection has Position,
ply and terminal only. No Python history, TT identity or declaration interface
is promised; consumers requiring those cannot substitute this for Core runtime.
"""
from dataclasses import dataclass
from types import SimpleNamespace

from generic_chess.core.position import Position, Hands
from generic_chess.core.pieces import Piece
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.native import _module, semantic as ns
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import pack_semantic_action


@dataclass(frozen=True, slots=True)
class CapsuleStateView:
    position: Position
    ply_count: int
    terminal_status: TerminalResult


class CapsulePathRuntime:
    def __init__(self, initial, compiled, witnesses):
        self.compiled = compiled
        self.native = compile_native_semantic_rules(compiled)
        self.native.require_terminal_policy_support()
        self.capsule = pack_semantic_search_position(self.compiled, self.native,
            SimpleNamespace(compiled=compiled, state=initial, _search_witnesses=witnesses))
        self._projection = None
        self._terminal = None
        self._rawmap = {}
        self._stack = []
        self.views = self.transitions = 0
        self.legal_provider_calls = self.legal_provider_fallbacks = 0
        self.legal_provider_operational_failures = 0
        assert self.position == initial.position
        assert self.ply_count == initial.ply_count
        assert self.terminal_status == initial.terminal_status

    def attach_stats(self, stats):
        self.stats = stats

    def full_snapshot(self):
        return ns.snapshot(self.native, self.capsule)

    def _project(self):
        if self._projection is None:
            s = _module().semantic_position_snapshot(self.native.capsule, self.capsule)
            ids = self.native.type_ids
            board = tuple(None if x is None else Piece(int(x[2]), ids[int(x[0])],
                ids[int(x[1])], bool(x[3])) for x in s['board'])
            hands = tuple(Hands(tuple(sorted((ids[i], int(v)) for i, v in enumerate(h)
                if v))) for h in s['hands'])
            aux = tuple(((int(z[0]), int(z[1])), tuple(z[2])
                if isinstance(z[2], (tuple, list)) else z[2]) for z in s['aux_state'])
            position = Position(board, hands, int(s['side']), self.compiled.ruleset_fingerprint, aux)
            self._projection = position, int(s['ply'])
            self.views += 1
        return self._projection

    @property
    def position(self):
        return self._project()[0]

    @property
    def ply_count(self):
        return self._project()[1]

    @property
    def terminal_status(self):
        if self._terminal is None:
            t = ns.terminal_status(self.native, self.capsule)
            self._terminal = TerminalResult(TerminalStatus(t['status']), t['winner'])
        return self._terminal

    @property
    def state(self):
        return CapsuleStateView(self.position, self.ply_count, self.terminal_status)

    def in_check(self, owner, checkpoint=None):
        if checkpoint:
            checkpoint()
        return ns.in_check(self.native, self.capsule, owner)

    def legal_actions(self, checkpoint=None):
        if checkpoint:
            checkpoint()
        self.legal_provider_calls += 1
        raw = ns.transient_legal_actions(self.native, self.capsule)
        self._rawmap = {ns.public_action(self.native, a): a for a in raw}
        return tuple(self._rawmap)

    def push(self, action, checkpoint=None):
        if checkpoint:
            checkpoint()
        raw = self._rawmap[action] if action in self._rawmap else pack_semantic_action(
            self.native, self.position, action)
        child = ns.make_checked(self.native, self.capsule, raw)
        self._stack.append((self.capsule, self._projection, self._terminal, self._rawmap))
        self.capsule = child
        self._projection = self._terminal = None
        self._rawmap = {}
        self.transitions += 1

    def pop(self):
        self.capsule, self._projection, self._terminal, self._rawmap = self._stack.pop()

    def assert_balanced(self):
        assert not self._stack
