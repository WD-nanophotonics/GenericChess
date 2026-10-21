"""Opt-in fixed-scale, episode-frozen TDLeaf and material-blind search.

This is the episode learner validated on Chess in DEV_AUX task2492/task2594,
not the separate batch learner in tdleaf.py. Valid-input arithmetic and search
ordering are preserved. Scores/features use player-0 perspective; only actual
rule terminals provide a final W/L/D target. A censored episode may learn its
observed search-to-search transitions, never an invented final draw.

No product defaults, learned prior tables or experiment-directory imports.
"""
from __future__ import annotations

from collections import Counter
from copy import copy
from dataclasses import dataclass, replace
from math import tanh, isfinite, inf
import json
import random
import time

MATE = 1_000_000.0

@dataclass(frozen=True)
class Sample:
    phi: tuple
    lower: float
    upper: float
    depth: int

@dataclass(frozen=True)
class Receipt:
    action: object
    value: float | None
    pv_phi: tuple | None
    pv_terminal: bool
    samples: tuple
    nodes: int
    complete: bool
    q_caps: int
    seconds: float
    reason: str
    completed_depth: int = 0
    attempted_depth: int = 0
    attempts: tuple = ()


@dataclass(frozen=True)
class SearchAttempt:
    depth: int
    nodes: int
    seconds: float
    complete: bool
    reason: str

class BudgetEnd(Exception):
    pass

class Model:

    def __init__(self, weights, *, fixed=0, scale=10.0):
        self.weights = list(map(float, weights))
        self.fixed = fixed
        self.scale = float(scale)
        if not self.weights or not all(map(isfinite, self.weights)) or type(fixed) is not int or not 0 <= fixed < len(self.weights) or not isfinite(self.scale) or self.scale <= 0:
            raise ValueError('invalid model')
        self.weights[fixed] = 1.0

    def raw(self, phi):
        if len(phi) != len(self.weights):
            raise ValueError('feature dimension')
        v = sum((x * w for x, w in zip(phi, self.weights)))
        if not isfinite(v) or abs(v) >= MATE / 2:
            raise ValueError('finite material magnitude exceeds terminal safety margin')
        return v

    def prediction(self, phi):
        return tanh(self.raw(phi) / self.scale)

    def gradient(self, phi):
        v = self.prediction(phi)
        return tuple((0.0 if i == self.fixed else x * (1 - v * v) / self.scale for i, x in enumerate(phi)))

    def apply(self, delta):
        if len(delta) != len(self.weights):
            raise ValueError('update dimension')
        candidate = [w + d for w, d in zip(self.weights, delta)]
        candidate[self.fixed] = 1.0
        if len(delta) != len(self.weights) or not all(map(isfinite, candidate)):
            raise ValueError('nonfinite update')
        self.weights = candidate

def transformed(x, scale):
    return tanh(x / scale)

