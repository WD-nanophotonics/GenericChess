"""Frozen B/N paired captures and R castling-origin boundary; no prices."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_source_square, action_target_square
from generic_chess.core.coordinates import Square
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for, _semantic_public_action
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.audit_resource_mode_feasibility import canonical_choice
from scripts.public_goal_intervals import PublicGame
from scripts.resource_mode_context import resource_ledger

PROTOCOL = 'docs/research/CHESS_MINOR_ROOK_ORIGIN_PROTOCOL.md'
PROTOCOL_SHA = '277a4ef1ce66f4ccacc294d00647299c7cbffe2ce8115cd15fc8fa139f8c808c'


def projection(state):
    return {'board': [None if p is None else [p.owner, p.current_type_id] for p in state.position.board],
            'hands': [list(h.items()) for h in state.position.hands],
            'side': state.position.side_to_move, 'aux': state.position.aux_state,
            'ply': state.ply_count,
            'terminal': [state.terminal_status.status.value, state.terminal_status.winner],
            'history': [(h.actor, h.action_signature, h.gave_check) for h in state.history],
            'repetition_shape': sorted(n for _, n in state.repetition_counts)}


def mirrored(position):
    board = [None]*64
    for index, piece in enumerate(position.board):
        if piece:
            board[(7-index//8)*8+index%8] = Piece(1-piece.owner, piece.base_type_id,
                                                piece.current_type_id, piece.promoted)
    # Explicitly swap white/black rights, retaining generic slot order from FEN helper.
    aux = dict(position.aux_state)
    aux[(0, -1)], aux[(3, -1)] = aux[(3, -1)], aux[(0, -1)]
    aux[(1, -1)], aux[(4, -1)] = aux[(4, -1)], aux[(1, -1)]
    return replace(position, board=tuple(board), side_to_move=1-position.side_to_move,
                   aux_state=tuple(sorted(aux.items())))


def audit():
    started = monotonic(); enumerated = 0; transitions = 0; rows = []
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('prospective protocol must be frozen')
    def checkpoint():
        if monotonic()-started >= 10:
            raise TimeoutError('frozen10-second control cap')
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    engine = semantic_engine_for(compiled); game = PublicGame(compiled)
    def choices(position):
        nonlocal enumerated
        checkpoint(); resource_ledger(compiled, position, 'chess')
        state = synthetic_state(compiled, position)
        if game.terminal(state).is_terminal:
            raise ValueError('ongoing control required')
        public = {}; bindings = set()
        for action in game.actions(state, checkpoint):
            checkpoint(); enumerated += 1; key = canonical_choice(action)
            if key in public or len(public) >= 128 or enumerated > 5000:
                raise ValueError('public action cap/duplicate')
            public[key] = action
        for runtime, binding in engine.iter_legal_action_bindings(position, checkpoint=checkpoint):
            checkpoint(); enumerated += 1; key = canonical_choice(_semantic_public_action(engine, runtime))
            if key in bindings or len(bindings) >= 128 or enumerated > 5000:
                raise ValueError('binding cap/duplicate')
            bindings.add(key)
        if public.keys() != bindings:
            raise ValueError('public/binding complete sets disagree')
        return state, public
    def execute(state, action):
        nonlocal transitions
        checkpoint()
        if transitions >= 14:
            raise ValueError('14-transition prospective cap')
        child = game.successor(state, action); transitions += 1; checkpoint()
        return child
    def select(public, source, target):
        matches = [a for a in public.values() if action_source_square(a) == source
                   and action_target_square(a) == target]
        if len(matches) != 1:
            raise ValueError('unique prospective coordinate action required')
        return matches[0]
    for owner in (0, 1):
        for tid, fen, target0 in (
            ('B', '7k/6r1/8/8/3B4/8/8/K7 w - - 0 1', Square(6, 6)),
            ('N', '7k/8/8/5r2/3N4/8/8/K7 w - - 0 1', Square(5, 4)),
        ):
            template = position_from_fen(fen, compiled); pair = []
            for base in (tid, 'P'):
                board = list(template.board); board[27] = Piece(0, base, tid, base == 'P')
                position = replace(template, board=tuple(board))
                if owner:
                    position = mirrored(position)
                state, public = choices(position)
                source = Square(3, 4 if owner else 3)
                target = Square(target0.file, 7-target0.rank) if owner else target0
                child = execute(state, select(public, source, target))
                pair.append((set(public), projection(child)))
            if pair[0] != pair[1]:
                raise AssertionError('paired minor current/history relation refuted')
            rows.append({'owner': owner, 'current': tid, 'complete_root_choices': len(pair[0][0]),
                         'origins_equal': True, 'qualified_capture_child': pair[0][1]})
        template = position_from_fen('k7/8/8/8/8/8/8/4K2R w K - 0 1', compiled)
        with_rights = []
        for base in ('R', 'P'):
            board = list(template.board); board[7] = Piece(0, base, 'R', base == 'P')
            position = replace(template, board=tuple(board))
            if owner:
                position = mirrored(position)
            state, public = choices(position); with_rights.append((state, public))
        castles = [key for key, a in with_rights[0][1].items() if 'castle_' in getattr(a, 'pattern_id', '')]
        if len(castles) != 1 or set(with_rights[0][1])-set(with_rights[1][1]) != set(castles) or set(with_rights[1][1])-set(with_rights[0][1]):
            raise AssertionError('expected sole native castling difference refuted')
        castle_child = execute(with_rights[0][0], with_rights[0][1][castles[0]])
        rank = 7 if owner else 0
        if (castle_child.position.board[rank*8+6] != Piece(owner, 'K', 'K')
                or castle_child.position.board[rank*8+5] != Piece(owner, 'R', 'R')):
            raise AssertionError('native castle physical positions refuted')
        own_slots = (0, 1) if owner else (3, 4)
        if any(dict(castle_child.position.aux_state).get((slot, -1), 1) for slot in own_slots):
            raise AssertionError('own castling rights not cleared')
        no_rights = []
        for state, _ in with_rights:
            aux = dict(state.position.aux_state)
            for slot in own_slots:
                aux[(slot, -1)] = 0
            state, public = choices(replace(state.position, aux_state=tuple(sorted(aux.items()))))
            child = execute(state, select(public, Square(7, rank), Square(7, 6 if owner else 1)))
            no_rights.append((set(public), projection(child)))
        if no_rights[0] != no_rights[1]:
            raise AssertionError('no-rights rook current/history relation refuted')
        rows.append({'owner': owner, 'current': 'R', 'imported_rights_counterexample': True,
                     'native_choices': len(with_rights[0][1]), 'promoted_choices': len(with_rights[1][1]),
                     'native_only_castle': castles[0], 'no_rights_choices': len(no_rights[0][0]),
                     'no_rights_origins_equal': True, 'native_castle_child': projection(castle_child)})
    if transitions != 14:
        raise AssertionError('declared transition count not complete')
    paths = [PROTOCOL, 'scripts/audit_chess_minor_rook_origin.py', 'generic_chess/rules/western_chess.py',
             'generic_chess/core/semantic_executor.py', 'scripts/audit_exchange_custody.py',
             'scripts/audit_f24f_western_chess_perft.py', 'scripts/audit_resource_mode_feasibility.py',
             'scripts/public_goal_intervals.py', 'scripts/resource_mode_context.py']
    return {'complete': True, 'public_transitions': transitions, 'enumerated': enumerated,
            'seconds': monotonic()-started, 'source_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
            'scope': 'synthetic paired controls; no historical reachability, population, or prices', 'rows': rows}


if __name__ == '__main__':
    result = audit()
    target = ROOT/'data/chess_minor_rook_origin_20261004.json'
    if target.exists():
        raise FileExistsError('preserve original evidence; no overwrite rerun')
    target.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'complete': result['complete'], 'transitions': result['public_transitions'],
                      'enumerated': result['enumerated'], 'seconds': result['seconds']}))
