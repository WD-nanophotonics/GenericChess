"""Probe-only relative leaf-price controls; Static ordering/dynamics stay intact."""
from dataclasses import replace
from statistics import median
from generic_chess.core.movement import LeapAtom


def relative_profiles(rule, base):
    """Equal prices and finite-board mean empty mobility, median scaled to1000.

    Only explicit plain-Leap/remove probe callers may use these controls. No
    fitted labels, leaf default, learner or value-optimality claim is implied.
    """
    if rule.capture_disposition != 'remove_from_game' or any(
            t.is_promotable or t.promotion_target_ids or not t.movement_atoms
            or any(not isinstance(a,LeapAtom) for a in t.movement_atoms)
            for t in rule.piece_types):
        raise ValueError('relative leaf controls require plain Leap/remove rules')
    shape=rule.board_shape;rates={}
    for t in rule.piece_types:
        if t.is_anchor:continue
        moves={a.offset for a in t.movement_atoms}
        rates[t.type_id]=sum(0<=x+dx<shape.width and 0<=y+dy<shape.height
            for x in range(shape.width) for y in range(shape.height)
            for dx,dy in moves)/(shape.width*shape.height)
    scale=median(rates.values())
    if scale<=0:raise ValueError('nonzero median empty-board mobility required')
    out={}
    for name in ('UNIT','MOBILITY'):
        board={t.type_id:0 if t.is_anchor else (1000 if name=='UNIT' else round(1000*rates[t.type_id]/scale)) for t in rule.piece_types}
        hand={t:round(.9*v) for t,v in board.items()}
        out[name]=replace(base,board_value_by_type=board,hand_value_by_base_type=hand,
            piece_profiles={t:replace(p,normalized_board_value=board[t],normalized_hand_value=hand[t]) for t,p in base.piece_profiles.items()})
    return out,rates
