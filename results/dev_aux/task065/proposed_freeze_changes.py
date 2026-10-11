from copy import deepcopy as _aux_deepcopy

def __init__(self, compiled, native_rules, *, board_values=None, hand_values=None, dynamic_values=None, spatial_occupancy_values=None, localized_control_values=None, compact_values=None, checkpoint=None, ordering_checkpoint=None, evaluator_scale: int=1, tt_megabytes: int=64, ordering_cache_enabled: bool=True, ordering_feature_reuse_enabled: bool=True, ordering_max_ply: int=-1, ordering_min_depth: int=1, policy=None, policy_deferred_legality: bool=False) -> None:
    native_rules.require_terminal_policy_support()
    if getattr(compiled, 'no_progress_draw', None) is not None:
        raise NativeUnsupportedRuleError('native search does not support no-progress draw rules')
    if not native_available():
        raise RuntimeError('native extension is not built')
    if compiled.ruleset_fingerprint != native_rules.fingerprint:
        raise ValueError('ruleset fingerprint mismatch for semantic engine')
    if isinstance(tt_megabytes, bool) or not isinstance(tt_megabytes, int) or (not 0 <= tt_megabytes <= 1024):
        raise ValueError('tt_megabytes must be an integer in [0, 1024]')
    if isinstance(evaluator_scale, bool) or not isinstance(evaluator_scale, int) or (not 1 <= evaluator_scale <= 1024):
        raise ValueError('evaluator_scale must be an integer in [1, 1024]')
    if not isinstance(ordering_cache_enabled, bool):
        raise TypeError('ordering_cache_enabled must be a bool')
    if not isinstance(ordering_feature_reuse_enabled, bool):
        raise TypeError('ordering_feature_reuse_enabled must be a bool')
    if isinstance(ordering_max_ply, bool) or not isinstance(ordering_max_ply, int) or (not -1 <= ordering_max_ply <= GC_SEM_MAX_PLY):
        raise ValueError('ordering_max_ply must be -1 or within GC_SEM_MAX_PLY')
    if isinstance(ordering_min_depth, bool) or not isinstance(ordering_min_depth, int) or (not 1 <= ordering_min_depth <= GC_SEM_MAX_PLY):
        raise ValueError('ordering_min_depth must be within GC_SEM_MAX_PLY')
    self._compiled = compiled
    self._native_rules = native_rules
    self._checkpoint_id = None
    self._ordering_checkpoint_id = None
    self._board_values = _profile_tuple(native_rules, board_values)
    self._hand_values = _profile_tuple(native_rules, hand_values)
    self._dynamic_values = _dynamic_tuple(dynamic_values)
    self._spatial_values = _spatial_tuple(native_rules, spatial_occupancy_values)
    self._localized_control_values = _localized_control_tuple(localized_control_values)
    self._compact_values = None if compact_values is None else _aux_deepcopy(dict(compact_values))
    self._ordering_board_values = None
    self._ordering_hand_values = None
    self._ordering_dynamic_values = None
    self._ordering_spatial_values = None
    self._ordering_localized_control_values = None
    self._ordering_compact_values = None
    self._ordering_evaluator_scale = 1
    self._evaluator_scale = evaluator_scale
    if (self._board_values is None) != (self._hand_values is None):
        raise ValueError('board_values and hand_values must be supplied together')
    self._tt_megabytes = tt_megabytes
    self._ordering_cache_enabled = ordering_cache_enabled
    self._ordering_feature_reuse_enabled = ordering_feature_reuse_enabled
    self._ordering_max_ply = ordering_max_ply
    self._ordering_min_depth = ordering_min_depth
    self._policy_model = None
    if policy is not None:
        if ordering_checkpoint is not None:
            raise ValueError('Semantic Policy-v0 cannot combine with legacy ordering checkpoint')
        if getattr(policy, 'ruleset_fingerprint', None) != compiled.ruleset_fingerprint:
            raise ValueError('semantic policy ruleset fingerprint mismatch')
        if getattr(policy, 'state_schema_id', None) != 'semantic-state-v0':
            raise ValueError('unsupported semantic policy state schema')
        if getattr(policy, 'action_schema_id', None) not in ('semantic-action-v0', 'semantic-action-v1'):
            raise ValueError('unsupported semantic policy action schema')
        if policy_deferred_legality and getattr(policy, 'action_schema_id', None) != 'semantic-action-v1':
            raise ValueError('deferred policy legality requires Semantic Policy-v1')
        self._policy_model = policy
    elif policy_deferred_legality:
        raise ValueError('deferred policy legality requires a policy')
    if not isinstance(policy_deferred_legality, bool):
        raise TypeError('policy_deferred_legality must be a bool')
    self._policy_deferred_legality = policy_deferred_legality
    if checkpoint is not None:
        self._set_checkpoint_values(checkpoint)
    if ordering_checkpoint is not None:
        self._set_ordering_checkpoint_values(ordering_checkpoint)
    self._capsule = self._new_capsule()

