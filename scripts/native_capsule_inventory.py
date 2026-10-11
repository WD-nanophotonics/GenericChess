"""Actual post-transition q inventory with delayed Python Position projection.

Keeps the existing limited material/terminal/check policy; it is not a complete
noisy-move classifier and never predicts effects without applying the action.
"""
from scripts.native_capsule_decode import DecodedCapsulePathRuntime
from generic_chess.native.semantic import material_summary


class InventoryCapsulePathRuntime(DecodedCapsulePathRuntime):
    def __init__(self, initial, compiled, witnesses):
        super().__init__(initial, compiled, witnesses)
        self._summary = None
        self.summary_calls = 0

    def material_summary(self):
        if self._summary is None or self._summary[0] is not self.capsule:
            self._summary = self.capsule, material_summary(self.native, self.capsule)
            self.summary_calls += 1
        return self._summary[1]

    @property
    def side_to_move(self):
        return self.material_summary()[0]

    def noisy_child(self, side, parent_enemies, parent_inventory, checkpoint=None):
        summary = self.material_summary()
        if summary[2][1-side] < parent_enemies or summary[3] != parent_inventory:
            return True
        if self.terminal_status.is_terminal:
            return True
        return self.in_check(summary[0], checkpoint=checkpoint)
