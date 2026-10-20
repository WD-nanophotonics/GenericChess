"""Write-once, outcome-blind preregistration for the task2618 comparison.

Registration freezes exact task2619 roots, methods, endpoints, runtime/source
pins and caps. It performs rule-history replay only; it never runs a search.
"""
from __future__ import annotations

import datetime
import argparse
import hashlib
import json
import random
from pathlib import Path

import chess

from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2565.train import restore
from results.dev_aux.task2618.train_learners import METHODS
from results.dev_aux.task2618.wdl_receipt_adapter import EPISODE_ORDER, initial_weights


ROOT = Path(__file__).resolve().parents[3]
RUN_ROOT = ROOT / "results/dev_aux/task2618"
RUNS = {
    1: RUN_ROOT / "learner-comparison-v1",
    2: RUN_ROOT / "learner-comparison-v2",
    3: RUN_ROOT / "learner-comparison-v3",
}
RUN = RUNS[1]
V2_ROOT_SELECTION = RUN_ROOT / "learner-comparison-v2-prep-verified/root-selection.json"
V3_ROOT_SELECTION = RUN_ROOT / "learner-comparison-v3-prep/root-selection.json"
AUDIT_PATH = ROOT / "results/dev_aux/task2618/learning-input-audit-v2.json"
TRAIN_PATH = ROOT / "results/dev_aux/task2619/prospective-training-roots.json"
EVAL_PATH = ROOT / "results/dev_aux/task2619/prospective-evaluation-roots.json"
FEASIBILITY_PATH = ROOT / "results/dev_aux/task2618/feasibility.json"
SEED_NAMESPACE = "DEV_AUX_TASK2618_CHESS_TREESTRAP_V1_SEED_{}"
CAP_NAMESPACE = "DEV_AUX_TASK2618_EVAL_FAMILY_CAP_V1"

SOURCE_PATHS = (
    "results/dev_aux/task2618/register_learners.py",
    "results/dev_aux/task2618/train_learners.py",
    "results/dev_aux/task2618/evaluate_learners.py",
    "results/dev_aux/task2618/analyze_learners.py",
    "results/dev_aux/task2618/wdl_receipt_adapter.py",
    "results/dev_aux/task2618/feasibility.py",
    "results/dev_aux/task2618/audit_learning_protocol_inputs.py",
    "results/dev_aux/task2618/reselect_training_roots.py",
    "results/dev_aux/task2618/reselect_training_roots_v3.py",
    "results/dev_aux/task2619/root_feasibility.py",
    "results/dev_aux/task2392/reader.py",
    "results/dev_aux/task2153/stop_evidence.py",
    "results/dev_aux/task109/adapter.py",
    "results/dev_aux/task2492/adapters.py",
    "results/dev_aux/task2492/episode.py",
    "results/dev_aux/task2492/learning.py",
    "results/dev_aux/task2504/search.py",
    "results/dev_aux/task2565/train.py",
)

