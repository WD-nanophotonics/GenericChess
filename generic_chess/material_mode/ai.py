"""Small two-player material-only negamax; no neural/native/UI dependencies."""
from __future__ import annotations
from dataclasses import dataclass
import random
import time
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.limits import SearchLimits
from .model import ModeAction


@dataclass(frozen=True, slots=True)
class ModeDecision:
    action: ModeAction | None
    score_units: int
    completed_depth: int
    nodes: int
    cancelled: bool = False


class _BudgetStop(Exception):
    pass


class _Cancelled(Exception):
    pass


class BasicTwoPlayer:
    def __init__(self, *, seed=0):
        self._random = random.Random(seed)

    def choose_action(self, session, limits: SearchLimits | None = None, *, cancel_token: CancellationToken | None = None):
        if session.rules.players != 2:
            raise NotImplementedError('four-player AI is intentionally not implemented')
        limits = limits or SearchLimits(max_depth=2, max_nodes=2000, max_time_seconds=1.0, quiescence_max_depth=0)
        depth_limit = 2 if limits.max_depth is None else limits.max_depth
        node_limit = 2000 if limits.max_nodes is None else limits.max_nodes
        time_limit = 1.0 if limits.max_time_seconds is None else limits.max_time_seconds
        started = time.perf_counter()
        nodes = 0
        engine = session._engine
        root = session.state
        if cancel_token is not None and cancel_token.is_cancelled():
            return ModeDecision(None, 0, 0, 0, True)
        if root.result.terminal:
            return ModeDecision(None, 0, 0, 0)
        actions = engine.legal_actions(root)
        if not actions:
            return ModeDecision(None, 0, 0, 0)
        best = actions[0]
        completed_depth = 0
        mate = engine.material_ceiling + 1

        def evaluation(state):
            actor = state.current_player
            if state.result.terminal:
                return 0 if state.result.winner is None else mate if state.result.winner == actor else -mate
            return engine.material_value(state, actor) - engine.material_value(state, 1 - actor)

        best_score = evaluation(root)

        def checkpoint():
            if cancel_token is not None and cancel_token.is_cancelled():
                raise _Cancelled
            if nodes >= node_limit or time.perf_counter() - started >= time_limit:
                raise _BudgetStop

        def negamax(state, depth):
            nonlocal nodes
            checkpoint()
            nodes += 1
            if depth == 0 or state.result.terminal:
                return evaluation(state)
            return max(-negamax(engine.after_legal(state, a), depth - 1) for a in engine.legal_actions(state))

        try:
            for depth in range(1, depth_limit + 1):
                value = None
                ties = []
                for action in actions:
                    checkpoint()
                    score = -negamax(engine.after_legal(root, action), depth - 1)
                    if value is None or score > value:
                        value, ties = score, [action]
                    elif score == value:
                        ties.append(action)
                # Full root iteration only. Equal material choices get no extra
                # positional heuristic; seeded ties allow purchases as well.
                best, best_score = self._random.choice(ties), value
                completed_depth = depth
        except _Cancelled:
            return ModeDecision(None, best_score, completed_depth, nodes, True)
        except _BudgetStop:
            pass
        if cancel_token is not None and cancel_token.is_cancelled():
            return ModeDecision(None, best_score, completed_depth, nodes, True)
        return ModeDecision(best, best_score, completed_depth, nodes)
