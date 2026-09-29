"""Bounded random-action terminal rollouts on a frozen R5 development root."""

from collections import Counter
import hashlib
import json
from pathlib import Path
from random import Random
import sys
from time import monotonic


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action, legal_successors
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23n_preference_corpus_r5 as f23n


FIXTURE = ROOT / "tests/fixtures/evaluator_v2_corpus_v7.json"
EXPECTED_SHA = "57d0d40ad4e74815ca1c542c2fa680750ea8a6411e47249a3892f23954dd064b"
ROOT_ID = "generic-f23n-legacy_capture_recapture-2"
SEED = 20260929
SAMPLES_PER_ACTION = 100
MAX_ACTIONS = 5_000
MAX_SECONDS = 10


def action_key(action):
    return json.dumps(action_to_dict(action), sort_keys=True)


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
    labels = {json.dumps(row["action"], sort_keys=True): row["value"]
              for row in exact["root_action_values"]}
    children = sorted(((action_key(action), child)
                       for action, child in legal_successors(root, compiled)),
                      key=lambda row: row[0])
    assert set(labels) == {key for key, _ in children}
    rng = Random(SEED)
    started = monotonic()
    actions_seen = 0
    results = {}
    for key, child in children:
        outcomes = Counter()
        statuses = Counter()
        for _ in range(SAMPLES_PER_ACTION):
            state = child
            while state.terminal_status.status.value == "ongoing":
                if actions_seen >= MAX_ACTIONS or monotonic() - started > MAX_SECONDS:
                    raise TimeoutError("R5 random-continuation budget exceeded")
                options = legal_actions(state, compiled)
                assert options
                state = apply_action(state, rng.choice(options), compiled)
                actions_seen += 1
            result = state.terminal_status
            statuses[result.status.value] += 1
            value = 0 if result.winner is None else (1 if result.winner == 0 else -1)
            outcomes[value] += 1
        results[key] = {"exact_minimax": labels[key],
                        "random_wins": outcomes[1],
                        "random_draws": outcomes[0],
                        "random_losses": outcomes[-1],
                        "terminal_status_counts": dict(sorted(statuses.items())),
                        "random_mean": (outcomes[1] - outcomes[-1]) / SAMPLES_PER_ACTION}
    return {"root_id": ROOT_ID, "seed": SEED,
            "samples_per_action": SAMPLES_PER_ACTION,
            "actions_applied": actions_seen, "elapsed_seconds": monotonic() - started,
            "results": results}


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
