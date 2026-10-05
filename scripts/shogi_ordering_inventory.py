"""Separate fixed-leaf capture-ordering adapter, not a new material prior."""
from scripts.shogi_static_inventory import StaticInventory,SCALE

class OrderingInventory(StaticInventory):
    def type_value(self,kind):
        return 0 if kind=='K' else self.weights[kind]

    def capture_order_value(self,moving_piece,captured_piece):
        if captured_piece.current_type_id=='K':raise ValueError('royal capture cannot be ordered')
        if captured_piece.base_type_id not in ('P','R'):raise ValueError('unqualified capture hand')
        return self.type_value(captured_piece.current_type_id)+SCALE-self.type_value(moving_piece.current_type_id)
