"""Bounded R20 witness for POINTWISE_Q value/search transfer.

The witness reconstructs the fixed R16/R17 child from persisted D0 spectra,
then evaluates only the four frozen seed-620700 openings.  It deliberately
avoids retraining, new roots, full F59 trust spectra, and Arena games.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_gen0_gen1_strength_triage as gen  # noqa: E402
from scripts import f61_strength_first_triage as f61  # noqa: E402


RULESET = "B_CANONICAL_STANDARD_SHOGI"
PARENT_ID = "2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362"
EXPECTED_CHILD_ID = "78bfa7cad9cc21ecfc95fd166566b25d3c954033b413660a7c398498dd6c571b"
EXPECTED_MODEL_SHA = "c6330b17fc11093cd404e204d3a6f461307971f2458e55d0147c4cc21c0f239c"
TRAINING_SEED = 59013
OPENING_SEED = 620700
NODES = 2_000
Q20_NODES = 20_000
TT_MB = 8
OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "pointwise_search_transfer_witness.json"


def _action_key(action: dict) -> str:
    return f59._action_key(action)


def _action_set(compiled, native, parent, child, record: dict) -> tuple[list[dict], dict]:
    session = f59._session(compiled, record)
    legal = sorted(session.legal_actions(), key=lambda a: json.dumps(f59.action_to_dict(a), sort_keys=True))
    cheap = f59._parallel_children(compiled, native, parent, record, [f59.action_to_dict(a) for a in legal], 1_000)
    order = sorted(range(len(legal)), key=lambda i: (-cheap[i], json.dumps(f59.action_to_dict(legal[i]), sort_keys=True)))
    selected = [f59.action_to_dict(legal[i]) for i in order[:6]]
    parent_2k = f59._root_search(compiled, native, parent, record, NODES)
    parent_80k = f59._root_search(compiled, native, parent, record, 80_000)
    child_2k = f59._root_search(compiled, native, child, record, NODES)
    seen = {_action_key(action) for action in selected}
    for payload in (parent_2k["action"], parent_80k["action"], child_2k["action"]):
        if payload is not None and _action_key(payload) not in seen:
            selected.append(payload)
            seen.add(_action_key(payload))
    return selected, {"parent_2k": parent_2k, "parent_80k": parent_80k, "child_2k": child_2k, "legal_action_count": len(legal)}


def _fit_fixed_child(compiled, parent, records):
    roots = []
    for record in records:
        spectrum = gen._load_root_checkpoint(compiled, parent, record, smoke=False)
        if spectrum is None:
            raise RuntimeError(f"missing persisted D0 spectrum for {record['position_key']}")
        usable = [row for row in spectrum if row.q_20k is not None]
        if len(usable) < 2:
            raise RuntimeError("persisted D0 spectrum has fewer than two q20 rows")
        roots.append(usable)
    features = np.vstack([row.features for root in roots for row in root])
    base = np.asarray([row.base_q for root in roots for row in root], dtype=float)
    target = np.asarray([row.q_20k for root in roots for row in root], dtype=float)
    groups = []
    cursor = 0
    for root in roots:
        groups.append(np.arange(cursor, cursor + len(root)))
        cursor += len(root)
    model = f61._fit_serializable(features, base, target, groups, "POINTWISE_Q", TRAINING_SEED)
    spec = {"candidate_id": "F61_D0_POINTWISE_Q_SEED_59013", "training_distribution": "D0_RANDOM_REACHABLE", "objective": "POINTWISE_Q", "seed": TRAINING_SEED}
    child, payload = f61._candidate_checkpoint(parent, compiled, model, spec)
    if child.checkpoint_id != EXPECTED_CHILD_ID or f61.stable_sha256(payload) != EXPECTED_MODEL_SHA:
        raise RuntimeError("fixed R16/R17 child reconstruction identity mismatch")
    return child, len(roots), int(len(features)), f61.stable_sha256(payload)


def _pair_metrics(rows: list[dict], prediction_key: str) -> dict:
    mse = []
    correct = 0
    total = 0
    for row in rows:
        target = np.asarray(row["q20"], dtype=float)
        prediction = np.asarray(row[prediction_key], dtype=float)
        mse.extend((prediction - target).tolist())
        for left in range(len(target)):
            for right in range(left + 1, len(target)):
                delta = np.sign(target[left] - target[right])
                if delta == 0:
                    continue
                total += 1
                correct += int(delta == np.sign(prediction[left] - prediction[right]))
    return {"mse": float(np.mean(np.square(mse))), "pairwise_ranking_accuracy": correct / total if total else 0.0, "comparable_pairs": total}


def _root_regret(row: dict, prediction_key: str) -> dict:
    target = np.asarray(row["q20"], dtype=float)
    prediction = np.asarray(row[prediction_key], dtype=float)
    teacher_index = int(np.argmax(target))
    chosen = int(np.argmax(prediction))
    return {"chosen_action": row["actions"][chosen], "teacher_best_action": row["actions"][teacher_index], "teacher_regret": float(np.max(target) - target[chosen])}


def _mean(values):
    return float(np.mean(np.asarray(values, dtype=float))) if values else 0.0


def main() -> None:
    compiled, native, parent, _ = gen._context(RULESET)
    if parent.checkpoint_id != PARENT_ID:
        raise RuntimeError("unexpected parent checkpoint")
    records = gen._d0_records(compiled, 620000, count=gen.ROOT_COUNT, smoke=False)
    child, root_count, training_actions, model_sha = _fit_fixed_child(compiled, parent, records)
    witness_rows = []
    openings = generate_arena_openings(compiled, count=4, seed=OPENING_SEED, min_plies=2, max_plies=6)
    for opening in openings.openings:
        record = {"action_history": [f59.action_to_dict(action) for action in opening.actions]}
        actions, searches = _action_set(compiled, native, parent, child, record)
        features = []
        base_values = []
        for action in actions:
            feature, base_q, _side = f59._child_features(compiled, native, parent, record, action)
            features.append(feature)
            base_values.append(base_q)
        features = np.vstack(features)
        base_values = np.asarray(base_values, dtype=float)
        q20 = np.asarray(f59._parallel_children(compiled, native, parent, record, actions, Q20_NODES), dtype=float)
        residual = CompactNonlinearResidual.from_dict(child.compact_nonlinear)
        learned_values = base_values + residual.predict(features)
        row = {"opening_id": opening.final_position_key, "actions": actions, "base_q": base_values.tolist(), "learned_total_q": learned_values.tolist(), "q20": q20.tolist(), "parent_2k": searches["parent_2k"], "parent_80k": searches["parent_80k"], "child_2k": searches["child_2k"]}
        row["baseline_regret"] = _root_regret(row, "base_q")
        row["learned_regret"] = _root_regret(row, "learned_total_q")
        row["parent_2k_teacher_regret"] = float(np.max(q20) - q20[next(i for i, action in enumerate(actions) if _action_key(action) == searches["parent_2k"]["action_key"])])
        row["child_2k_teacher_regret"] = float(np.max(q20) - q20[next(i for i, action in enumerate(actions) if _action_key(action) == searches["child_2k"]["action_key"])])
        row["learned_one_ply_teacher_regret"] = row["learned_regret"]["teacher_regret"]
        witness_rows.append(row)
    value = {"baseline": _pair_metrics(witness_rows, "base_q"), "learned": _pair_metrics(witness_rows, "learned_total_q"), "per_root": [{"opening_id": row["opening_id"], "baseline": row["baseline_regret"], "learned": row["learned_regret"]} for row in witness_rows]}
    search = {"per_root": [{"opening_id": row["opening_id"], "parent_2k": {"action": row["parent_2k"]["action"], "teacher_regret": row["parent_2k_teacher_regret"]}, "child_2k": {"action": row["child_2k"]["action"], "teacher_regret": row["child_2k_teacher_regret"]}, "learned_one_ply": {"action": row["learned_regret"]["chosen_action"], "teacher_regret": row["learned_one_ply_teacher_regret"]}} for row in witness_rows], "mean_parent_2k_teacher_regret": _mean([row["parent_2k_teacher_regret"] for row in witness_rows]), "mean_child_2k_teacher_regret": _mean([row["child_2k_teacher_regret"] for row in witness_rows]), "mean_learned_one_ply_teacher_regret": _mean([row["learned_one_ply_teacher_regret"] for row in witness_rows])}
    base = value["baseline"]
    learned = value["learned"]
    root_better = sum(row["learned"]["teacher_regret"] < row["baseline"]["teacher_regret"] for row in value["per_root"])
    root_not_worse = sum(row["learned"]["teacher_regret"] <= row["baseline"]["teacher_regret"] for row in value["per_root"])
    materially_better_value = (
        learned["mse"] < base["mse"]
        and learned["pairwise_ranking_accuracy"] > base["pairwise_ranking_accuracy"]
        and root_better > 0
    )
    if not materially_better_value:
        interpretation = "LEARNING_UPSTREAM_FAILURE"
    elif learned["mse"] < base["mse"] and learned["pairwise_ranking_accuracy"] > base["pairwise_ranking_accuracy"] and search["mean_child_2k_teacher_regret"] > search["mean_learned_one_ply_teacher_regret"] and sum(row["child_2k_teacher_regret"] > row["learned_one_ply_teacher_regret"] for row in witness_rows) >= 3:
        interpretation = "SEARCH_TRANSFER_COUPLING"
    else:
        interpretation = "LOCAL_INTERFACE_EVIDENCE_INCONCLUSIVE"
    payload = {"schema": "generic-chess-f61-pointwise-search-transfer-witness-v1", "ruleset": RULESET, "parent_checkpoint_id": parent.checkpoint_id, "child_checkpoint_id": child.checkpoint_id, "model_sha256": model_sha, "training": {"training_seed": TRAINING_SEED, "training_roots": root_count, "training_actions": training_actions, "persisted_d0_only": True}, "opening_seed": OPENING_SEED, "nodes": NODES, "q20_nodes": Q20_NODES, "tt_megabytes": TT_MB, "witness_count": len(witness_rows), "value_transfer": value, "search_transfer": search, "interpretation": interpretation, "interpretation_counts": {"learned_top_regret_better_roots": root_better, "learned_top_regret_not_worse_roots": root_not_worse}, "witness_rows": witness_rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
