"""Frozen ten public ordered-effect controls; no outcome or coefficient batch."""
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_source_square, action_target_square, action_to_dict
from generic_chess.core.coordinates import Square
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.semantic_executor import semantic_engine_for, _semantic_public_action
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.audit_physical_placement_sampling import serialize_board
from scripts.owned_tag_trace import trace_tag

PROTOCOL = 'docs/research/OWNED_TAG_TRACE_PROTOCOL.md'
PROTOCOL_SHA = '875dff4dbcaf5cb81a75148851d44267d8cf995be3ca49f473b502f8f3eadeeb'


def fixtures(chess, shogi):
    for owner in (0, 1):
        rank = 0 if owner == 0 else 7
        castle = ('4k3/8/8/8/8/8/8/4K2R w K - 0 1',
                  '4k2r/8/8/8/8/8/8/4K3 b k - 0 1')[owner]
        yield 'castle', owner, chess, position_from_fen(castle, chess), Square(4, rank), Square(6, rank), None, {
            'owner': owner, 'base': 'R', 'board': {rank*8+7: Fraction(1)}, 'held': 0, 'lost': 0}, {
            'board': {rank*8+5: Fraction(1)}, 'held': 0, 'lost': 0}
        ep = ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
              '4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1')[owner]
        rank = 4 if owner == 0 else 3
        yield 'ep', owner, chess, position_from_fen(ep, chess), Square(4, rank), Square(3, rank+(1 if owner == 0 else -1)), None, {
            'owner': 1-owner, 'base': 'P', 'board': {rank*8+3: Fraction(1)}, 'held': 0, 'lost': 0}, {
            'board': {}, 'held': 0, 'lost': 1}
        template = initial_state(shogi).position
        for kind in ('promote', 'drop', 'capture_hand'):
            board = [None]*81
            board[0] = Piece(0, 'K', 'K'); board[80] = Piece(1, 'K', 'K')
            hands = [Hands.empty(), Hands.empty()]
            if kind == 'promote':
                rank = 6 if owner == 0 else 2
                destination = rank+(1 if owner == 0 else -1)
                board[rank*9+4] = Piece(owner, 'P', 'P')
                source, target, promotion = Square(4, rank), Square(4, destination), 'TP'
                tag = {'owner': owner, 'base': 'P', 'board': {rank*9+4: Fraction(1)}, 'held': 0, 'lost': 0}
                expected = {'board': {destination*9+4: Fraction(1)}, 'held': 0, 'lost': 0}
            elif kind == 'drop':
                hands[owner] = Hands((('G', 2),))
                source, target, promotion = None, Square(4, 4), None
                tag = {'owner': owner, 'base': 'G', 'board': {}, 'held': 1, 'lost': 0}
                expected = {'board': {40: Fraction(1, 2)}, 'held': Fraction(1, 2), 'lost': 0}
            else:
                rank = 5 if owner == 0 else 3
                board[40] = Piece(owner, 'R', 'R'); board[rank*9+4] = Piece(1-owner, 'P', 'TP', True)
                source, target, promotion = Square(4, 4), Square(4, rank), None
                tag = {'owner': 1-owner, 'base': 'P', 'board': {rank*9+4: Fraction(1)}, 'held': 0, 'lost': 0}
                expected = {'board': {}, 'held': 0, 'lost': 1}
            position = replace(template, board=tuple(board), hands=tuple(hands), side_to_move=owner)
            yield kind, owner, shogi, position, source, target, promotion, tag, expected


def tag_dict(tag):
    return {**tag, 'board': {str(s): str(v) for s, v in tag['board'].items()},
            'held': str(tag['held']), 'lost': str(tag['lost'])}


def audit():
    started = monotonic(); total = 0; transitions = 0
    def checkpoint():
        if monotonic()-started > 10:
            raise TimeoutError('10-second owned-tag control cap')
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen tag protocol changed')
    chess = compile_ruleset_for_execution(build_western_chess_ruleset())
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    rows = []
    for kind, owner, compiled, position, source, target, promotion, tag, expected in fixtures(chess, shogi):
        checkpoint(); root = synthetic_state(compiled, position); engine = semantic_engine_for(compiled)
        if root.terminal_status.is_terminal or any(engine.in_check(position, o) for o in (0, 1)):
            raise ValueError('declared ongoing unchecked fixture required')
        count = 0; matches = []
        for runtime, binding in engine.iter_legal_action_bindings(position, checkpoint=checkpoint):
            count += 1; total += 1
            if count > 128 or total > 512:
                raise RuntimeError('owned-tag public enumeration cap exceeded')
            action = _semantic_public_action(engine, runtime)
            if (action_source_square(action) == source and action_target_square(action) == target
                    and getattr(action, 'promotion_target_id', None) == promotion
                    and (kind != 'drop' or action.base_type_id == 'G')):
                matches.append((action, runtime, binding))
        if len(matches) != 1:
            raise ValueError(f'unique declared {kind}/{owner} public choice missing')
        action, runtime, binding = matches[0]
        if transitions >= 10:
            raise RuntimeError('ten-public-transition cap exceeded')
        child = apply_action(root, action, compiled); transitions += 1; checkpoint()
        result = trace_tag(engine, position, child.position, runtime, binding, tag)
        if any(result[k] != expected[k] for k in expected):
            raise AssertionError(f'frozen {kind}/{owner} tag result refuted')
        if kind == 'promote' and child.position.board[runtime.target].current_type_id != 'TP':
            raise AssertionError('promoted mode missing')
        if kind == 'capture_hand' and child.position.hands[owner].count('P') != 1:
            raise AssertionError('public demotion/custody conversion missing')
        if len(child.history) != len(root.history)+1:
            raise AssertionError('history transition missing')
        rows.append({'fixture': kind, 'actor_owner': owner, 'action': action_to_dict(action),
                     'root_choices': count, 'before_tag': tag_dict(tag), 'after_tag': tag_dict(result),
                     'before_board': serialize_board(position), 'after_board': serialize_board(child.position),
                     'before_hands': [dict(h.items()) for h in position.hands],
                     'after_hands': [dict(h.items()) for h in child.position.hands],
                     'history_lengths': [len(root.history), len(child.history)]})
    paths = [PROTOCOL, 'scripts/audit_owned_tag_trace.py', 'scripts/owned_tag_trace.py',
             'scripts/finite_owned_service.py', 'generic_chess/core/semantic_executor.py',
             'generic_chess/core/pieces.py', 'generic_chess/core/position.py',
             'generic_chess/core/transition.py', 'generic_chess/rules/western_chess.py',
             'generic_chess/rules/standard_shogi.py']
    checkpoint()
    return {'complete': True, 'scope': 'owned-tag semantic controls, no coefficients/goal labels',
            'fixtures': rows, 'enumerated_choices': total, 'public_transitions': transitions,
            'sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
            'elapsed_seconds': monotonic()-started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('fixtures', 'sha256')}, indent=2))