class AlphaBeta:
    """Full-width search with material-independent randomized ordering.

    No TT, SEE, MVV-LVA, nullmove, futility or material-based pruning.
    Optional capture/check-evasion qsearch requires an admitted environment;
    full Generic sessions currently support qdepth=0 only.
    """

    def __init__(self, depth=2, qdepth=2):
        if depth < 1 or qdepth < 0:
            raise ValueError('invalid depth')
        self.depth, self.qdepth = (depth, qdepth)

    def search(self, env, model, *, nodes=8192, seconds=5.0, seed=0, cancel=lambda: None):
        if self.qdepth and not getattr(env, 'supports_qsearch', True):
            raise ValueError('Generic session adapter supports qdepth=0 only')
        start = time.perf_counter()
        count = 0
        caps = 0
        samples = []
        rng = random.Random(seed)

        def poll():
            nonlocal count
            if count >= nodes or time.perf_counter() - start >= seconds:
                raise BudgetEnd('resource limit')
            if count % 128 == 0:
                cancel()
            count += 1

        def walk(depth, qleft, alpha, beta):
            nonlocal caps
            poll()
            terminal = env.terminal()
            if terminal is not None:
                return (MATE * terminal, None, True, None)
            phi = env.features()
            a0, b0 = (alpha, beta)
            own = env.player() == 0
            if depth == 0:
                checked = env.in_check()
                if qleft == 0:
                    if checked and self.qdepth > 0:
                        raise BudgetEnd('qdepth in check')
                    caps += 1
                    return (model.raw(phi), phi, False, None)
                actions = list(env.actions())
                if not checked:
                    actions = [a for a in actions if env.tactical(a)]
                best = (-inf if own else inf) if checked else model.raw(phi)
                best_phi = phi
                best_terminal = False
                chosen = None
                if not checked:
                    if own:
                        alpha = max(alpha, best)
                    else:
                        beta = min(beta, best)
                    if alpha >= beta:
                        return (best, best_phi, False, None)
            else:
                actions = list(env.actions())
                best = -inf if own else inf
                best_phi = None
                best_terminal = False
                chosen = None
            rng.shuffle(actions)
            for a in actions:
                env.push(a)
                try:
                    score, pv, pvt, _ = walk(max(0, depth - 1), qleft if depth else qleft - 1, alpha, beta)
                finally:
                    env.pop()
                if own and score > best or (not own and score < best):
                    best, best_phi, best_terminal, chosen = (score, pv, pvt, a)
                if own:
                    alpha = max(alpha, best)
                else:
                    beta = min(beta, best)
                if alpha >= beta:
                    break
            if not isfinite(best):
                raise ValueError('ongoing state without actions')
            if depth > 0:
                lo, hi = (-inf, best) if best <= a0 else (best, inf) if best >= b0 else (best, best)
                samples.append(Sample(tuple(phi), lo, hi, depth))
            return (best, best_phi, best_terminal, chosen)
        try:
            cancel()
            v, pv, pvt, action = walk(self.depth, self.qdepth, -inf, inf)
            return Receipt(action, v, pv, pvt, tuple(samples), count, True, caps, time.perf_counter() - start, 'complete', self.depth, self.depth)
        except (BudgetEnd, NonScoringTerminal) as e:
            return Receipt(None, None, None, False, (), count, False, caps, time.perf_counter() - start, str(e), 0, self.depth)


def completed_depth_search(env, model, *, depth=2, nodes=8192, seconds=5.,
                           seed=0, cancel=lambda: None):
    """Opt-in q0 iterative decisions using the existing full-width search.

    Each depth is a fresh search, paid from one shared allowance. Only the
    last complete depth supplies action, PV and training samples. A local
    resource cutoff may retain that result; external cancellation and
    non-scoring semantics discard it. No partial deeper value is exposed.
    """
    if depth < 1 or nodes < 1 or seconds <= 0:
        raise ValueError('invalid decision budget')
    began = time.perf_counter()
    total = caps = 0
    attempts = []
    last = None
    cancelled = None

    def poll():
        nonlocal cancelled
        try:
            cancel()
        except BudgetEnd as error:
            cancelled = str(error)
            raise

    reason = 'resource limit'
    for current_depth in range(1, depth + 1):
        try:
            poll()
        except BudgetEnd:
            reason = cancelled
            last = None
            break
        remaining = seconds - (time.perf_counter() - began)
        if total >= nodes or remaining <= 0:
            break
        receipt = AlphaBeta(current_depth, 0).search(
            env, model, nodes=nodes - total, seconds=remaining,
            seed=seed, cancel=poll)
        total += receipt.nodes
        caps += receipt.q_caps
        attempts.append(SearchAttempt(current_depth, receipt.nodes,
                                      receipt.seconds, receipt.complete, receipt.reason))
        if cancelled is not None:
            reason, last = cancelled, None
            break
        if not receipt.complete:
            reason = receipt.reason
            if reason != 'resource limit':
                last = None
            break
        last = receipt
        reason = 'complete'
    # A stop arriving during the final small search also prevents fallback.
    try:
        poll()
    except BudgetEnd:
        reason, last = cancelled, None
    elapsed = time.perf_counter() - began
    attempted = attempts[-1].depth if attempts else 0
    if last is None:
        return Receipt(None, None, None, False, (), total, False, caps,
                       elapsed, reason, 0, attempted, tuple(attempts))
    if last.completed_depth < depth:
        reason = 'last_completed_depth: resource limit'
    return replace(last, nodes=total, q_caps=caps, seconds=elapsed,
                   reason=reason, attempted_depth=attempted, attempts=tuple(attempts))

