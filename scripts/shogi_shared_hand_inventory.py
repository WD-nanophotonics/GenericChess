"""One globally shared held-weight vector, independent of leaf/path."""
from scripts.shogi_static_inventory import StaticInventory,SCALE
from scripts.material_leaf_choice import inventory_features

class SharedHandInventory(StaticInventory):
    def __init__(self,weights,held=None):
        super().__init__(weights);self.held={'P':0,'R':0} if held is None else dict(held)
        if set(self.held)!={'P','R'} or any(type(v) is not int or not 0<=v<=SCALE for v in self.held.values()):raise ValueError('one bounded integer hand vector required')

    def evaluate(self,state):
        value=super().evaluate(state);sign=1 if state.position.side_to_move==0 else -1
        for (location,kind),number in inventory_features(state.position,{'K'}).items():
            if location=='hand':value-=sign*number*(SCALE-self.held[kind])
        return value
