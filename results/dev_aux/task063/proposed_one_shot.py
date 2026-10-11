def semantic_iterative_search(native_rules, position, max_depth: int, *, max_nodes: int | None=None, max_time_seconds: float | None=None, cancel_token=None, board_values=None, hand_values=None, dynamic_values=None, spatial_occupancy_values=None, localized_control_values=None, compact_values=None, _root_ply_offset: int=0, tt_megabytes: int=0, root_window_pruning: bool=False) -> dict:
    """Run deterministic iterative search on a semantic position.

    The Native entrypoint owns the recursive semantic state stack and checks
    node, monotonic-time, and cooperative-cancellation budgets.  Evaluator
    tables are an immutable call binding; they are not part of the RuleSet
    fingerprint and may be changed between searches.
    """
    if not native_available():
        raise RuntimeError('native extension is not built')
    native_rules.require_terminal_policy_support()
    if _root_ply_offset not in (0, 1):
        raise ValueError('_root_ply_offset must be 0 or 1')
    if isinstance(tt_megabytes, bool) or not isinstance(tt_megabytes, int) or (not 0 <= tt_megabytes <= 1024):
        raise ValueError('tt_megabytes must be an integer in [0, 1024]')
    if not isinstance(root_window_pruning, bool):
        raise TypeError('root_window_pruning must be a bool')
    _require_root_window_support(root_window_pruning)
    if (board_values is None) != (hand_values is None):
        raise ValueError('board_values and hand_values must be supplied together')
    expected = tuple(native_rules.type_ids)
    if isinstance(board_values, Mapping) or isinstance(hand_values, Mapping):
        if not isinstance(board_values, Mapping) or not isinstance(hand_values, Mapping):
            raise ValueError('board_values and hand_values must use the same profile form')
        if set(board_values) != set(expected) or set(hand_values) != set(expected):
            raise ValueError('semantic evaluator profile must cover exactly native type IDs')
        board_values = tuple((int(board_values[type_id]) for type_id in expected))
        hand_values = tuple((int(hand_values[type_id]) for type_id in expected))
    if board_values is not None:
        board_values = tuple((int(value) for value in board_values))
        hand_values = tuple((int(value) for value in hand_values))
    if dynamic_values is not None:
        if isinstance(dynamic_values, Mapping):
            if set(dynamic_values) != {'mobility', 'promotion_potential', 'anchor_safety'}:
                raise ValueError('semantic dynamic evaluator profile must cover exactly the dynamic feature names')
            dynamic_values = tuple((int(dynamic_values[name]) for name in ('mobility', 'promotion_potential', 'anchor_safety')))
        else:
            dynamic_values = tuple((int(value) for value in dynamic_values))
        if len(dynamic_values) != 3:
            raise ValueError('semantic dynamic evaluator profile must contain three values')
    if spatial_occupancy_values is not None:
        if isinstance(spatial_occupancy_values, Mapping):
            spatial_keys = {f'{owner}:{type_id}' for owner in (0, 1) for type_id in expected}
            if set(spatial_occupancy_values) != spatial_keys:
                raise ValueError('semantic spatial evaluator profile must cover every owner/current type')
            spatial_rows = tuple((tuple((int(v) for v in spatial_occupancy_values[f'{owner}:{type_id}'])) for owner in (0, 1) for type_id in expected))
            if any((len(row) != 9 for row in spatial_rows)):
                raise ValueError('each spatial owner/type mapping row must contain nine values')
            spatial_occupancy_values = tuple((value for row in spatial_rows for value in row))
        else:
            spatial_occupancy_values = tuple((int(value) for value in spatial_occupancy_values))
        if len(spatial_occupancy_values) != 2 * len(expected) * 9:
            raise ValueError('semantic spatial evaluator profile length must match 2 * type_count * 9')
        if any((sum(spatial_occupancy_values[i:i + 9]) != 0 for i in range(0, len(spatial_occupancy_values), 9))):
            raise ValueError('semantic spatial evaluator rows must have zero sum')
    if localized_control_values is not None:
        localized_control_values = tuple((int(value) for value in localized_control_values))
        if len(localized_control_values) != 9 or sum(localized_control_values) != 0:
            raise ValueError('semantic localized control profile must contain nine values with zero sum')
    flag = None
    unregister = None
    if cancel_token is not None:
        flag = _module().create_cancel_flag()
        unregister = cancel_token.register_callback(lambda: _module().request_cancel(flag))
    try:
        raw = dict(_module().semantic_iterative_search(native_rules.capsule, position, int(max_depth), None if max_nodes is None else int(max_nodes), None if max_time_seconds is None else float(max_time_seconds), flag, board_values, hand_values, dynamic_values, spatial_occupancy_values, localized_control_values, compact_values, int(_root_ply_offset), int(tt_megabytes), None, 1, None, root_window_pruning))
    finally:
        if unregister is not None:
            unregister()
    raw['best_action'] = None if raw.get('best_action') is None else int(raw['best_action'])
    raw['principal_variation'] = tuple((int(value) for value in raw.get('principal_variation', ())))
    for key in ('score', 'nodes', 'completed_depth', 'selective_depth', 'qnodes', 'elapsed_nanoseconds', 'legal_generation_count', 'transition_count', 'beta_cutoffs', 'tt_probes', 'tt_hits', 'tt_exact_hits', 'tt_stores', 'tt_replacements', 'tt_collisions', 'tt_cutoffs', 'tt_previous_iteration_hits', 'tt_current_iteration_hits', 'tt_allocated_bytes', 'tt_occupied_entries', 'tt_entry_bytes'):
        raw[key] = int(raw.get(key, 0))
    raw['used_fallback'] = bool(raw.get('used_fallback', False))
    raw['declaration_id'] = None if raw.get('declaration_id') is None else str(raw['declaration_id'])
    raw['tt_status'] = 'ENABLED' if tt_megabytes else 'NOT_STARTED'
    raw['elapsed_seconds'] = raw['elapsed_nanoseconds'] / 1000000000.0
    raw['ruleset_fingerprint'] = str(native_rules.fingerprint)
    raw['evaluator_config_hash'] = hashlib.sha256(json.dumps({'ruleset_fingerprint': native_rules.fingerprint, 'board_values': board_values, 'hand_values': hand_values}, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    return raw
