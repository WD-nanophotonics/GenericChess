"""Class-preserving sufficient set order; no invented terminal/material rate."""


def _validate(row):
    if row.get('kind') == 'quiet':
        vector = row.get('vector')
        if not isinstance(vector, (list, tuple)) or len(vector) != 5 or any(type(x) is not int for x in vector):
            raise ValueError('five exact quiet inventory components required')
        if 'source_terminal' in row: raise ValueError('quiet must not disguise terminal')
    elif row.get('kind') == 'source_terminal':
        goal = row.get('source_terminal', {})
        if type(goal.get('value')) is not int or goal['value'] not in (-1, 0, 1):
            raise ValueError('verified source goal value required')
        if 'vector' in row: raise ValueError('true goal must not become an inventory vector')
        winner = goal.get('winner')
        if winner not in (None, 0, 1) or goal['value'] != (0 if winner is None else 1 if winner == 0 else -1):
            raise ValueError('source winner/value inconsistent')
    else: raise ValueError('declared quiet/source-terminal class required')


def dominates(x, y):
    _validate(x); _validate(y)
    if x['kind'] != y['kind']: return False
    if x['kind'] == 'quiet': return all(a >= b for a, b in zip(x['vector'], y['vector']))
    return x['source_terminal']['value'] >= y['source_terminal']['value']


def typed_set_order(candidate, baseline):
    if not candidate or not baseline: raise ValueError('complete nonempty typed sets required')
    for row in list(candidate.values())+list(baseline.values()): _validate(row)
    checks = 0; witnesses = {}; unmatched = []
    for path, x in candidate.items():
        eligible = []
        for other, y in baseline.items():
            checks += 1
            if dominates(x, y): eligible.append(other)
        if eligible: witnesses[path] = min(eligible)
        else: unmatched.append(path)
    return dict(weak_order_proved=not unmatched, strict_improvement_proved=False,
                witnesses=witnesses, unmatched=sorted(unmatched), endpoint_pair_checks=checks,
                candidate_paths_subset_of_baseline=set(candidate) <= set(baseline))
