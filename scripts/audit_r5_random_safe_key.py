"""Bound exact R5 random-policy computation with the core search identity."""

import hashlib
import json
from pathlib import Path
import sys
from time import monotonic


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import search_state_identity
from generic_chess.core.transition import legal_successors
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23n_preference_corpus_r5 as f23n


FIXTURE = ROOT / "tests/fixtures/evaluator_v2_corpus_v7.json"
EXPECTED_SHA = "57d0d40ad4e74815ca1c542c2fa680750ea8a6411e47249a3892f23954dd064b"
ROOT_ID = "generic-f23n-legacy_capture_recapture-2"
MAX_STATES = 10_000
MAX_SECONDS = 5


class BudgetExceeded(Exception):
    pass


def audit():
    if hashlib.sha256(FIXTURE.read_bytes()).hexdigest() != EXPECTED_SHA:
        raise RuntimeError("frozen R5 fixture changed")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    exact = next(row for row in fixture["effective_preference_representatives"]
                 if row["id"] == ROOT_ID)
    assert exact["planned_split"] == "DEVELOPMENT"
    plan = f23n._plan_entry(exact["construction_family"])
    compiled, root = f23n._build_candidate(
        f23c._imports(), plan, tuple(exact["parameter"])
    )
    assert compiled.repetition_policy == "draw"
    labels = {json.dumps(row["action"], sort_keys=True): row["value"]
              for row in exact["root_action_values"]}
    losing = [(action, child) for action, child in legal_successors(root, compiled)
              if labels[json.dumps(action_to_dict(action), sort_keys=True)] == "LOSS"]
    assert len(losing) == 1
    started = monotonic()
    cache = {}
    hits = 0
    root_actor = root.position.side_to_move

    def distribution(state):
        nonlocal hits
        if monotonic() - started > MAX_SECONDS:
            raise BudgetExceeded("seconds")
        key = search_state_identity(state, compiled)
        if key in cache:
            hits += 1
            return cache[key]
        if len(cache) >= MAX_STATES:
            raise BudgetExceeded("states")
        # Reserve this identity before recursing; max_ply makes cycles finite.
        cache[key] = None
        terminal = state.terminal_status
        if terminal.status.value != "ongoing":
            value = 0 if terminal.winner is None else (
                1 if terminal.winner == root_actor else -1
            )
            result = (float(value == 1), float(value == 0), float(value == -1))
        else:
            children = legal_successors(state, compiled)
            assert children
            rows = [distribution(child) for _, child in children]
            result = tuple(sum(row[i] for row in rows) / len(rows) for i in range(3))
        cache[key] = result
        return result

    try:
        probabilities = distribution(losing[0][1])
        classification = "COMPLETE"
        abort_reason = None
    except BudgetExceeded as exc:
        probabilities = None
        classification = "COST_ABORT"
        abort_reason = str(exc)
    return {"classification": classification, "abort_reason": abort_reason,
            "root_id": ROOT_ID, "action": action_to_dict(losing[0][0]),
            "random_outcome_probabilities_win_draw_loss": probabilities,
            "state_identities_seen": len(cache), "cache_hits": hits,
            "max_states": MAX_STATES, "max_seconds": MAX_SECONDS,
            "elapsed_seconds": monotonic() - started}


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
