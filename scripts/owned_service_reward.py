"""Research unit-capture accounting, separated from terminal goal utility."""
from fractions import Fraction

from generic_chess.core.actions import action_source_square
from generic_chess.core.semantic_executor import _resolve_square_ref
from scripts.owned_tag_trace import validate_tag


def binding_reward(engine, position, runtime, binding, tag):
    """Exact one-own-action reward from a caller-verified standard binding.

    Qualified standard pattern scope has at most one physical enemy removal,
    preceding any board movement. Unsupported effect ordering fails closed.
    Legality/authentication comes from the complete engine iterator, not IDs.
    """
    validate_tag(position, tag, engine.support.type_metadata)
    if (binding.pattern not in engine.ir.patterns or runtime.pattern_id != binding.pattern.pattern_id
            or binding.actor_owner != position.side_to_move
            or any(getattr(binding, key) != getattr(runtime, key)
                   for key in ('source', 'target', 'geometry_id', 'promotion_target_id'))):
        raise ValueError('exact caller-verified binding required')
    removed = 0; moved = False
    for effect in binding.pattern.effects:
        if effect.kind in ('move', 'shift', 'place', 'remove_from_hand'):
            moved = True
        if effect.kind != 'remove':
            continue
        if moved or effect.disposition not in ('capture_to_hand', 'remove_from_game'):
            raise ValueError('qualified pre-move enemy removal required')
        square = _resolve_square_ref(effect.square_ref, engine.support, engine.ir.aux_slots,
                                     position, binding.actor_owner, binding)
        if square is None or not 0 <= square < len(position.board):
            raise ValueError('resolved victim square required')
        victim = position.board[square]
        if (victim is None or victim.owner == binding.actor_owner
                or engine.support.type_metadata[victim.current_type_id].is_anchor):
            raise ValueError('ordinary enemy physical victim required')
        removed += 1
    if removed > 1:
        raise ValueError('single-victim standard scope required')
    return Fraction(removed)*tag['board'].get(runtime.source, Fraction(0)) if binding.actor_owner == tag['owner'] else Fraction(0)


def public_child_reward(before, after, action, tag, metadata):
    """Independent child-board count control for an authoritative standard child.

    This is not a legality test. Caller supplies a real public transition; no
    guessed terminal payoff is added and capture-to-hand still earns one unit.
    """
    validate_tag(before, tag, metadata)
    if before.side_to_move != tag['owner']:
        return Fraction(0)
    enemy = 1-tag['owner']
    count = lambda p: sum(piece is not None and piece.owner == enemy
                          and not metadata[piece.current_type_id].is_anchor for piece in p.board)
    delta = count(before)-count(after)
    if delta not in (0, 1):
        raise ValueError('single-victim standard child required')
    source = action_source_square(action)
    square = None if source is None else source.rank*before.board_size()+source.file
    return Fraction(delta)*tag['board'].get(square, Fraction(0))


def continuation_prediction(mode_mass, reference_reward):
    """Known expectation and honest[0,unsupported mass] continuation bounds."""
    if any(type(q) is not int and not isinstance(q, Fraction) or not 0 <= q <= 1
           for q in mode_mass.values()) or sum(mode_mass.values()) > 1:
        raise ValueError('substochastic exact mode mass required')
    if any(type(g) is not int and not isinstance(g, Fraction) or not 0 <= g <= 1
           for g in reference_reward.values()):
        raise ValueError('exact unit service reference required')
    known = sum((q*reference_reward[m] for m, q in mode_mass.items() if m in reference_reward), Fraction(0))
    missing = sum((q for m, q in mode_mass.items() if m not in reference_reward), Fraction(0))
    return (known, known+missing)
