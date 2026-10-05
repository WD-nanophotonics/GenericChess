"""Full conserved Shogi board inventory; deliberately no held-price choice."""
from generic_chess.ai.evaluation.config import MAX_STATIC_EVAL
from scripts.resource_mode_context import resource_ledger
from scripts.material_leaf_choice import inventory_features
from scripts.shogi_static_inventory import quantize

MODES = frozenset(('P','L','N','S','G','B','R','TP','TL','TN','TS','TB','TR'))

class FullBoardInventory:
    def __init__(self, compiled, weights):
        if set(weights) != MODES:
            raise ValueError('all thirteen ordinary current modes required')
        self.compiled = compiled
        self.weights = {t: quantize(v) for t,v in weights.items()}
        self.calls = 0

    def evaluate(self, state):
        p = state.position
        resource_ledger(self.compiled,p,'shogi')
        if any(h.total() for h in p.hands):
            raise ValueError('held-price law not selected; board-only evaluator')
        value = 0
        for (location,kind),number in inventory_features(p,{'K'}).items():
            if location != 'board' or kind not in self.weights:
                raise ValueError('unqualified inventory mode')
            value += self.weights[kind]*number
        if abs(value) >= MAX_STATIC_EVAL:
            raise ValueError('static separation violated')
        self.calls += 1
        return value if p.side_to_move == 0 else -value
