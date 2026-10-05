"""Fixed quantization and physical inventory evaluator, research-only."""
from fractions import Fraction as F
from generic_chess.ai.evaluation.config import MAX_STATIC_EVAL
from scripts.material_leaf_choice import inventory_features
SCALE=100000

def quantize(value):
    value=F(value)
    if not 0<=value<=1:raise ValueError('normalized coefficient required')
    return (2*value.numerator*SCALE+value.denominator)//(2*value.denominator)

class StaticInventory:
    def __init__(self,weights):
        self.weights={t:quantize(v) for t,v in weights.items()}
        if set(self.weights)!={'P','TP','R'}:raise ValueError('frozen board-mode scope')
        self.calls=0

    def evaluate(self,state):
        p=state.position; count=sum(x is not None and x.current_type_id!='K' for x in p.board)+sum(h.total() for h in p.hands)
        if count>2:raise ValueError('two-resource bound')
        value=0
        for (location,kind),number in inventory_features(p,{'K'}).items():
            if location=='board':weight=self.weights[kind]
            elif location=='hand' and kind in ('P','R'):weight=SCALE
            else:raise ValueError('unqualified physical mode')
            value+=weight*number
        if abs(value)>=MAX_STATIC_EVAL:raise ValueError('static separation violated')
        self.calls+=1
        return value if p.side_to_move==0 else -value
