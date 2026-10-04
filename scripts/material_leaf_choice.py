"""Exact depth1 choice primitives, not a prior constructor or production search."""
from collections import Counter
from fractions import Fraction

from generic_chess.core.terminal import TerminalStatus


def inventory_features(position, anchor_types):
    """Signed owner-zero counts; board current and held base identities differ."""
    result = Counter()
    for piece in position.board:
        if piece is None:
            continue
        if piece.owner not in (0, 1):
            raise ValueError('invalid board owner')
        if piece.current_type_id not in anchor_types:
            result['board', piece.current_type_id] += 1 if piece.owner == 0 else -1
    for owner, hand in enumerate(position.hands):
        for type_id, count in hand.items():
            if type(count) is not int or count < 0 or type_id in anchor_types:
                raise ValueError('invalid ordinary hand count')
            result['hand', type_id] += count if owner == 0 else -count
    # Keep encountered zero components: missing mode weights must not hide in
    # owner cancellation or a control corpus lacking that mode's imbalance.
    return dict(result)


def material_score(position, weights, anchor_types, token_bound):
    if type(token_bound) is not int or token_bound < 1:
        raise ValueError('positive ordinary-token bound required')
    if any(type(w) is not int and not isinstance(w, Fraction) or not 0 <= w <= 1
           for w in weights.values()):
        raise ValueError('normalized exact nonnegative rational weights required')
    features = inventory_features(position, anchor_types)
    if any(key not in weights for key in features):
        raise ValueError('missing material mode/type weight')
    count = sum(p is not None and p.current_type_id not in anchor_types for p in position.board)
    count += sum(hand.total() for hand in position.hands)
    if count > token_bound:
        raise ValueError('ordinary-token bound exceeded')
    raw = sum((Fraction(weights[key]) * n for key, n in features.items()), Fraction(0))
    return raw / (token_bound + 1)


def material_sensitive_pair(first, second):
    """Mixed-sign inventory difference; does not imply global argmax exposure."""
    difference = [first.get(key, 0) - second.get(key, 0) for key in first.keys() | second.keys()]
    return any(x > 0 for x in difference) and any(x < 0 for x in difference)


def one_ply_choice(children, game, evaluate, *, owner, complete=False, censored_statuses=()):
    """Score a previously completed full choice table before outcome probing.

    children: unique canonical choice-ID -> authoritative child state.
    evaluate returns exact owner-zero nonterminal material in(-1,1).
    Incomplete/unresolved choices produce no selected action, never a fallback.
    """
    if type(owner) is not int or owner not in (0, 1) or not children:
        raise ValueError('nonempty child table and owner0/1 required')
    if complete is not True:
        return {'complete': False, 'selected': None, 'reason': 'incomplete choice table'}
    if any(not isinstance(key, str) or not key for key in children):
        raise ValueError('canonical string choice IDs required')
    censored = frozenset(censored_statuses)
    if any(not isinstance(status, TerminalStatus) or status is TerminalStatus.ONGOING for status in censored):
        raise ValueError('censor only explicit terminal statuses')
    scores = {}
    for key, child in children.items():
        terminal = game.terminal(child)
        if terminal.is_terminal:
            if (terminal.status is TerminalStatus.NO_CONTEST or terminal.status in censored
                    or getattr(terminal, 'unresolved', False)):
                return {'complete': False, 'selected': None, 'reason': 'unqualified terminal/claim',
                        'unresolved_choice': key}
            if terminal.winner not in (None, 0, 1):
                raise ValueError('invalid terminal winner')
            scores[key] = Fraction(0 if terminal.winner is None else 1 if terminal.winner == 0 else -1)
        else:
            value = evaluate(child)
            if type(value) is not int and not isinstance(value, Fraction) or not -1 < value < 1:
                raise ValueError('exact nonterminal material strictly inside(-1,1) required')
            scores[key] = Fraction(value)
    best = (max if owner == 0 else min)(scores.values())
    selected = min(key for key, score in scores.items() if score == best)
    return {'complete': True, 'selected': selected, 'score': best, 'scores': scores}
