"""Exact algebra of a declared task; neither game legality nor material values.

Contexts are observed before selecting an action. Every nonterminal action must
have its complete nonempty adversarial reply set supplied by the caller.
Weights, binary success labels and completeness are assumptions/input evidence,
not facts inferred by this finite fixture.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Action:
    physical_id: str
    replies: tuple[bool, ...]
    complete: bool = True


def context_success(actions: tuple[Action, ...]) -> int:
    """Best guaranteed success, with duplicate physical descriptions unioned."""
    unique: dict[str, tuple[bool, ...]] = {}
    for action in actions:
        if not action.complete or not action.replies:
            raise ValueError('incomplete or empty reply evidence; not task failure')
        if any(type(reply) is not bool for reply in action.replies):
            raise ValueError('binary success evidence required')
        evidence = tuple(sorted(set(action.replies)))
        previous = unique.setdefault(action.physical_id, evidence)
        if previous != evidence:
            raise ValueError('conflicting descriptions of one physical action')
    return int(any(all(replies) for replies in unique.values()))


def task_score(contexts: tuple[tuple[Fraction, tuple[Action, ...]], ...]) -> Fraction:
    """Average local max/min under one explicit, normalized common measure."""
    if not contexts or any(w <= 0 for w, _ in contexts):
        raise ValueError('positive context weights required')
    if sum((w for w, _ in contexts), Fraction()) != 1:
        raise ValueError('weights must sum to one; no hidden renormalization')
    return sum((w * context_success(actions) for w, actions in contexts), Fraction())


def observations() -> dict[str, Fraction]:
    half = Fraction(1, 2)
    yes, no = (True,), (False,)
    a = ((half, (Action('a', yes), Action('b', no))),
         (half, (Action('a', no), Action('b', yes))))
    b = ((half, (Action('broad', yes),)), (half, (Action('broad', yes),)))
    redundant = tuple((w, actions + (Action('losing', no), actions[0])) for w, actions in a)
    before = ((half, (Action('a', yes),)), (half, (Action('a', no),)))
    refuted = ((half, (Action('a', (True, False)), Action('b', no))), a[1])
    return {'context_adaptive_A': task_score(a), 'broad_B': task_score(b),
            'redundant_options': task_score(redundant), 'before_new_success': task_score(before),
            'after_new_success': task_score(a), 'after_refutation': task_score(refuted),
            'wrong_action_average_A': half, 'wrong_max_after_average_A': half}


if __name__ == '__main__':
    import json
    print(json.dumps({key: str(value) for key, value in observations().items()}, indent=2))
