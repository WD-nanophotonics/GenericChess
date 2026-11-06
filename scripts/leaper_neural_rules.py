"""Explicit ordinary-Leaper research domain and structural equality."""
from generic_chess.core.movement import LeapAtom

def admitted(rules):
    """The explicit first domain: ordinary leap, removal capture, royal safety."""
    w,h=rules.board_shape.width,rules.board_shape.height
    if not (4<=w<=19 and 4<=h<=19):raise ValueError('board outside4..19')
    if w!=h:raise ValueError('current Core baseline executes square boards only; rectangular graph support is not claimed')
    if rules.capture_disposition!='remove_from_game' or rules.repetition_policy!='draw':raise ValueError('unsupported capture/history policy')
    if rules.semantic_actions or rules.declarations or rules.automatic_adjudications or rules.pass_enabled or rules.consecutive_action_adjudications or rules.repeated_cycle_target_conditions or rules.no_progress_draw:
        raise ValueError('conditional/session/auxiliary rules not in first domain')
    if any(p.is_promotable or p.promotion_target_ids or any(not isinstance(a,LeapAtom) for a in p.movement_atoms) for p in rules.piece_types):raise ValueError('ordinary nonpromoting leapers only')
    if any(any(row) for owners in rules.drop_allowed.values() for row in owners):raise ValueError('drops not supported')
    if any(promotion for owners in rules.promotion_allowed.values() for promotion in owners):raise ValueError('promotion not supported')
    if any(abs(x)>18 or abs(y)>18 or (x,y)==(0,0) for p in rules.piece_types for x,y in (a.offset for a in p.movement_atoms)):
        raise ValueError('offset outside37x37 structural domain')


def rule_signature(piece_type):
    # A structural tuple is for equality/grouping, NEVER a numeric NN feature.
    return (piece_type.is_anchor,tuple(sorted(set(a.offset for a in piece_type.movement_atoms))))
