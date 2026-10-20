"""Read only initial fixed-scale material features for task2633 candidates."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

TASK = ROOT / "results/dev_aux/task2634"
PLAN = json.loads((TASK / "plan.json").read_text(encoding="utf-8"))
OUT = TASK / "static-initial-features.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> dict:
    candidate_index_path = ROOT / PLAN["candidate_index"]
    candidate_index_raw = candidate_index_path.read_bytes()
    if sha(candidate_index_raw) != PLAN["candidate_index_sha256"]:
        raise ValueError("candidate index changed after static plan freeze")
    for rel, expected in PLAN["source_sha256"].items():
        if sha((ROOT / rel).read_bytes()) != expected:
            raise ValueError(f"pinned adapter/source changed: {rel}")

    index = json.loads(candidate_index_raw)
    if len(index["rows"]) != PLAN["candidate_count"]:
        raise ValueError("candidate count changed after plan freeze")
    rows = []
    for candidate in index["rows"]:
        rules_path = ROOT / candidate["source_file"]
        raw = rules_path.read_bytes()
        if sha(raw) != candidate["ruleset_sha256"]:
            raise ValueError(f"candidate rule hash changed: {rules_path}")
        ruleset = deserialize_ruleset(raw.decode("utf-8"))
        compiled = compile_ruleset_for_execution(ruleset)
        env = FixedScaleSessionEnv(GameSession(compiled), unit_type=PLAN["unit_type"])
        # Intentionally do not call actions(), push(), terminal(), replay(), or
        # construct/update a learner/model. Only inspect initial channels/input.
        features = tuple(env.features())
        names = tuple(env.names)
        if len(features) != len(names):
            raise AssertionError("adapter channel and feature dimensions differ")
        position = env.session.state.position
        direct_counts = []
        for kind, type_id in names:
            if kind == "board":
                value = sum(
                    (1 if piece.owner == 0 else -1)
                    for piece in position.board
                    if piece is not None and piece.current_type_id == type_id
                )
            elif kind == "hand":
                value = position.hands[0].count(type_id) - position.hands[1].count(type_id)
            else:
                raise AssertionError(f"unexpected adapter channel kind: {kind}")
            direct_counts.append(value)
        if tuple(direct_counts) != features:
            raise AssertionError("adapter vector disagrees with direct board/hand count reconstruction")
        rows.append({
            "seed": ruleset.metadata.get("seed") if ruleset.metadata else None,
            "ruleset_sha256": sha(raw),
            "channels": [list(name) for name in names],
            "initial_features": list(features),
            "direct_count_reconstruction_matches": True,
            "all_initial_features_zero": all(value == 0 for value in features),
        })

    channel_orders = {tuple(tuple(name) for name in row["channels"]) for row in rows}
    feature_vectors = {tuple(row["initial_features"]) for row in rows}
    if len(rows) != PLAN["candidate_count"]:
        raise AssertionError("not all candidates were audited")
    result = {
        "status": "COMPLETE",
        "plan_sha256": sha((TASK / "plan.json").read_bytes()),
        "candidate_index_sha256": sha(candidate_index_raw),
        "candidate_count": len(rows),
        "unique_channel_orders": len(channel_orders),
        "unique_initial_feature_vectors": len(feature_vectors),
        "all_initial_feature_vectors_zero": all(row["all_initial_features_zero"] for row in rows),
        "all_direct_count_reconstructions_match": all(row["direct_count_reconstruction_matches"] for row in rows),
        "channel_order": [list(name) for name in rows[0]["channels"]] if rows else [],
        "scope": "Static initial adapter input only. No actions, playout, outcomes, search, model/learner construction or update, training, evaluation, or root admission.",
        "rows": rows,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    return result


if __name__ == "__main__":
    main()
