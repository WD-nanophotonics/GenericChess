"""Certificate-only scoring for literal full-history Leaper quality controls.

Source-graph labels remain separately attributed. No Player, solver, training,
Core transition or archived-code execution occurs in this consumer.
"""
from __future__ import annotations

import json
from collections import Counter


def _action_key(action: dict) -> str:
    if not isinstance(action, dict) or not action:
        raise ValueError("a nonempty public action record is required")
    return json.dumps(action, sort_keys=True, separators=(",", ":"))


def classify_certified_choice(control: dict, action: dict, *, root_state_sha256: str) -> dict:
    """Score only certified actions at the exact ROOT, with explicit abstention.

    The caller separately validates legality with the complete rule/history.
    A proof's source_parent_id is never a substitute for its actual root hash.
    A named losing action alone does not prove it inferior: the game may be
    lost regardless. A certified draw likewise need not be globally optimal.
    """
    if root_state_sha256 != control["root_state_sha256"]:
        raise ValueError("query root does not match the literal certified history")
    labels = {}
    for row in control["certified_actions"]:
        value = row["own_WDL"]
        if type(value) is not int or value not in (-1, 0, 1):
            raise ValueError("certificate WDL must be integer -1/0/1")
        key = _action_key(row["action"])
        if key in labels and labels[key] != value:
            raise ValueError("conflicting certified values for one action")
        labels[key] = value
    lower = max(labels.values(), default=-1)
    upper = control.get("certified_root_upper_WDL", 1)
    if type(upper) is not int or upper not in (-1, 0, 1):
        raise ValueError("certified root upper bound must be integer -1/0/1")
    if upper < lower:
        raise ValueError("root upper bound contradicts a certified action value")
    value = labels.get(_action_key(action))
    if value is None:
        category = "UNCERTIFIED_ACTION"
    elif value < lower:
        category = "CERTIFIED_INFERIOR"
    elif value == upper:
        category = "CERTIFIED_OPTIMAL"
    elif value == 0:
        category = "CERTIFIED_DRAW_OPTIMALITY_UNKNOWN"
    else:
        category = "CERTIFIED_LOSS_OPTIMALITY_UNKNOWN"
    return dict(category=category, chosen_own_WDL=value,
                root_own_WDL_interval=[lower, upper],
                known_action_value=value is not None,
                guaranteed_WDL_gap=max(0, lower-value) if value is not None else None,
                label_scope="certificate_only; source_graph_values_not_used")


def summarize_certified_choices(control: dict, returns: list[dict]) -> dict:
    """Keep ALL returned actions in the coverage denominator, including unknowns.

    This is a conditional descriptive ledger, not whole-root accuracy or Elo.
    No synthetic draw/loss is assigned to a missing return or unlabelled action.
    """
    rows = [classify_certified_choice(control, r["action"],
            root_state_sha256=r["root_state_sha256"]) for r in returns]
    counts = Counter(r["category"] for r in rows)
    known = sum(r["known_action_value"] for r in rows)
    return dict(returned_actions=len(rows), certified_value_returns=known,
                uncertified_value_returns=len(rows)-known,
                certified_value_coverage=(known/len(rows) if rows else None),
                categories=dict(counts), rows=rows,
                scope="all returned actions retained; not accuracy on a selected known subset")
