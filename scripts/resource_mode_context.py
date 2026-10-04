"""Research-only origin/resource guards; not a reachability or value estimator."""
from collections import Counter
from fractions import Fraction

from generic_chess.core.errors import ensure_ruleset_match
from scripts.owned_tag_trace import validate_tag


def resource_ledger(compiled, position, game, *, full_chess=False):
    """Validate origins/custody and return explicit missing Chess resources.

    Shogi conserves global base inventory across both hands; Chess conserves
    each owner's base inventory only after adding the inferred graveyard.
    No synthetic position becomes historically reachable through this guard.
    """
    if (game, compiled.board_size) not in (('chess', 8), ('shogi', 9)):
        raise ValueError('declared standard Chess/Shogi scope required')
    ensure_ruleset_match(position, compiled)
    if type(full_chess) is not bool or position.board_shape.width != compiled.board_size:
        raise ValueError('square standard board and bool full-inventory flag required')
    if len(position.board) != compiled.board_size**2 or len(position.hands) != 2:
        raise ValueError('board/two-hand shape mismatch')
    metadata = compiled.support.type_metadata
    initial = compiled.initial_position
    expected = Counter((p.owner, p.base_type_id) for p in initial.board if p)
    actual = Counter()
    anchors = Counter()
    for piece in position.board:
        if piece is None:
            continue
        if type(piece.owner) is not int or piece.owner not in (0, 1):
            raise ValueError('board owner0/1 required')
        base = metadata.get(piece.base_type_id)
        current = metadata.get(piece.current_type_id)
        if base is None or current is None or type(piece.promoted) is not bool:
            raise ValueError('known base/current and bool promotion required')
        if piece.promoted:
            if base.is_anchor or piece.current_type_id not in base.promotion_target_ids:
                raise ValueError('promotion must preserve an allowed base origin')
        elif piece.current_type_id != piece.base_type_id:
            raise ValueError('unpromoted current/base mismatch')
        if base.is_anchor != current.is_anchor:
            raise ValueError('anchor origin/current mismatch')
        actual[piece.owner, piece.base_type_id] += 1
        if base.is_anchor:
            anchors[piece.owner, piece.base_type_id] += 1
    expected_anchors = Counter({key: n for key, n in expected.items()
                                if metadata[key[1]].is_anchor})
    if anchors != expected_anchors:
        raise ValueError('exact initial anchors per owner required')
    for owner, hand in enumerate(position.hands):
        seen = set()
        for base_id, count in hand.items():
            base = metadata.get(base_id)
            if (base_id in seen or type(count) is not int or count <= 0
                    or base is None or base.is_anchor
                    or not any(t == base_id for _, t in expected)):
                raise ValueError('unique ordinary initial-base positive hand counts required')
            seen.add(base_id)
            if game == 'chess':
                raise ValueError('Chess hands outside declared resource scope')
            actual[owner, base_id] += count
    if game == 'shogi':
        global_expected = Counter()
        global_actual = Counter()
        for (_, base), count in expected.items():
            global_expected[base] += count
        for (_, base), count in actual.items():
            global_actual[base] += count
        if global_actual != global_expected:
            raise ValueError('Shogi global base inventory changed')
        return {'inventory': dict(global_actual), 'graveyard': {}}
    if any(n > expected[key] for key, n in actual.items()):
        raise ValueError('Chess owner/base inventory increased')
    missing = {key: n-actual[key] for key, n in expected.items() if n != actual[key]}
    if full_chess and missing:
        raise ValueError('full Chess inventory required')
    return {'inventory': dict(actual), 'graveyard': missing}


def owned_mode_mass(position, tag, metadata, *, continuation=True):
    """Project a valid identity law without silently mixing native/promoted bases.

    Terminal/declaration endpoint handling is the caller's frozen responsibility;
    explicit continuation=False excludes physically surviving endpoint mass.
    Lost ownership is already absorbing. Fractional hand identities can occupy
    several refined modes at once after drops; do not force a single label.
    """
    if type(continuation) is not bool:
        raise ValueError('explicit bool continuation eligibility required')
    validate_tag(position, tag, metadata)
    if not continuation:
        return {}
    result = Counter()
    for square, mass in tag['board'].items():
        if mass:
            piece = position.board[square]
            result['board', piece.base_type_id, piece.current_type_id] += Fraction(mass)
    if tag['held']:
        result['hand', tag['base']] += Fraction(tag['held'])
    return dict(result)