def _set_checkpoint_values(self, checkpoint) -> None:
    checkpoint.validate_ruleset(self._compiled)
    type_ids = tuple(self._native_rules.type_ids)
    self._board_values = tuple(checkpoint.semantic_quantized_board(type_ids))
    self._hand_values = tuple(checkpoint.semantic_quantized_hand(type_ids))
    dynamic = checkpoint.semantic_quantized_dynamic()
    self._dynamic_values = None if dynamic is None else tuple(dynamic)
    spatial = checkpoint.semantic_quantized_spatial(type_ids)
    self._spatial_values = None if spatial is None else tuple(spatial)
    control = checkpoint.semantic_quantized_localized_control()
    self._localized_control_values = None if control is None else tuple(control)
    self._compact_values = dict(checkpoint.compact_nonlinear) if checkpoint.compact_nonlinear else None
    self._evaluator_scale = checkpoint.semantic_native_scale
    self._checkpoint_id = checkpoint.checkpoint_id

def _set_ordering_checkpoint_values(self, checkpoint) -> None:
    checkpoint.validate_ruleset(self._compiled)
    type_ids = tuple(self._native_rules.type_ids)
    self._ordering_board_values = tuple(checkpoint.semantic_quantized_board(type_ids))
    self._ordering_hand_values = tuple(checkpoint.semantic_quantized_hand(type_ids))
    dynamic = checkpoint.semantic_quantized_dynamic()
    self._ordering_dynamic_values = None if dynamic is None else tuple(dynamic)
    spatial = checkpoint.semantic_quantized_spatial(type_ids)
    self._ordering_spatial_values = None if spatial is None else tuple(spatial)
    control = checkpoint.semantic_quantized_localized_control()
    self._ordering_localized_control_values = None if control is None else tuple(control)
    self._ordering_compact_values = dict(checkpoint.compact_nonlinear) if checkpoint.compact_nonlinear else None
    self._ordering_evaluator_scale = checkpoint.semantic_native_scale
    self._ordering_checkpoint_id = checkpoint.checkpoint_id

def bind_evaluator(self, board_values, hand_values, dynamic_values=None, spatial_occupancy_values=None, localized_control_values=None, compact_values=None, *, evaluator_scale: int=1) -> None:
    board = _profile_tuple(self._native_rules, board_values)
    hand = _profile_tuple(self._native_rules, hand_values)
    if (board is None) != (hand is None):
        raise ValueError('board_values and hand_values must be supplied together')
    self._board_values, self._hand_values = (board, hand)
    self._dynamic_values = _dynamic_tuple(dynamic_values)
    self._spatial_values = _spatial_tuple(self._native_rules, spatial_occupancy_values)
    self._localized_control_values = _localized_control_tuple(localized_control_values)
    self._compact_values = None if compact_values is None else _aux_deepcopy(dict(compact_values))
    if isinstance(evaluator_scale, bool) or not isinstance(evaluator_scale, int) or (not 1 <= evaluator_scale <= 1024):
        raise ValueError('evaluator_scale must be an integer in [1, 1024]')
    self._evaluator_scale = evaluator_scale
    self._checkpoint_id = None
    self._capsule = self._new_capsule()

@property
def native_evaluator_values(self) -> dict:
    """Return the exact fixed-point values bound to the Native engine."""
    return {'scale': self._evaluator_scale, 'board': tuple(self._board_values or ()), 'hand': tuple(self._hand_values or ()), 'dynamic': tuple(self._dynamic_values or ()), 'spatial_occupancy': tuple(self._spatial_values or ()), 'localized_control': tuple(self._localized_control_values or ()), 'compact_nonlinear': _aux_deepcopy(self._compact_values)}
