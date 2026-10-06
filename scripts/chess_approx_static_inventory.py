"""Declared approximate material component; never rewrites legal context."""
from fractions import Fraction as F
from generic_chess.ai.evaluation.config import MAX_STATIC_EVAL
from scripts.native_chess_contact_intervals import FINGERPRINT
from scripts.material_leaf_choice import inventory_features
SCALE = 100000


class ChessApproxStaticInventory:
    def __init__(self, weights):
        if set(weights) != set('PNBRQ'):
            raise ValueError('complete ordinary Chess weights required')
        self.weights = {}
        for mode, value in weights.items():
            if (type(value) is not int and not isinstance(value, F)) or not 0 <= value <= 1:
                raise ValueError('exact normalized coefficient required')
            value = F(value)
            self.weights[mode] = (2*value.numerator*SCALE+value.denominator)//(2*value.denominator)
        self.calls = 0

    def evaluate(self, state):
        p = state.position
        if p.ruleset_fingerprint != FINGERPRINT or p.board_shape.width != 8 or p.board_shape.height != 8:
            raise ValueError('native Western rules/shape required')
        if p.side_to_move not in (0, 1) or any(hand.total() for hand in p.hands):
            raise ValueError('native actor/no hands required')
        kings = [0, 0]; ordinary = 0
        for piece in p.board:
            if piece is None: continue
            if type(piece.owner) is not int or piece.owner not in (0, 1):
                raise ValueError('native two-owner scope')
            native = piece.base_type_id == piece.current_type_id and not piece.promoted
            promoted = piece.base_type_id == 'P' and piece.promoted and piece.current_type_id in 'NBRQ'
            if piece.current_type_id == 'K':
                if not native: raise ValueError('native anchors required')
                kings[piece.owner] += 1
            elif piece.current_type_id in self.weights and (native or promoted): ordinary += 1
            else: raise ValueError('unsupported material profile')
        if kings != [1, 1] or ordinary > 30:
            raise ValueError('one King each and30-resource bound required')
        value = sum(self.weights[mode]*n for (location, mode), n in inventory_features(p, {'K'}).items())
        if abs(value) >= MAX_STATIC_EVAL: raise ValueError('mate/static separation failed')
        self.calls += 1
        return value if p.side_to_move == 0 else -value
