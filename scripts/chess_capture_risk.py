"""Opt-in development leaf residual using semantic pseudo-capture eligibility.

This is an approximation, not legal exchange analysis: pins/check evasions,
recapture sequences, off-target effects and postconditions are not represented.
No side-to-move or history is changed to query the two owners.
"""
from time import perf_counter

from generic_chess.ai.evaluation.config import MAX_STATIC_EVAL
from generic_chess.native.semantic import is_square_attacked, pack_position


class SemanticHangingRisk:
    """Discount unprotected, pseudo-attacked inventory by a declared half.

    The half is an explicit fixed development hypothesis, never fitted to
    answers or interpreted as a calibrated loss probability. All candidates
    use their own existing inventory prices and the identical residual law.
    """

    def __init__(self, base, provider):
        if provider is None:
            raise ValueError('semantic capture-risk requires the native provider')
        self.base = base
        self.provider = provider
        self.queries = 0
        self.risk_calls = 0
        self.risk_seconds = 0.0

    def __getattr__(self, name):
        return getattr(self.base, name)

    def terms(self, state):
        start = perf_counter()
        p = state.position
        rules = self.provider.native_rules
        # State-only pseudo-attack query; neither terminal nor repetition
        # adjudication is attempted with this transient packed projection.
        packed = pack_position(rules, self.provider._state_only_payload(p, state.ply_count))
        losses = [0, 0]
        exposed = []
        for square, piece in enumerate(p.board):
            if piece is None or self.provider.compiled.types_by_id[piece.current_type_id].is_anchor:
                continue
            self.queries += 1
            if not is_square_attacked(rules, packed, square, 1-piece.owner):
                continue
            self.queries += 1
            if is_square_attacked(rules, packed, square, piece.owner):
                continue
            value = self.base.weights[piece.current_type_id]
            losses[piece.owner] += value
            exposed.append(dict(square=square, owner=piece.owner,
                                type_id=piece.current_type_id, value=value))
        delta = losses[1-p.side_to_move]-losses[p.side_to_move]
        # Symmetric truncation avoids a negative-only rounding bias.
        correction = (abs(delta)//2) * (1 if delta >= 0 else -1)
        self.risk_calls += 1
        self.risk_seconds += perf_counter()-start
        return dict(losses=losses, correction=correction, exposed=exposed)

    def evaluate(self, state):
        value = self.base.evaluate(state)+self.terms(state)['correction']
        if abs(value) >= MAX_STATIC_EVAL:
            raise ValueError('capture-risk/static mate separation failed')
        return value