TRAIN_OUTPUTS = (
    "started.json", "queries.jsonl", "games.jsonl", "proposal-blocks.jsonl", "arm-progress.jsonl",
    "training-result.json", "evaluation-started.json", "evaluation-games.jsonl",
    "evaluation-queries.jsonl", "evaluation-result.json", "analysis.json",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def record_set_digest(rows: list[dict]) -> str:
    return sha(b"\n".join(canonical(row["record"]) for row in rows))


def training_source_index(revision: int, seed_index: int, root_index: int,
                         selected_indices: list[int]) -> int:
    if revision in (2, 3):
        offset = root_index
    elif revision == 1:
        offset = seed_index * 120 + root_index
    else:
        raise ValueError("unsupported task2618 registration revision")
    if not 0 <= offset < len(selected_indices):
        raise ValueError("training manifest source index is out of range")
    return selected_indices[offset]


def derived_seed(namespace: str) -> int:
    return int.from_bytes(hashlib.sha256(namespace.encode("utf-8")).digest()[:4], "big") & 0x7FFFFFFF


def family_caps(families: list[int], seed: int) -> tuple[dict[str, int], list[int]]:
    if len(families) != 32 or len(set(families)) != 32:
        raise ValueError("the frozen evaluation panel requires 32 unique families")
    ordered = list(families)
    random.Random(seed).shuffle(ordered)
    caps = {str(family): (20_000 if index < 16 else 40_000)
            for index, family in enumerate(ordered)}
    return caps, ordered


def _write_once(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()


def _read_json(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value, raw


def _check_role_session() -> tuple[dict, dict]:
    session, _ = _read_json(ROOT / ".local_agent/session.json")
    role, _ = _read_json(ROOT / ".local_agent/role.json")
    if session.get("state") != "active" or session.get("thread_id") != "01a128cf-ae2d-7352-a456-06bd38367221":
        raise ValueError("registration requires the active DEV_AUX research segment")
    if role.get("role") != "DEV_AUX" or role.get("branch") != "sidemission":
        raise ValueError("registration must run in DEV_AUX/sidemission")
    return session, role


def _verify_roots(rows: list[dict], *, expected_count: int, label: str) -> None:
    if len(rows) != expected_count:
        raise ValueError(f"{label} root count {len(rows)} != {expected_count}")
    seen_families: set[int] = set()
    for index, row in enumerate(rows):
        record = row.get("record")
        family = row.get("family")
        if not isinstance(record, dict) or not isinstance(family, int) or family in seen_families:
            raise ValueError(f"malformed or duplicate {label} root at index {index}")
        seen_families.add(family)
        record_bytes = canonical(record)
        if row.get("record_sha256") != sha(record_bytes):
            raise ValueError(f"{label} root record hash mismatch at index {index}")
        if len(record.get("moves", ())) != 8:
            raise ValueError(f"{label} root is not an eight-ply complete history at index {index}")
        env = restore(0, None, record)
        if env.record() != record or env.terminal() is not None:
            raise ValueError(f"{label} exact-history replay failed at index {index}")


def _load_inputs() -> tuple[dict, dict, dict, dict, dict]:
    audit, audit_raw = _read_json(AUDIT_PATH)
    train_doc, train_raw = _read_json(TRAIN_PATH)
    eval_doc, eval_raw = _read_json(EVAL_PATH)
    feasibility, feasibility_raw = _read_json(FEASIBILITY_PATH)
    if audit.get("status") != "PREPARATION_AUDIT_ONLY_NOT_REGISTERED":
        raise ValueError("the input audit is not the expected preparation audit")
    if audit.get("registration_or_launch_authorized") is not False or audit.get("search_or_outcome_access") is not False:
        raise ValueError("input audit crossed the pre-search/outcome boundary")
    if feasibility.get("status") != "FEASIBILITY_ONLY":
        raise ValueError("task2618 feasibility is not a cost-only estimate")
    if feasibility.get("threshold_assessment") != "BELOW_120_MINUTES":
        raise ValueError("the registered run requires a Chat necessity assessment")
    if feasibility.get("estimate_with_margin_and_reserve_seconds", 1e99) >= 7_200:
        raise ValueError("the estimated run reaches the 120-minute Chat threshold")
    for key, path, raw in (
        ("task2619_training_roots", TRAIN_PATH, train_raw),
        ("task2619_evaluation_roots", EVAL_PATH, eval_raw),
    ):
        pin = audit.get("sources", {}).get(key, {})
        if pin.get("path") != path.relative_to(ROOT).as_posix() or pin.get("sha256") != sha(raw):
            raise ValueError(f"task2619 root source no longer matches the input audit: {key}")
    if train_doc.get("task") != "DEV_AUX2619":
        raise ValueError("unexpected training-root manifest")
    if eval_doc.get("task") != "DEV_AUX2619":
        raise ValueError("unexpected evaluation-root manifest")
    if chess.__version__ != audit.get("python_chess_version"):
        raise ValueError("python-chess runtime differs from the input audit")
    return audit, train_doc, eval_doc, feasibility, {
        "audit": audit_raw, "training_roots": train_raw,
        "evaluation_roots": eval_raw, "feasibility": feasibility_raw,
    }


def build_registration(session: dict, revision: int = 1) -> tuple[dict, dict, dict, dict]:
    audit, train_doc, eval_doc, feasibility, input_raw = _load_inputs()
    selection = audit["selection"]
    seeds = audit["seed_schedule"]["seeds"]
    train_source_rows = train_doc["roots"]
    eval_source_rows = eval_doc["roots"]
    evaluation_rows = eval_source_rows
    if revision == 1:
        train_start, train_end = selection["training_root_indices_remaining"]
        training_rows = train_source_rows[train_start:train_end]
        if len(training_rows) != 480:
            raise ValueError("audited v1 seed/root count differs from the frozen design")
        if train_end - train_start != selection["training_root_count_remaining"]:
            raise ValueError("training root index range disagrees with the outcome-blind audit")
        if len(seeds) * selection["training_roots_per_seed_if_four_seed_design"] != len(training_rows):
            raise ValueError("training roots do not divide evenly across seeds")
        training_source = {
            "path": TRAIN_PATH.relative_to(ROOT).as_posix(),
            "sha256": input_raw["training_roots"],
            "indices": [train_start, train_end],
            "exact_selected_records_sha256": record_set_digest(training_rows),
            "excluded_cost_only_indices": selection["cost_only_training_root_indices_excluded"],
            "family_range": selection["training_family_range"],
            "shared_across_seeds": False,
        }
        selected_indices = list(range(train_start, train_end))
    elif revision == 2:
        selection_raw = V2_ROOT_SELECTION.read_bytes()
        panel = json.loads(selection_raw)
        if panel.get("task") != "DEV_AUX2618_CHESS_LEARNER_COMPARISON_V2_ROOT_PANEL" or panel.get("status") != "PREPARATION_ONLY_NOT_REGISTERED":
            raise ValueError("v2 root panel is not the expected preparation artifact")
        if panel.get("search_started") is not False or panel.get("outcome_fields_used_for_selection"):
            raise ValueError("v2 root panel accessed outcomes or search")
        source_paths = {
            "training_roots_sha256": TRAIN_PATH,
            "evaluation_roots_sha256": EVAL_PATH,
            "input_audit_sha256": AUDIT_PATH,
            "root_selector_source_sha256": ROOT / "results/dev_aux/task2618/reselect_training_roots.py",
            "v1_games_exposure_file_sha256": RUN / "games.jsonl",
        }
        for key, path in source_paths.items():
            if sha(path.read_bytes()) != panel.get("sources", {}).get(key):
                raise ValueError(f"v2 panel source changed: {key}")
        if panel.get("eligible_unexposed_count") != 429 or panel.get("panel_size") != 120:
            raise ValueError("v2 selected panel counts changed")
        training_rows = panel.get("roots", [])
        if len(training_rows) != 120:
            raise ValueError("v2 root panel must contain exactly 120 roots")
        exposed = set(panel.get("exposed_family_ids_excluded", []))
        if any(row.get("family") in exposed for row in training_rows):
            raise ValueError("v2 root panel includes a v1-exposed family")
        if record_set_digest(training_rows) != panel.get("selected_exact_record_set_sha256"):
            raise ValueError("v2 selected record-set hash mismatch")
        _verify_roots(training_rows, expected_count=120, label="v2 training")
        training_source = {
            "path": V2_ROOT_SELECTION.relative_to(ROOT).as_posix(),
            "sha256": sha(selection_raw),
            "selected_exact_record_set_sha256": panel["selected_exact_record_set_sha256"],
            "selection_seed": panel["selection_seed"],
            "selection_seed_namespace": panel["selection_seed_namespace"],
            "eligible_unexposed_count": panel["eligible_unexposed_count"],
            "exposed_family_ids_excluded": panel["exposed_family_ids_excluded"],
            "shared_across_seeds": True,
        }
        selected_indices = list(range(len(training_rows)))
    elif revision == 3:
        selection_raw = V3_ROOT_SELECTION.read_bytes()
        panel = json.loads(selection_raw)
        if panel.get("task") != "DEV_AUX2618_CHESS_LEARNER_COMPARISON_V3_ROOT_PANEL" or panel.get("status") != "PREPARATION_ONLY_NOT_REGISTERED":
            raise ValueError("v3 root panel is not the expected preparation artifact")
        if panel.get("search_started") is not False or panel.get("outcome_fields_used_for_selection"):
            raise ValueError("v3 root panel accessed outcomes or search")
        source_paths = {
            "training_roots_sha256": TRAIN_PATH,
            "evaluation_roots_sha256": EVAL_PATH,
            "input_audit_sha256": AUDIT_PATH,
            "v2_registered_plan_sha256": RUNS[2] / "plan.json",
            "root_selector_source_sha256": ROOT / "results/dev_aux/task2618/reselect_training_roots_v3.py",
        }
        for key, path in source_paths.items():
            if sha(path.read_bytes()) != panel.get("sources", {}).get(key):
                raise ValueError(f"v3 panel source changed: {key}")
        if panel.get("eligible_remaining_count") != 360 or panel.get("panel_size") != 120:
            raise ValueError("v3 selected panel counts changed")
        training_rows = panel.get("roots", [])
        if len(training_rows) != 120:
            raise ValueError("v3 root panel must contain exactly 120 roots")
        excluded = set(panel.get("registered_v2_panel_families_excluded", []))
        if len(excluded) != 120 or any(row.get("family") in excluded for row in training_rows):
            raise ValueError("v3 root panel intersects or mismatches the registered v2 panel")
        if record_set_digest(training_rows) != panel.get("selected_exact_record_set_sha256"):
            raise ValueError("v3 selected record-set hash mismatch")
        _verify_roots(training_rows, expected_count=120, label="v3 training")
        training_source = {
            "path": V3_ROOT_SELECTION.relative_to(ROOT).as_posix(),
            "sha256": sha(selection_raw),
            "selected_exact_record_set_sha256": panel["selected_exact_record_set_sha256"],
            "selection_seed": panel["selection_seed"],
            "selection_seed_namespace": panel["selection_seed_namespace"],
            "eligible_remaining_count": panel["eligible_remaining_count"],
            "registered_v2_panel_families_excluded": panel["registered_v2_panel_families_excluded"],
            "shared_across_seeds": True,
        }
        selected_indices = list(range(len(training_rows)))
    else:
        raise ValueError("unsupported task2618 registration revision")
    if len(seeds) != 4 or len(evaluation_rows) != 32:
        raise ValueError("seed/evaluation root counts differ from the frozen design")
    _verify_roots(evaluation_rows, expected_count=32, label="evaluation")
    train_keys = {canonical(row["record"]) for row in training_rows}
    eval_keys = {canonical(row["record"]) for row in evaluation_rows}
    if train_keys & eval_keys:
        raise ValueError("exact full-history training/evaluation root overlap")
    train_hash = record_set_digest(training_rows)
    eval_hash = record_set_digest(evaluation_rows)
    if revision == 1 and train_hash != selection["training_root_records_sha256"]:
        raise ValueError("selected training-root records differ from the audited exact set")
    if eval_hash != selection["evaluation_root_records_sha256"]:
        raise ValueError("selected evaluation-root records differ from the audited exact set")

    cap_seed = derived_seed(CAP_NAMESPACE)
    families = [row["family"] for row in evaluation_rows]
    caps, cap_order = family_caps(families, cap_seed)
    methods = list(METHODS)
    endpoints = ["initial", *methods]
    ordered_slots = [
        [seed_index, seed, root["family"], color, endpoint]
        for root in evaluation_rows
        for seed_index, seed in enumerate(seeds)
        for color in (0, 1)
        for endpoint in endpoints
    ]
    if len(ordered_slots) != 1_024 or len(set(tuple(slot) for slot in ordered_slots)) != 1_024:
        raise ValueError("evaluation slot panel is not exactly 1,024 unique slots")

    source_hashes = {path: sha((ROOT / path).read_bytes()) for path in SOURCE_PATHS}
    plan = {
        "task": "DEV_AUX2618_CHESS_LEARNER_COMPARISON",
        "design_revision": revision,
        "status": "FROZEN_BEFORE_SEARCH",
        "registered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "session_id": session["id"],
        "segment_started_at": session["started_at"],
        "methods": methods,
        "seeds": seeds,
        "seed_count": len(seeds),
        "roots_per_seed": len(training_rows) if revision == 1 else 120,
        "training_root_selection": training_source,
        "training_families": [row["family"] for row in training_rows],
        "evaluation_root_selection": {
            "path": EVAL_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha(input_raw["evaluation_roots"]),
            "exact_selected_records_sha256": eval_hash,
            "root_count": len(evaluation_rows),
        },
        "input_audit": {
            "path": AUDIT_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha(input_raw["audit"]),
            "claim_scope": audit["claims_limited_to"],
        },
        "feasibility": {
            "path": FEASIBILITY_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha(input_raw["feasibility"]),
            "estimate_seconds": feasibility["estimate_with_margin_and_reserve_seconds"],
            "estimate_minutes": feasibility["estimate_minutes"],
            "interpretation": "Planning estimate only; not a runtime guarantee.",
        },
        "arm_order": [[seed_index, method] for seed_index in range(len(seeds)) for method in methods],
        "episode_order": [list(item) for item in EPISODE_ORDER],
        "candidate_initial_weights_by_seed": {
            str(seed): initial_weights(seed) for seed in seeds
        },
        "learner_parameters": {
            "TreeStrap": {"eta": 0.05, "target": "one-sided AlphaBeta interval semi-gradient"},
            "TDLeaf": {"eta": 0.05, "lambda": 0.95, "target": "complete candidate episodes only"},
            "WDL": {"proposal": "task2618 multiplicative coordinate proposal", "acceptance": "strict positive paired finite reward interval"},
        },
        "fixed_foe_weights": [1.0, 1.0, 1.0, 1.0, 1.0],
        "search": {"training": "task2612 AlphaBeta/Receipt", "depth": 2, "qdepth": 0},
        "nodes_per_seed_method_arm": 1_000_000,
        "max_nodes_per_search": 8_192,
        "seconds_per_search_cap": 2.0,
        "max_plies_per_game": 512,
        "ordering_seed_base": 972_568_000,
        "training_hard_cap_seconds": 2_100,
        "evaluation": {
            "depth": 2,
            "q_limit": 2,
            "root_count": 32,
            "expected_slots": 1_024,
            "ordered_slots": ordered_slots,
            "cap_values_nodes_both_sides": [20_000, 40_000],
            "cap_randomization_seed": cap_seed,
            "cap_assignment_order": cap_order,
            "caps_by_family": caps,
            "nodes_per_search": 8_192,
            "seconds_per_search": 2.0,
            "max_plies_per_game": 512,
            "ordering_seed_base": 972_568_000,
            "hard_cap_seconds": 3_600,
        },
        "setup_audit_reserve_seconds": 900,
        "all_in_hard_cap_seconds": 6_600,
        "cost_accounting": "Charge all candidate and fixed-foe nodes, including incomplete/partial searches, to the registered arm/panel caps.",
        "unknown_policy": "Actual terminal Chess W/D/L only; unresolved or unstarted slots retain full [-1,+1] reward bounds and are never imputed as draws.",
        "evaluation_endpoint_order": endpoints,
        "evaluation_contrasts": "All paired finite-panel contrasts across initial, TreeStrap, TDLeaf and WDL over the fixed 256 (seed,family,color) matches; no CI or population claim.",
        "source_sha256": source_hashes,
        "python_chess_version": chess.__version__,
        "search_or_outcome_access_during_registration": False,
    }
    training_manifest = {
        "status": "FROZEN_BEFORE_TRAINING",
        "source_path": training_source["path"],
        "source_sha256": training_source["sha256"],
        "selected_indices": selected_indices,
        "shared_panel_across_seeds": revision in (2, 3),
        "seed_blocks": [
            {"seed_index": index, "seed": seed,
             "families": [row["family"] for row in (
                 training_rows if revision in (2, 3) else training_rows[index * 120:(index + 1) * 120]
             )]}
            for index, seed in enumerate(seeds)
        ],
        "roots": [
            {"seed_index": seed_index, "seed": seed,
             "source_index": training_source_index(revision, seed_index, index, selected_indices), **row}
            for seed_index, seed in enumerate(seeds)
            for index, row in enumerate(
                training_rows if revision in (2, 3) else training_rows[seed_index * 120:(seed_index + 1) * 120]
            )
        ],
    }
    eval_manifest = {
        "status": "FROZEN_BEFORE_TRAINING",
        "source_path": EVAL_PATH.relative_to(ROOT).as_posix(),
        "source_sha256": sha(input_raw["evaluation_roots"]),
        "roots": evaluation_rows,
    }
    return plan, training_manifest, eval_manifest, source_hashes


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def preflight(run_dir: Path | None = None) -> dict:
    run_dir = RUN if run_dir is None else run_dir
    required = ("plan.json", "registration.json", "root-manifest.json", "evaluation-root-manifest.json")
    if any(not (run_dir / name).is_file() for name in required):
        raise FileNotFoundError("learner comparison registration is incomplete")
    plan_raw = (run_dir / "plan.json").read_bytes()
    registration, _ = _read_json(run_dir / "registration.json")
    train_manifest_raw = (run_dir / "root-manifest.json").read_bytes()
    eval_manifest_raw = (run_dir / "evaluation-root-manifest.json").read_bytes()
    plan = json.loads(plan_raw)
    if registration.get("status") != "REGISTERED_PRE_TRAINING" or registration.get("search_started") is not False:
        raise ValueError("registration is not a pre-search registration")
    if registration.get("plan_sha256") != sha(plan_raw):
        raise ValueError("registered plan hash mismatch")
    if registration.get("root_manifest_sha256") != sha(train_manifest_raw):
        raise ValueError("training root manifest hash mismatch")
    if registration.get("evaluation_root_manifest_sha256") != sha(eval_manifest_raw):
        raise ValueError("evaluation root manifest hash mismatch")
    if plan.get("status") != "FROZEN_BEFORE_SEARCH" or plan.get("task") != "DEV_AUX2618_CHESS_LEARNER_COMPARISON":
        raise ValueError("unexpected task plan")
    if len(plan.get("arm_order", [])) != 12 or len(plan.get("evaluation", {}).get("ordered_slots", [])) != 1_024:
        raise ValueError("registered plan has incomplete arms or evaluation slots")
    for relative, expected in plan["source_sha256"].items():
        if sha((ROOT / relative).read_bytes()) != expected:
            raise ValueError(f"registered source changed: {relative}")
    if any((run_dir / name).exists() for name in TRAIN_OUTPUTS):
        raise FileExistsError("a search output exists beside this pre-search registration")
    session, _ = _check_role_session()
    if session.get("id") != plan.get("session_id") or chess.__version__ != plan.get("python_chess_version"):
        raise ValueError("session or python-chess runtime differs from registration")
    return {"status": "PRE_SEARCH_PREFLIGHT_PASS", "plan_sha256": sha(plan_raw),
            "training_root_count": len(json.loads(train_manifest_raw)["roots"]),
            "evaluation_root_count": len(json.loads(eval_manifest_raw)["roots"]),
            "arm_count": len(plan["arm_order"]),
            "evaluation_slot_count": len(plan["evaluation"]["ordered_slots"]),
            "search_started": False}


def register(revision: int = 1, run_dir: Path | None = None) -> dict:
    if revision not in RUNS:
        raise ValueError("unsupported task2618 registration revision")
    run_dir = RUNS[revision] if run_dir is None else run_dir
    stop = SharedDeleteStopReader(ROOT)
    stop()
    session, _ = _check_role_session()
    if run_dir.exists():
        raise FileExistsError(f"write-once learner run directory already exists: {run_dir}")
    plan, train_manifest, eval_manifest, source_hashes = build_registration(session, revision)
    run_dir.mkdir()
    plan_raw = _json_bytes(plan)
    train_raw = _json_bytes(train_manifest)
    eval_raw = _json_bytes(eval_manifest)
    _write_once(run_dir / "plan.json", plan_raw)
    _write_once(run_dir / "root-manifest.json", train_raw)
    _write_once(run_dir / "evaluation-root-manifest.json", eval_raw)
    registration = {
        "status": "REGISTERED_PRE_TRAINING",
        "registered_at": plan["registered_at"],
        "session_id": session["id"],
        "plan_sha256": sha(plan_raw),
        "root_manifest_sha256": sha(train_raw),
        "evaluation_root_manifest_sha256": sha(eval_raw),
        "source_sha256": source_hashes,
        "search_started": False,
        "training_search_authorized_by_registration": True,
        "evaluation_search_requires_complete_training_and_later_bound_evaluation_registration": True,
    }
    _write_once(run_dir / "registration.json", _json_bytes(registration))
    return preflight(run_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", type=int, choices=sorted(RUNS), default=1)
    args = parser.parse_args()
    print(json.dumps(register(args.revision), indent=2, sort_keys=True))