class TDLeafEpisode:
    """Frozen-episode Figure-3-style TD(lambda) sum, gamma=1.

    Search-to-search targets use their original frozen gradients. UNKNOWN
    withholds the final TD error but retains observed interior transitions.
    """

    def __init__(self, eta=0.05, lam=0.95):
        if not 0 <= lam <= 1 or not isfinite(eta) or eta < 0:
            raise ValueError('finite nonnegative eta and lambda in [0,1] required')
        self.eta, self.lam = (eta, lam)
        self.reset()

    def reset(self):
        self.rows = []
        self.snapshot = None

    def observe(self, model, receipt):
        if not receipt.complete:
            return dict(samples=0, loss=None, changed=False)
        current = tuple(model.weights)
        if self.snapshot is None:
            self.snapshot = current
        if current != self.snapshot:
            raise ValueError('episode weights changed before TD update')
        value = transformed(receipt.value, model.scale)
        grad = tuple((0.0 for _ in model.weights)) if receipt.pv_terminal else model.gradient(receipt.pv_phi)
        self.rows.append((value, grad))
        return dict(samples=0, loss=None, changed=False)

    def finish(self, model, outcome):
        if outcome is not None and outcome not in (-1, 0, 1):
            raise ValueError('actual outcome must be -1, 0, 1 or None')
        if self.snapshot is not None and tuple(model.weights) != self.snapshot:
            raise ValueError('episode weights changed')
        rows = self.rows
        elig = [0.0] * len(model.weights)
        delta = [0.0] * len(elig)
        loss = 0.0
        terms = 0
        terminal_change = 0.0
        for i, (pred, grad) in enumerate(rows):
            target = rows[i + 1][0] if i + 1 < len(rows) else outcome
            if target is None:
                break
            elig = [self.lam * e + g for e, g in zip(elig, grad)]
            error = float(target) - pred
            loss += error * error / 2
            terms += 1
            for j, e in enumerate(elig):
                delta[j] += error * e
            if i + 1 == len(rows):
                terminal_change = sum((abs(error * e) for e in elig))
        model.apply([self.eta * x for x in delta])
        stats = dict(samples=terms, loss=loss / max(1, terms), changed=any(delta), terminal_credit_l1=terminal_change, observed_searches=len(rows), censored=outcome is None)
        self.reset()
        return stats


@dataclass(frozen=True)
class SessionChoice:
    """A real board/semantic action or owned declaration, never a score label."""

    kind: str
    action: object | None = None
    declaration_id: str | None = None


class NonScoringTerminal(RuntimeError):
    def __init__(self, result):
        self.result = result
        super().__init__('Non-scoring terminal is not W/L/D: ' + str(result))


def compile_channels(compiled, *, unit_type='P'):
    """Board CURRENT types and hand BASE types; one declared fixed board unit."""
    eligible = sorted(p.type_id for p in compiled.piece_types if not p.is_anchor)
    if unit_type not in eligible:
        raise ValueError('declare an existing non-anchor unit type before transfer')
    unit = ('board', unit_type)
    return (unit,) + tuple((kind, name) for kind in ('board', 'hand')
                          for name in eligible if (kind, name) != unit)


