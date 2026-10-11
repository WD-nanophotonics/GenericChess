def _spatial_tuple(native_rules, values):
    if values is None:
        return None
    type_ids = tuple(native_rules.type_ids)
    if isinstance(values, Mapping):
        expected = {f'{owner}:{type_id}' for owner in (0, 1) for type_id in type_ids}
        if set(values) != expected:
            raise ValueError('semantic spatial evaluator profile must cover every owner/current type')
        rows = [tuple((int(v) for v in values[f'{owner}:{type_id}'])) for owner in (0, 1) for type_id in type_ids]
        if any((len(row) != SPATIAL_CELL_COUNT for row in rows)):
            raise ValueError('each spatial owner/type mapping row must contain nine values')
        result = tuple((value for row in rows for value in row))
    else:
        result = tuple((int(value) for value in values))
    expected_length = 2 * len(type_ids) * SPATIAL_CELL_COUNT
    if len(result) != expected_length:
        raise ValueError('semantic spatial evaluator profile length must match 2 * type_count * 9')
    for offset in range(0, len(result), SPATIAL_CELL_COUNT):
        if sum(result[offset:offset + SPATIAL_CELL_COUNT]) != 0:
            raise ValueError('semantic spatial evaluator rows must have zero sum')
    return result
