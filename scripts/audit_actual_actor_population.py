"""Exact marked-actor measures; abstract task flags, not game coefficients."""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROTOCOL = ROOT / 'docs/research/ACTUAL_ACTOR_POPULATION_PROTOCOL.md'
PROTOCOL_SHA = 'f7398eb4f948ebdf26e4ec852587150cc1eaf74cc563317e415e9004d10509b5'


@dataclass(frozen=True)
class Actor:
    kind: str
    source: str
    success: bool


def summarize(contexts):
    """Keep each context and actor intact; never replace a focal resource."""
    if not contexts or any(not isinstance(w, Fraction) or w < 0 for w, _ in contexts):
        raise ValueError('nonnegative exact weights required')
    if sum((w for w, _ in contexts), Fraction()) != 1:
        raise ValueError('normalized context law required')
    for _, actors in contexts:
        if not actors or len({a.source for a in actors}) != len(actors):
            raise ValueError('nonempty distinct actual actors required')
        if any(not a.kind or not a.source or type(a.success) is not bool for a in actors):
            raise ValueError('complete binary actor evidence required')
    kinds = sorted({a.kind for _, actors in contexts for a in actors})
    mean = lambda fn: sum((w * fn(actors) for w, actors in contexts), Fraction())
    target = mean(lambda actors: sum(a.success for a in actors))
    rows = {}
    for kind in kinds:
        count = lambda actors: sum(a.kind == kind for a in actors)
        wins = lambda actors: sum(a.success for a in actors if a.kind == kind)
        n = mean(count)
        if n == 0:
            raise ValueError('type has no positive mass')
        pooled = mean(wins) / n
        marked_mass = mean(lambda actors: Fraction(count(actors), len(actors)))
        marked_wins = mean(lambda actors: Fraction(wins(actors), len(actors)))
        sources = {}
        for source in sorted({a.source for _, actors in contexts for a in actors if a.kind == kind}):
            mass = mean(lambda actors: sum(a.kind == kind and a.source == source for a in actors))
            if mass:
                success_mass = mean(lambda actors: sum(a.success for a in actors
                                                       if a.kind == kind and a.source == source))
                sources[source] = {'probability': str(mass / n), 'mean_success': str(success_mass / mass)}
        rows[kind] = {'mean_count': str(n), 'pooled_mean': str(pooled),
                      'context_then_actor_mean': str(marked_wins / marked_mass), 'sources': sources}
    coefficients = {kind: Fraction(row['pooled_mean']) for kind, row in rows.items()}
    prediction = lambda actors: sum((coefficients[a.kind] for a in actors), Fraction())
    return {'types': rows, 'mean_actor_success_count': str(target),
            'pooled_count_prediction_mean': str(mean(prediction)),
            'context_then_actor_prediction_mean': str(sum((Fraction(row['mean_count']) *
                Fraction(row['context_then_actor_mean']) for row in rows.values()), Fraction())),
            'pooled_count_squared_error': str(mean(lambda actors:
                (prediction(actors) - sum(a.success for a in actors)) ** 2))}


def audit():
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen actor-population protocol changed')
    third, half = Fraction(1, 3), Fraction(1, 2)
    fixed = ((third, (Actor('A', 'left', True), Actor('B', 'middle', False))),
             (third, (Actor('A', 'left', True), Actor('B', 'right', True))),
             (third, (Actor('A', 'middle', False), Actor('B', 'right', True))))
    variable = ((half, (Actor('A', 'left', True), Actor('B', 'right', False))),
                (half, (Actor('A', 'left', False), Actor('A', 'middle', False), Actor('B', 'right', True))))
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'scope': 'five abstract contexts; no game or material validation',
            'fixed_inventory': summarize(fixed), 'variable_inventory': summarize(variable)}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result, indent=2))
