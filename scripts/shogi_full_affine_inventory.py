"""Full-stock owner-zero affine inventory, with no scalar hand default."""
from fractions import Fraction as F
from generic_chess.ai.evaluation.config import MAX_STATIC_EVAL
from scripts.resource_mode_context import resource_ledger
from scripts.material_leaf_choice import inventory_features
from scripts.shogi_full_board_inventory import MODES
from scripts.shogi_static_inventory import quantize,SCALE
from scripts.shared_min_envelope_certificate import affine_box_min

BASES=('P','L','N','S','G','B','R')
BOX=((0,SCALE),)*len(BASES)

class FullAffineInventory:
    def __init__(self,compiled,weights):
        if set(weights)!=MODES or any(type(v) is not int and not isinstance(v,F) for v in weights.values()):
            raise ValueError('all thirteen exact board coefficients required')
        self.compiled=compiled;self.weights={t:quantize(v) for t,v in weights.items()}
        if 38*SCALE>=MAX_STATIC_EVAL:raise ValueError('whole-box static separation violated')

    def row(self,state):
        resource_ledger(self.compiled,state.position,'shogi')
        features=inventory_features(state.position,{'K'})
        if any(location=='board' and kind not in self.weights or location=='hand' and kind not in BASES for location,kind in features):
            raise ValueError('unqualified physical inventory mode')
        constant=sum(self.weights[k]*n for (location,k),n in features.items() if location=='board')
        result=(constant,)+tuple(features.get(('hand',base),0) for base in BASES)
        if not (-MAX_STATIC_EVAL<affine_box_min(result,BOX) and affine_box_min(tuple(-v for v in result),BOX)>-MAX_STATIC_EVAL):
            raise ValueError('affine row separation violated')
        return result

def robust_dominators(rows,*,owner):
    if type(owner) is not int or owner not in (0,1) or not rows or len(rows)>64:
        raise ValueError('bounded complete row table and explicit owner required')
    if any(not isinstance(key,str) or not key or len(row)!=8 or any(type(v) is not int for v in row) for key,row in rows.items()):
        raise ValueError('canonical keys and exact full-dimension integer rows required')
    sign=1 if owner==0 else -1;margins={};winners=[]
    for key,row in rows.items():
        margins[key]={other:affine_box_min(tuple(sign*(a-b) for a,b in zip(row,baseline)),BOX)
                      for other,baseline in rows.items() if other!=key}
        if all(v>0 for v in margins[key].values()):winners.append(key)
    return dict(strict_dominators=winners,margins=margins,
                scope='complete one-ply affine static rows, one shared seven-dimensional box; no goal values')
