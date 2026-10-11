def bind_evaluator(self, board_values, hand_values, dynamic_values=None, spatial_occupancy_values=None, localized_control_values=None, compact_values=None, *, evaluator_scale: int=1) -> None:
    board = _profile_tuple(self._native_rules, board_values)
    hand = _profile_tuple(self._native_rules, hand_values)
    if (board is None) != (hand is None):
        raise ValueError('board_values and hand_values must be supplied together')
    self._board_values, self._hand_values = (board, hand)
    self._dynamic_values = _dynamic_tuple(dynamic_values)
    self._spatial_values = _spatial_tuple(self._native_rules, spatial_occupancy_values)
    self._localized_control_values = _localized_control_tuple(localized_control_values)
    self._compact_values = None if compact_values is None else dict(compact_values)
    if isinstance(evaluator_scale, bool) or not isinstance(evaluator_scale, int) or (not 1 <= evaluator_scale <= 1024):
        raise ValueError('evaluator_scale must be an integer in [1, 1024]')
    self._evaluator_scale = evaluator_scale
    self._checkpoint_id = None
    self._capsule = self._new_capsule()
