"""Research-only tag projection from a caller-verified ordered semantic binding.

Private reference resolvers are pinned by the control report. No legality engine,
state transition or policy is replaced; callers supply the authoritative child.
"""
from fractions import Fraction

from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import _resolve_square_ref, _resolve_type_id
from scripts.finite_owned_service import exchangeable_hand_drop

AUX = frozenset(('set_bool', 'clear_right', 'set_token', 'clear_token'))


def _mass(value):
    if type(value) is not int and not isinstance(value, Fraction) or not 0 <= value <= 1:
        raise ValueError('exact tag probability required')
    return Fraction(value)


def validate_tag(position, tag, metadata):
    owner, base = tag['owner'], tag['base']
    if type(owner) is not int or owner not in (0, 1) or base not in metadata or metadata[base].is_anchor:
        raise ValueError('ordinary owner/base tag required')
    board = tag['board']
    for square, value in board.items():
        _mass(value)
        if type(square) is not int or not 0 <= square < len(position.board):
            raise ValueError('valid tag board square required')
        piece = position.board[square]
        if (value <= 0 or piece is None or piece.owner != owner or piece.base_type_id != base
                or metadata[piece.current_type_id].is_anchor):
            raise ValueError('tag board support mismatch')
    held, lost = _mass(tag['held']), _mass(tag['lost'])
    if held and position.hands[owner].count(base) < 1:
        raise ValueError('tag hand support mismatch')
    if sum(board.values(), Fraction(0))+held+lost != 1:
        raise ValueError('tag mass must sum to one')


def trace_tag(engine, before, after, runtime_action, verified_binding, tag):
    """Caller must get binding from legal iterator for this exact parent/action."""
    validate_tag(before, tag, engine.support.type_metadata)
    binding, pattern = verified_binding, verified_binding.pattern
    if (pattern not in engine.ir.patterns or pattern.pattern_id != runtime_action.pattern_id
            or binding.actor_owner != before.side_to_move
            or binding.geometry_id != runtime_action.geometry_id
            or binding.source != runtime_action.source or binding.target != runtime_action.target
            or binding.promotion_target_id != runtime_action.promotion_target_id):
        raise ValueError('exact caller-verified binding required')
    owner, base, side = tag['owner'], tag['base'], binding.actor_owner
    board = list(before.board); hands = [dict(h.items()) for h in before.hands]
    mass = {s: _mass(v) for s, v in tag['board'].items()}
    held, lost = _mass(tag['held']), _mass(tag['lost'])
    body = [e for e in pattern.effects if e.kind not in AUX]
    drop = tuple(e.kind for e in body) == ('remove_from_hand', 'place')
    if any(e.kind in ('remove_from_hand', 'place') for e in body):
        if not drop or any(e.count != 1 for e in body):
            raise ValueError('proved count1 paired hand-drop contract required')
        types = [_resolve_type_id(e.piece_type_ref, binding) for e in body]
        if types[0] is None or types[0] != types[1]:
            raise ValueError('paired drop base mismatch')
    dropped = Fraction(0)
    def square(ref):
        result = _resolve_square_ref(ref, engine.support, engine.ir.aux_slots, before, side, binding)
        if result is None or not 0 <= result < len(board):
            raise ValueError('resolved effect square required')
        return result
    for effect in body:
        kind = effect.kind
        if kind in ('move', 'shift'):
            source, target = square(effect.from_ref), square(effect.to_ref)
            if board[source] is None or board[target] is not None:
                raise ValueError('ordered move occupancy mismatch')
            board[target], board[source] = board[source], None
            if source in mass:
                mass[target] = mass.pop(source)
        elif kind == 'remove':
            source = square(effect.square_ref); victim = board[source]
            if victim is None or effect.disposition not in ('capture_to_hand', 'remove_from_game'):
                raise ValueError('qualified physical removal required')
            q = mass.pop(source, Fraction(0))
            if effect.disposition == 'capture_to_hand':
                hands[side][victim.base_type_id] = hands[side].get(victim.base_type_id, 0)+1
                if q and side == owner:
                    held += q
                else:
                    lost += q
            else:
                lost += q
            board[source] = None
        elif kind == 'remove_from_hand':
            type_id = _resolve_type_id(effect.piece_type_ref, binding)
            count = hands[side].get(type_id, 0)
            if count < 1:
                raise ValueError('positive pre-drop count required')
            if side == owner and type_id == base:
                held, dropped = exchangeable_hand_drop(held, count)
            hands[side][type_id] = count-1
            if not hands[side][type_id]:
                del hands[side][type_id]
        elif kind == 'place':
            target = square(effect.to_ref)
            type_id = _resolve_type_id(effect.piece_type_ref, binding)
            if board[target] is not None:
                raise ValueError('empty paired-drop destination required')
            board[target] = Piece(side, type_id, type_id)
            if dropped:
                mass[target] = dropped
        elif kind == 'set_current_type':
            target = square(effect.square_ref); piece = board[target]
            type_id = _resolve_type_id(effect.type_ref, binding)
            if piece is None or type_id is None:
                raise ValueError('qualified type update required')
            board[target] = Piece(piece.owner, piece.base_type_id, type_id, type_id != piece.base_type_id)
        else:
            raise ValueError('unsupported physical tag effect')
    if runtime_action.promotion_target_id is not None and runtime_action.source is not None:
        target = runtime_action.target; piece = board[target]
        if piece is None or piece.owner != side:
            raise ValueError('promotion actor mismatch')
        board[target] = Piece(piece.owner, piece.base_type_id, runtime_action.promotion_target_id, True)
    if tuple(board) != after.board or hands != [dict(h.items()) for h in after.hands]:
        raise ValueError('trace differs from authoritative public board/hand effects')
    result = {'owner': owner, 'base': base, 'board': mass, 'held': held, 'lost': lost}
    validate_tag(after, result, engine.support.type_metadata)
    return result
