"""Pure WDL proposal arithmetic for the shared AlphaBeta/Receipt runner.

No search is executed here.  Outcomes are actual White-relative terminal
labels (-1/0/+1); None represents an unresolved/censored episode.
"""
from __future__ import annotations

import math
import random
from collections.abc import Sequence


EPISODE_ORDER = (("incumbent", 0), ("proposal", 0),
                 ("proposal", 1), ("incumbent", 1))


def initial_weights(seed: int) -> list[float]:
    rng = random.Random(seed)
    return [1.0] + [rng.uniform(0.5, 1.5) for _ in range(4)]


def propose(weights: Sequence[float], seed: int, round_index: int) -> list[float]:
    if len(weights) != 5 or round_index < 0:
        raise ValueError("expected five weights and a nonnegative round index")
    rng = random.Random(seed * 100000 + round_index + 972568000)
    result = list(weights)
    coordinate = 1 + round_index % 4
    result[coordinate] *= math.exp(rng.uniform(-math.log(2), math.log(2)))
    return result


def reward_bounds(white_outcome: int | None, candidate_color: int) -> tuple[int, int]:
    if candidate_color not in (0, 1):
        raise ValueError("candidate_color must be 0 (White) or 1 (Black)")
    if white_outcome is None:
        return (-1, 1)
    if white_outcome not in (-1, 0, 1):
        raise ValueError("terminal outcome must be -1, 0, +1, or None")
    reward = white_outcome if candidate_color == 0 else -white_outcome
    return (reward, reward)


def paired_interval(rows: Sequence[dict]) -> tuple[float, float] | None:
    """Return proposal-minus-incumbent paired interval; None means incomplete.

    Each row carries variant, color, white_outcome and root_key.  Requiring the
    exact frozen order and one root prevents accidental unpaired acceptance.
    """
    if len(rows) != 4:
        return None
    if tuple((r.get("variant"), r.get("color")) for r in rows) != EPISODE_ORDER:
        raise ValueError("episode rows violate the frozen four-game order")
    if len({r.get("root_key") for r in rows}) != 1:
        raise ValueError("the four episodes must share one opening root")
    bounds = {}
    for row in rows:
        bounds[(row["variant"], row["color"])] = reward_bounds(
            row.get("white_outcome"), row["color"]
        )
    lo = sum(bounds[("proposal", c)][0] - bounds[("incumbent", c)][1]
             for c in (0, 1)) / 2
    hi = sum(bounds[("proposal", c)][1] - bounds[("incumbent", c)][0]
             for c in (0, 1)) / 2
    return (lo, hi)


def accept_proposal(rows: Sequence[dict]) -> tuple[bool, tuple[float, float] | None]:
    interval = paired_interval(rows)
    return (interval is not None and interval[0] > 0, interval)


def charge_nodes(candidate_nodes: int, foe_nodes: int, actor_is_candidate: bool,
                 newly_searched: int, arm_cap: int) -> tuple[int, int]:
    """Charge each Receipt to the same combined per-arm node budget."""
    if min(candidate_nodes, foe_nodes, newly_searched) < 0 or arm_cap < 0:
        raise ValueError("node counts and cap must be nonnegative")
    candidate_nodes += newly_searched if actor_is_candidate else 0
    foe_nodes += 0 if actor_is_candidate else newly_searched
    if candidate_nodes + foe_nodes > arm_cap:
        raise ValueError("receipt exceeds the combined candidate-plus-foe cap")
    return candidate_nodes, foe_nodes
