"""Lossless path incidence for the declared typed-outcome utility only."""
from scripts.typed_exchange_order import dominates, _validate


def compress(outcomes):
    if not outcomes: raise ValueError('nonempty complete outcome table required')
    groups = {}; rows = {}; incidence = {}
    for path, row in outcomes.items():
        if not isinstance(path, str) or not path: raise ValueError('lossless path IDs required')
        _validate(row)
        signature = ('quiet', *row['vector']) if row['kind'] == 'quiet' else ('source_terminal', row['source_terminal']['value'])
        label = repr(signature)
        groups.setdefault(label, []).append(path); rows.setdefault(label, row); incidence[path] = label
    return dict(groups=groups, representatives=rows, path_to_signature=incidence)


def compressed_order(candidate, baseline, budget):
    x = compress(candidate); y = compress(baseline)
    witnesses = {}; unmatched = []
    for signature, row in x['representatives'].items():
        found = []
        for other, base in y['representatives'].items():
            if budget['remaining'] <= 0:
                return dict(complete=False, weak_order_proved=None, reason='signature-pair cap',
                            candidate=x, baseline=y)
            budget['remaining'] -= 1; budget['checks'] += 1
            if dominates(row, base): found.append(other)
        if found: witnesses[signature] = min(found)
        else: unmatched.append(signature)
    return dict(complete=True, weak_order_proved=not unmatched,
                strict_improvement_proved=False, witnesses=witnesses,
                unmatched=sorted(unmatched), candidate=x, baseline=y,
                candidate_paths_subset_of_baseline=set(candidate) <= set(baseline))
