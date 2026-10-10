"""Thin search attribution bridge, not a new production player.

One fixed-order negamax/alpha-beta implementation drives Core, python-chess and
cshogi. Tables below are arbitrary frozen controls, not fitted piece prices.
Fresh snapshots explicitly start a new history. Played roots replay every move.
Western draw policy matches the project's rules, not FIDE claim adjudication.
Nyugyoku declaration is outside this board-action assay, not outside our target.
Run an audit before timing; trace hashing is separately measured overhead.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.ai.evaluation.config import MATE_SCORE
from generic_chess.core.identity import position_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import terminal_result
from generic_chess.core.transition import apply_action
from generic_chess.learning.shogi_rules import gc_action_to_usi, sfen_to_gc_state
from scripts.audit_lichess_complete_children import uci
from scripts.chess_development import root_from_fen

VALUES = {
    'chess': dict(K=0, P=100, N=200, B=300, R=400, Q=500),
    'shogi': dict(K=0, P=100, L=200, N=300, S=400, G=500, B=600, R=700,
                  TP=500, TL=500, TN=500, TS=500, TB=800, TR=900),
}
CASES = [
    dict(id='chess-middle', game='chess', setup='start',
         moves='e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 d2d3 f8c5'),
    dict(id='chess-tactic', game='chess', setup='7k/5ppp/8/8/8/5Q2/6PP/6K1 w - - 0 1', moves=''),
    dict(id='chess-promotion', game='chess', setup='7k/P7/8/8/8/8/7p/K7 w - - 0 1', moves=''),
    dict(id='chess-ep', game='chess', setup='start', moves='e2e4 a7a6 e4e5 d7d5'),
    dict(id='shogi-middle', game='shogi', setup='start',
         moves='7g7f 3c3d 2g2f 8c8d 2f2e 8d8e 2e2d 2c2d'),
    dict(id='shogi-tactic', game='shogi', setup='8k/9/6R2/9/9/9/9/9/K8 b G 1', moves=''),
    dict(id='shogi-promotion', game='shogi', setup='8k/9/4P4/9/9/9/9/9/K8 b - 1', moves=''),
    dict(id='shogi-drop', game='shogi', setup='4k4/9/9/9/9/9/9/9/4K4 b RSnp 1', moves=''),
]


class Material:
    def __init__(self, game):
        self.values = VALUES[game]

    def evaluate(self, state):
        p = state.position
        score = sum((1 if x.owner == p.side_to_move else -1) * self.values[x.current_type_id]
                    for x in p.board if x is not None)
        return score + sum((1 if owner == p.side_to_move else -1) * self.values[tid] * count
                           for owner, hand in enumerate(p.hands) for tid, count in hand.items())

    def type_value(self, tid):
        return self.values[tid]

    def capture_order_value(self, moving, captured):
        return 10 * self.type_value(captured.current_type_id) - self.type_value(moving.current_type_id)


class CoreBoard:
    def __init__(self, case, compiled, provider=None):
        self.game, self.compiled = case['game'], compiled
        setup = case['setup']
        if self.game == 'chess':
            import chess
            state = root_from_fen(chess.STARTING_FEN if setup == 'start' else setup, compiled)
            self.label = uci
        else:
            import cshogi
            sfen = cshogi.Board().sfen() if setup == 'start' else setup
            if sfen.split()[-1] != '1':
                raise ValueError('fresh Shogi snapshots require move number1; replay history otherwise')
            state = sfen_to_gc_state(compiled, sfen)
            key = position_identity_key(state.position, compiled)
            state = replace(state, ply_count=0, history=(HistoryRecord(key, -1, '', False),))
            state = replace(state, terminal_status=terminal_result(state, compiled))
            self.label = gc_action_to_usi
        witnesses = [state.position]
        from generic_chess.core.movegen import legal_actions
        for move in case['moves'].split():
            actions = {self.label(a): a for a in legal_actions(state, compiled)}
            state = apply_action(state, actions[move], compiled)
            witnesses.append(state.position)
        self.initial = state
        self.witnesses = tuple(witnesses)
        self.runtime = SearchPathRuntime.from_state(state, compiled,
            history_witnesses=self.witnesses, legal_binding_provider=provider)
        self.material = Material(self.game)
        self.checkpoint = None

    def actions(self):
        return sorted(((self.label(a), a) for a in self.runtime.legal_actions(checkpoint=self.checkpoint)), key=lambda x: x[0])

    def push(self, action):
        self.runtime.push(action, checkpoint=self.checkpoint)

    def pop(self):
        self.runtime.pop()

    def terminal(self, ply):
        result = self.runtime.terminal_status
        if not result.is_terminal:
            return None
        if result.winner is None:
            return 0
        return (MATE_SCORE-ply if result.winner == self.runtime.position.side_to_move else -MATE_SCORE+ply)

    def evaluate(self):
        return self.material.evaluate(self.runtime.state)

    def snapshot(self):
        p = self.runtime.position
        cells = tuple(None if x is None else (x.owner, x.base_type_id, x.current_type_id, x.promoted)
                      for x in p.board)
        hands = tuple(tuple(h.items()) for h in p.hands)
        return cells, hands, p.side_to_move, p.aux_state, self.runtime.ply_count

    def restored(self):
        return (self.runtime.position == self.initial.position and self.runtime.depth == 0
                and self.runtime.ply_count == self.initial.ply_count
                and self.runtime.terminal_status == self.initial.terminal_status)


class ChessBoard:
    def __init__(self, case):
        import chess
        self.module = chess
        self.board = chess.Board(chess.STARTING_FEN if case['setup'] == 'start' else case['setup'])
        if not self.board.is_valid():
            raise ValueError('invalid Chess snapshot')
        for move in case['moves'].split():
            self.board.push_uci(move)
        self.root_fen, self.root_stack = self.board.fen(), len(self.board.move_stack)
        self.root_ply = self.root_stack
        self.values = {getattr(chess, name): value for name, value in
                       [('KING', 0), ('PAWN', 100), ('KNIGHT', 200), ('BISHOP', 300), ('ROOK', 400), ('QUEEN', 500)]}

    def actions(self):
        return sorted(((m.uci(), m) for m in self.board.legal_moves), key=lambda x: x[0])

    def push(self, action):
        self.board.push(action)

    def pop(self):
        self.board.pop()

    def terminal(self, ply):
        if self.board.is_checkmate():
            return -MATE_SCORE + ply
        if self.board.is_stalemate() or self.root_ply + ply >= 1000:
            return 0
        # Below100000 occurrences in this bounded assay; no FIDE claim/75move/
        # insufficient-material rule is declared by the production RuleSet.
        return None

    def evaluate(self):
        return sum((1 if p.color == self.board.turn else -1)*self.values[p.piece_type]
                   for p in self.board.piece_map().values())

    def snapshot(self):
        chess = self.module
        names = dict(zip(chess.PIECE_TYPES, 'PNBRQK'))
        cells = []
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece is None:
                cells.append(None)
            else:
                promoted = bool(self.board.promoted & chess.BB_SQUARES[square])
                tid = names[piece.piece_type]
                cells.append((0 if piece.color else 1, 'P' if promoted else tid, tid, promoted))
        ep = self.board.ep_square
        aux = {
            'b_ks': int(self.board.has_kingside_castling_rights(chess.BLACK)),
            'b_qs': int(self.board.has_queenside_castling_rights(chess.BLACK)),
            'ep_target': None if ep is None else (chess.square_file(ep), chess.square_rank(ep)),
            'w_ks': int(self.board.has_kingside_castling_rights(chess.WHITE)),
            'w_qs': int(self.board.has_queenside_castling_rights(chess.WHITE)),
        }
        return (tuple(cells), ((), ()), 0 if self.board.turn else 1,
                tuple(((i, -1), aux[name]) for i, name in enumerate(sorted(aux))), len(self.board.move_stack))

    def restored(self):
        return self.board.fen() == self.root_fen and len(self.board.move_stack) == self.root_stack


class ShogiBoard:
    def __init__(self, case):
        import cshogi
        from generic_chess.learning.shogi_rules import CSHOGI_INDEX, HAND_ORDER
        self.module = cshogi
        self.board = cshogi.Board() if case['setup'] == 'start' else cshogi.Board(case['setup'])
        self.history = [(self._identity(), -1, False)]
        for move in case['moves'].split():
            self.push(self.board.move_from_usi(move))
        self.root_sfen = self.board.sfen()
        self.root_history = tuple(self.history)
        self.root_ply = len(case['moves'].split())
        self.values = {index: VALUES['shogi'][tid] for tid, index in CSHOGI_INDEX.items()}
        self.hand_values = {index: VALUES['shogi'][tid] for tid, index in HAND_ORDER.items()}

    def actions(self):
        return sorted(((self.module.move_to_usi(m), m) for m in self.board.legal_moves), key=lambda x: x[0])

    def push(self, action):
        actor = self.board.turn
        self.board.push(action)
        self.history.append((self._identity(), actor, self.board.is_check()))

    def pop(self):
        self.board.pop()
        self.history.pop()

    def _identity(self):
        # Exact piece/hand/turn key; move counter is not position identity.
        return " ".join(self.board.sfen().split()[:3])

    def terminal(self, ply):
        if self.board.is_game_over():
            return -MATE_SCORE + ply
        occurrences = [i for i, record in enumerate(self.history)
                       if record[0] == self.history[-1][0]]
        if len(occurrences) >= 4:
            cycle = self.history[occurrences[-4]+1:]
            checking = [side for side in (0, 1)
                        if any(actor == side for _, actor, _ in cycle)
                        and all(check for _, actor, check in cycle if actor == side)]
            if len(checking) == 1:
                return -MATE_SCORE + ply if checking[0] == self.board.turn else MATE_SCORE - ply
            return 0
        if self.root_ply + ply >= 500:
            raise ValueError('assay excludes the 500-ply extension/declaration boundary')
        return None

    def evaluate(self):
        score = 0
        for piece in self.board.pieces:
            if piece:
                score += (1 if (piece >> 4) == self.board.turn else -1)*self.values[piece & 15]
        for owner, hand in enumerate(self.board.pieces_in_hand):
            score += (1 if owner == self.board.turn else -1)*sum(self.hand_values[i]*n for i, n in enumerate(hand))
        return score

    def snapshot(self):
        from generic_chess.learning.shogi_rules import CSHOGI_INDEX, HAND_ORDER
        names = {index: tid for tid, index in CSHOGI_INDEX.items()}
        bases = dict(TP='P', TL='L', TN='N', TS='S', TB='B', TR='R')
        cells = [None]*81
        for index, piece in enumerate(self.board.pieces):
            if piece:
                tid = names[piece & 15]
                file, rank = divmod(index, 9)
                cells[(8-rank)*9+file] = (piece >> 4, bases.get(tid, tid), tid, tid in bases)
        hands = tuple(tuple(sorted((tid, hand[index]) for tid, index in HAND_ORDER.items() if hand[index]))
                      for hand in self.board.pieces_in_hand)
        return tuple(cells), hands, self.board.turn, (), self.board.move_number-1

    def restored(self):
        return self.board.sfen() == self.root_sfen and tuple(self.history) == self.root_history


@dataclass
class Work:
    nodes: int = 0
    leaves: int = 0
    terminal_queries: int = 0
    legal_queries: int = 0
    pushes: int = 0
    cutoffs: int = 0
    root_completed: int = 0


class Exhausted(Exception):
    pass


def minimal_ab(board, depth, *, seconds=30, node_limit=100000, trace=False, cooperative=False):
    """Identical algorithm and lexicographic actions across backend adapters.

    Nodes count all recursive entries including root and terminal leaves;
    pushes count successful child transitions. Time is checked before each node.
    Completed earlier root children survive a budget exception; no fake D-depth.
    """
    work, digest = Work(), hashlib.sha256()
    runtime_fields = ('pushes', 'pops', 'legal_provider_calls', 'legal_provider_actions',
                      'legal_provider_seconds', 'legal_provider_payload_seconds',
                      'legal_provider_decode_binding_seconds', 'legal_provider_fallbacks',
                      'legal_provider_operational_failures', 'child_external_key_computations',
                      'history_reconstruction_attempts', 'opaque_history_child_external_key_computations')
    runtime = getattr(board, 'runtime', None)
    before = {name: getattr(runtime, name, 0) for name in runtime_fields} if runtime else {}
    start = perf_counter()
    def deadline_checkpoint():
        if perf_counter()-start >= seconds:
            raise Exhausted
    if hasattr(board, 'checkpoint'):
        board.checkpoint = deadline_checkpoint if cooperative else None
    best_move, best_score = None, -MATE_SCORE*2

    def visit(left, alpha, beta, ply):
        nonlocal best_move, best_score
        if work.nodes >= node_limit or perf_counter()-start >= seconds:
            raise Exhausted
        work.nodes += 1
        work.terminal_queries += 1
        terminal = board.terminal(ply)
        if terminal is not None or left == 0:
            work.leaves += 1
            value = terminal if terminal is not None else board.evaluate()
            if trace:
                digest.update(f'L:{ply}:{value};'.encode())
            return value
        work.legal_queries += 1
        actions = board.actions()
        if trace:
            digest.update(('A:' + ','.join(label for label, _ in actions) + ';').encode())
        value = -MATE_SCORE*2
        for label, action in actions:
            board.push(action)
            work.pushes += 1
            try:
                score = -visit(left-1, -beta, -alpha, ply+1)
            finally:
                board.pop()
            if trace:
                digest.update(f'V:{ply}:{label}:{score};'.encode())
            if ply == 0:
                work.root_completed += 1
                if best_move is None or score > best_score:
                    best_move, best_score = label, score
            value = max(value, score)
            alpha = max(alpha, value)
            if alpha >= beta:
                work.cutoffs += 1
                break
        return value

    try:
        score = visit(depth, -MATE_SCORE*2, MATE_SCORE*2, 0)
        reason = 'completed_depth'
    except Exhausted:
        score, reason = (best_score if best_move is not None else None), 'budget'
    finally:
        if hasattr(board, 'checkpoint'):
            board.checkpoint = None
    if not board.restored():
        raise AssertionError('search failed to restore root')
    return dict(move=best_move, score=score, reason=reason, wall_seconds=perf_counter()-start,
                completed_depth=depth if reason == 'completed_depth' else 0,
                work=asdict(work), trace_sha256=digest.hexdigest() if trace else None,
                runtime_counters={name: getattr(runtime, name, 0)-value for name, value in before.items()},
                native_provider_active=None if runtime is None else runtime._legal_provider_active)


def audit_pair(left, right, depth):
    """Compare full legal sets, material, terminals and every descendant.

    This is untimed semantic instrumentation, not a speed measurement.
    """
    checked = 0
    def walk(remaining, ply):
        nonlocal checked
        checked += 1
        assert left.snapshot() == right.snapshot(), ('full state', ply)
        assert left.evaluate() == right.evaluate(), ('material', ply)
        assert left.terminal(ply) == right.terminal(ply), ('terminal', ply)
        if left.terminal(ply) is not None:
            # A specialized library can expose geometric moves after its draw
            # adjudication; Core exposes no further game action. Both searches
            # stop at the matched terminal before querying a move frontier.
            return
        a, b = left.actions(), right.actions()
        assert [x[0] for x in a] == [x[0] for x in b], ('legal', ply,
            sorted(set(x[0] for x in a)^set(x[0] for x in b)))
        if remaining and left.terminal(ply) is None:
            for (_, am), (_, bm) in zip(a, b):
                left.push(am)
                right.push(bm)
                try:
                    walk(remaining-1, ply+1)
                finally:
                    right.pop()
                    left.pop()
    walk(depth, 0)
    assert left.restored() and right.restored()
    return checked


def iterative_minimal(board, *, seconds, node_limit=1000000, max_depth=12):
    """Shared bare iterative driver for common-time decision comparisons.

    Publish the last fully completed depth, otherwise first legal fallback.
    Do not promote a partial high-depth score to a completed-depth reference.
    """
    start = perf_counter()
    actions = board.actions()
    move = actions[0][0] if actions else None
    total = Work()
    score, complete, last = None, 0, None
    for depth in range(1, max_depth+1):
        time_left = seconds-(perf_counter()-start)
        nodes_left = node_limit-total.nodes
        if time_left <= 0 or nodes_left <= 0:
            break
        last = minimal_ab(board, depth, seconds=time_left, node_limit=nodes_left)
        for key, value in last['work'].items():
            setattr(total, key, getattr(total, key)+value)
        if last['reason'] != 'completed_depth':
            break
        complete, move, score = depth, last['move'], last['score']
    return dict(move=move, score=score, completed_depth=complete,
                reason='completed_depth' if complete == max_depth else 'budget',
                fallback=complete == 0, wall_seconds=perf_counter()-start,
                work=asdict(total), interrupted_root_completed=None if last is None else last['work']['root_completed'])


def supported_search(board, depth, seconds, nodes, provider=None):
    """Cold TT/ordering production search, same material; q and tactical scan off.

    Its main+q node definition differs from minimal_ab. Report both, never
    equate numerical node budgets across these algorithms as equal work.
    """
    from generic_chess.ai.alphabeta.search import run_root_search
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    stats = SearchStatistics()
    start = perf_counter()
    action, score, pv, reason = run_root_search(board.initial, board.compiled,
        board.material, TranspositionTable(max_entries=65536),
        SearchLimits(max_depth=depth, max_nodes=nodes, max_time_seconds=seconds,
                     quiescence_max_depth=0, quiescence_hard_max_depth=0),
        None, stats, use_tt=True, use_ordering=True,
        tuning=SearchTuning(use_root_tactical=False),
        _history_witnesses=board.witnesses, legal_binding_provider=provider)
    return dict(move=None if action is None else board.label(action), score=score,
                pv=[board.label(a) for a in pv], reason=reason,
                wall_seconds=perf_counter()-start, statistics=asdict(stats),
                node_definition='main+q recursive visits across iterative depths; unlike minimal fixed depth')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--case', choices=[c['id'] for c in CASES])
    p.add_argument('--depth', type=int, default=2)
    p.add_argument('--seconds', type=float, default=30)
    p.add_argument('--nodes', type=int, default=100000)
    p.add_argument('--audit-depth', type=int, default=1)
    p.add_argument('--repeat', type=int, default=1)
    p.add_argument('--native', action='store_true', help='also compare Native legality on the same Core minimal AB')
    p.add_argument('--supported', action='store_true', help='also run cold TT/ordering iterative production search')
    args = p.parse_args()
    if args.depth < 1 or args.seconds <= 0 or args.seconds > 120 or args.repeat not in range(1, 11):
        p.error('bounded assay: depth>=1, seconds(0,120], repeat1..10')
    if args.audit_depth not in range(0, 3):
        p.error('audit depth0..2; deeper exhaustive trees require a separate cost decision')
    cases = [c for c in CASES if not args.case or c['id'] == args.case]
    if len(cases)*args.repeat*args.seconds*(2+args.native+args.supported) > 3300:
        p.error('expected maximum run above55min; consult necessity before larger run')
    result = dict(schema=1, cases=cases, values=VALUES, configuration=vars(args) | {'output': str(args.output)},
                  versions={name: importlib.metadata.version(name) for name in ('chess', 'cshogi')}, rows=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    compiled = {game: compile_ruleset_for_execution(build_builtin_ruleset(name))
                for game, name in [('chess', 'western_chess'), ('shogi', 'standard_shogi')]}
    for case in cases:
        left = CoreBoard(case, compiled[case['game']])
        right = ChessBoard(case) if case['game'] == 'chess' else ShogiBoard(case)
        audit = audit_pair(left, right, args.audit_depth)
        boards = [('core', left), ('specialized', right)]
        provider = None
        if args.native:
            from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
            provider = NativeSemanticLegalityProvider.try_create(compiled[case['game']], strict=True)
            if provider is None:
                raise RuntimeError('requested Native control unavailable; do not silently rename Core fallback')
            native = CoreBoard(case, compiled[case['game']], provider=provider)
            audit_pair(native, right, args.audit_depth)
            boards.append(('core_native_legality', native))
        if args.supported:
            boards.append(('supported_core', left))
        for repeat in range(args.repeat):
            # Counterbalance timing order; constructors and audit excluded.
            for name, board in (boards if repeat%2 == 0 else list(reversed(boards))):
                row = (supported_search(board, args.depth, args.seconds, args.nodes)
                       if name == 'supported_core' else
                       minimal_ab(board, args.depth, seconds=args.seconds, node_limit=args.nodes))
                result['rows'].append(dict(case=case['id'], backend=name, repeat=repeat, audited_states=audit, **row))
                args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
                print(case['id'], name, repeat, row['reason'],
                      row.get('work', row.get('statistics'))['nodes'], round(row['wall_seconds'], 4), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