class FixedScaleSessionEnv:
    """Full GameSession authority with a material-only value approximation.

    Promotion, drops, semantic actions, declarations, auxiliary state and
    relevant history remain in the session; material channels are not a
    state quotient. Generic quiescence is deliberately unsupported.
    """

    supports_qsearch = False

    def __init__(self, session, *, unit_type='P'):
        self.unit_type = unit_type
        self.session = copy(session)
        self.stack = []
        self.names = compile_channels(session.compiled, unit_type=unit_type)

    def player(self):
        return self.session.state.position.side_to_move

    def features(self):
        position = self.session.state.position
        known = self.session.compiled.types_by_id
        observed = {p.current_type_id for p in position.board if p is not None}
        observed.update(base for hand in position.hands for base, n in hand.counts if n)
        if not observed <= set(known):
            raise ValueError('material observation contains an unknown executable type')
        board, hand = Counter(), Counter()
        for piece in position.board:
            if piece is not None:
                board[piece.current_type_id] += 1 if piece.owner == 0 else -1
        for owner, holding in enumerate(position.hands):
            for base, count in holding.counts:
                hand[base] += (1 if owner == 0 else -1) * count
        return tuple((board if kind == 'board' else hand)[name] for kind, name in self.names)

    def terminal(self):
        from generic_chess.session.result import SessionStatus
        result = self.session.result
        if result.status is SessionStatus.NO_CONTEST or result.declaration_outcome in ('RESTART', 'NO_CONTEST'):
            raise NonScoringTerminal(result)
        if result.status is SessionStatus.ONGOING:
            return None
        return 0 if result.winner is None else 1 if result.winner == 0 else -1

    def actions(self):
        from generic_chess.core.actions import action_to_dict
        from generic_chess.session.result import SessionStatus
        if self.session.result.status is not SessionStatus.ONGOING:
            return ()
        # Include owned LOSS declarations too: available_declarations filters
        # them out, whereas the full old learner/search domain included them.
        declarations = [SessionChoice('DECLARATION', declaration_id=d.declaration_id)
                        for d in sorted(self.session.compiled.declarations, key=lambda d: d.declaration_id)
                        if d.owner == self.player()]
        actions = sorted(self.session.legal_actions(),
                         key=lambda a: json.dumps(action_to_dict(a), sort_keys=True))
        return tuple(declarations) + tuple(SessionChoice('ACTION', action=a) for a in actions)

    def winning_declaration(self):
        """A current rule-authoritative win; assigns no value to other outcomes."""
        wins = [d for d in self.session.available_declarations() if d.outcome == 'WIN']
        if not wins:
            return None
        return SessionChoice('DECLARATION',
                             declaration_id=min(wins, key=lambda d: d.declaration_id).declaration_id)

    def in_check(self):
        return False  # q0 only; no generic stand-pat/qsearch assertion.

    def tactical(self, action):
        raise NotImplementedError('no generic qsearch admission')

    def push(self, choice):
        if not isinstance(choice, SessionChoice):
            raise ValueError('typed session choice required')
        child = copy(self.session)
        if choice.kind == 'ACTION' and choice.action is not None and choice.declaration_id is None:
            child.submit(choice.action)
        elif choice.kind == 'DECLARATION' and choice.action is None and isinstance(choice.declaration_id, str):
            child.declare(choice.declaration_id)
        else:
            raise ValueError('invalid or mixed session choice')
        self.stack.append(self.session)
        self.session = child

    def pop(self):
        self.session = self.stack.pop()

    def record(self):
        from generic_chess.session.serialization import serialize_game_record
        return json.loads(serialize_game_record(self.session.to_record()))

    def replay(self):
        from generic_chess.session.serialization import deserialize_game_record
        from generic_chess.session.session import GameSession
        other = GameSession.replay(self.session.compiled,
                                  deserialize_game_record(json.dumps(self.record())))
        if other.state != self.session.state or other.result != self.session.result or other.to_record() != self.session.to_record():
            raise ValueError('full Generic state/result/history did not survive replay')
        return type(self)(other, unit_type=self.unit_type)


class ChessEnv:
    """Optional python-chess authority, full stack and claimable-draw policy."""

    names = ('P', 'N', 'B', 'R', 'Q')
    supports_qsearch = True

    def __init__(self, board=None):
        import chess  # Optional development dependency, never a material prior.
        self._chess = chess
        self.board = chess.Board() if board is None else board.copy(stack=True)

    def player(self):
        return 0 if self.board.turn else 1

    def features(self):
        c = self._chess
        return tuple(len(self.board.pieces(t, c.WHITE)) - len(self.board.pieces(t, c.BLACK))
                     for t in (1, 2, 3, 4, 5))

    def terminal(self):
        outcome = self.board.outcome(claim_draw=True)
        return None if outcome is None else 0 if outcome.winner is None else 1 if outcome.winner else -1

    def actions(self):
        return tuple(self.board.legal_moves)

    def in_check(self):
        return self.board.is_check()

    def tactical(self, action):
        return self.board.is_capture(action) or action.promotion is not None

    def push(self, action):
        self.board.push(action)

    def pop(self):
        self.board.pop()

    def record(self):
        return dict(initial=self.board.root().fen(), moves=[m.uci() for m in self.board.move_stack], fen=self.board.fen())


