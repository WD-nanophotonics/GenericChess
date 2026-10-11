def bind_evaluator(self, board_values, hand_values, dynamic_values=None, spatial_occupancy_values=None, localized_control_values=None, compact_values=None, *, evaluator_scale=1):
    staged = object.__new__(type(self))
    staged.__dict__ = self.__dict__.copy()
    _original_bind(staged, board_values, hand_values, dynamic_values, spatial_occupancy_values, localized_control_values, compact_values, evaluator_scale=evaluator_scale)
    self.__dict__.update(staged.__dict__)