def unchanged_model(weights):
    return Model(weights, fixed=0, scale=10.0)


def unchanged_learner():
    return TDLeafEpisode(eta=0.05, lam=0.95)


@dataclass(frozen=True)
class EpisodeResult:
    outcome: int | None
    ending: str
    plies: int
    queries: int
    nodes: int
    seconds: float
    update: dict | None


def play_episode(env, model, *, opponent, learner=None, learner_color=0,
                 horizon=128, depth=2, query_nodes=4096, max_nodes=250_000,
                 seconds=60.0, seed=0, cancel=lambda: None, on_query=None,
                 iterative=False, opponent_depth=None, opponent_iterative=None):
    """One bounded episode; training and evaluation share the same play path.

    The caller owns roots, seeds, aggregate budgets, stop flags and output.
    Pass learner=None for evaluation. Targets always remain player-0-oriented,
    even when the candidate plays player1. An incomplete query advances no
    action; any observed interior TD transitions may still be learned.
    An available rule-authoritative WIN declaration can finish without a search
    query. Its assessment/commit time remains inside the episode deadline.
    Iterative play retains only the last complete q0 depth and pays all attempts.
    Explicit opponent settings permit a fixed foe while comparing candidate
    search policies; omitted settings use the candidate's search configuration.
    """
    if learner_color not in (0, 1) or horizon < 1 or query_nodes < 1 or max_nodes < 1 or seconds <= 0:
        raise ValueError('invalid episode budget or player')
    if learner is not None and (learner.rows or learner.snapshot is not None):
        raise ValueError('episode learner must start with no pending observations')
    began = time.perf_counter()
    deadline = began + seconds
    nodes = queries = plies = 0
    ending = 'HORIZON_UNKNOWN'
    outcome = None

    def guard():
        cancel()
        if time.perf_counter() >= deadline:
            raise BudgetEnd('TIME_CAP_UNKNOWN')

    try:
        for ply in range(horizon):
            guard()
            outcome = env.terminal()
            if outcome is not None:
                ending = 'ACTUAL_TERMINAL'
                break
            remaining = max_nodes - nodes
            if remaining <= 0:
                ending = 'NODE_CAP_UNKNOWN'
                break
            # Execute a rule-authoritative win before asking search to compare
            # it with an unscored outcome. No search score/receipt is fabricated.
            # Assessment/commit time is paid by the existing episode deadline;
            # queries/nodes below count AlphaBeta work, not declaration checks.
            winning = getattr(env, 'winning_declaration', None)
            choice = winning() if winning is not None else None
            if choice is not None:
                guard()
                env.push(choice)
                plies += 1
                continue
            actor = env.player()
            current = model if actor == learner_color else opponent
            current_depth = depth if actor == learner_color or opponent_depth is None else opponent_depth
            current_iterative = iterative if actor == learner_color or opponent_iterative is None else opponent_iterative
            search = completed_depth_search if current_iterative else AlphaBeta(current_depth, 0).search
            search_kwargs = dict(depth=current_depth) if current_iterative else {}
            receipt = search(
                env, current, nodes=min(query_nodes, remaining),
                seconds=min(5., max(1e-9, deadline - time.perf_counter())),
                seed=seed + ply, cancel=guard, **search_kwargs)
            nodes += receipt.nodes
            queries += 1
            if on_query is not None:
                on_query(ply, actor, receipt)
            if not receipt.complete:
                ending = receipt.reason
                break
            guard()
            if learner is not None and actor == learner_color:
                learner.observe(model, receipt)
            env.push(receipt.action)
            plies += 1
    except BudgetEnd as error:
        ending = str(error)
    except NonScoringTerminal:
        ending = 'NON_SCORING_UNKNOWN'
    # The last allowed action may itself finish the real game. This check
    # needs no successor search and cannot turn a resource limit into a draw.
    try:
        outcome = env.terminal()
    except NonScoringTerminal:
        outcome = None
        ending = 'NON_SCORING_UNKNOWN'
    if outcome is not None:
        ending = 'ACTUAL_TERMINAL'
    update = learner.finish(model, outcome) if learner is not None else None
    return EpisodeResult(outcome, ending, plies, queries, nodes,
                         time.perf_counter() - began, update)
