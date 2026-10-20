"""Write-once, outcome-blind registration for the task2618 cost scan."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

import chess

from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2565.train import restore


ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2618/wdl-shared-cost"
TRAINING_ROOTS = ROOT / "results/dev_aux/task2619/prospective-training-roots.json"
SEEDS = (1733, 2618, 6112, 9929)
SOURCE_PATHS = (
    "results/dev_aux/task2618/register_wdl_cost_scan.py",
    "results/dev_aux/task2618/shared_wdl_cost_scan.py",
    "results/dev_aux/task2618/wdl_receipt_adapter.py",
    "results/dev_aux/task2392/reader.py",
    "results/dev_aux/task2153/stop_evidence.py",
    "results/dev_aux/task109/adapter.py",
    "results/dev_aux/task2492/adapters.py",
    "results/dev_aux/task2492/learning.py",
    "results/dev_aux/task2565/train.py",
    "results/dev_aux/task2619/root_feasibility.py",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: object) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def register() -> dict:
    stop = SharedDeleteStopReader(ROOT)
    stop()
    session = json.loads((ROOT / ".local_agent/session.json").read_text(encoding="utf-8"))
    role = json.loads((ROOT / ".local_agent/role.json").read_text(encoding="utf-8"))
    if session.get("state") != "active" or session.get("thread_id") != "01a128cf-ae2d-7352-a456-06bd38367221":
        raise ValueError("registration requires the active DEV_AUX segment")
    if role.get("role") != "DEV_AUX" or role.get("branch") != "sidemission":
        raise ValueError("registration must run in DEV_AUX/sidemission")
    if RUN.exists():
        raise FileExistsError(f"write-once run directory already exists: {RUN}")

    roots_raw = TRAINING_ROOTS.read_bytes()
    root_manifest = json.loads(roots_raw)
    roots = root_manifest["roots"]
    rounds = 8
    selected = roots[: len(SEEDS) * rounds]
    if len(selected) != 32:
        raise ValueError("task2619 training pool lacks the frozen 32-root cost panel")
    selected_families = []
    for index, row in enumerate(selected):
        record = row["record"]
        if len(record.get("moves", ())) != 8 or canonical_digest(record) != row["record_sha256"]:
            raise ValueError(f"bad full-history training root at index {index}")
        env = restore(0, None, record)
        if env.record() != record or env.terminal() is not None:
            raise ValueError(f"training root replay failed at index {index}")
        selected_families.append(row["family"])

    source_hashes = {
        name: digest((ROOT / name).read_bytes()) for name in SOURCE_PATHS
    }
    plan = {
        "task": "DEV_AUX2618_WDL_SHARED_PATH_COST_ONLY",
        "status": "FROZEN_BEFORE_SEARCH",
        "session_id": session["id"],
        "segment_started_at": session["started_at"],
        "registered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "training_roots_path": str(TRAINING_ROOTS.relative_to(ROOT)).replace("\\", "/"),
        "training_roots_sha256": digest(roots_raw),
        "selection": "first32 exact full-history nonterminal task2619 training roots; 8 per seed; no evaluation roots read",
        "root_indices": list(range(32)),
        "families": selected_families,
        "seeds": list(SEEDS),
        "seed_count": len(SEEDS),
        "proposal_rounds": rounds,
        "episode_order": [["incumbent", 0], ["proposal", 0], ["proposal", 1], ["incumbent", 1]],
        "candidate_initialization": "task2618 deterministic [pawn=1, others Uniform(0.5,1.5)] per seed",
        "proposal": "one coordinate 1..4 in cyclic order; multiplicative exp(Uniform(-ln2,ln2)); seed=seed*100000+round+972568000",
        "fixed_foe_weights": [1.0, 1.0, 1.0, 1.0, 1.0],
        "search": {"implementation": "task2612 AlphaBeta/Receipt", "depth": 2, "qdepth": 0},
        "node_budget_per_seed": 100000,
        "max_nodes_per_search": 8192,
        "seconds_per_search_cap": 2.0,
        "max_plies_per_game": 512,
        "global_hard_cap_seconds": 900,
        "cost_accounting": "charge every completed or partial Receipt to candidate or fixed-foe side in one combined per-seed cap",
        "unknown_policy": "full [-1,+1] endpoint; no draw imputation; incomplete paired block does not update weights",
        "persistence": "costs, censoring/completion category and resource usage only; no WDL labels, intervals, proposals or weights persisted",
        "fitness_evaluation": False,
        "source_sha256": source_hashes,
        "python_chess_version": chess.__version__,
    }
    RUN.mkdir()
    plan_bytes = (json.dumps(plan, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with (RUN / "plan.json").open("xb") as file:
        file.write(plan_bytes)
    registration = {
        "status": "REGISTERED_COST_ONLY",
        "registered_at": plan["registered_at"],
        "session_id": session["id"],
        "plan_sha256": digest(plan_bytes),
        "plan_path": "results/dev_aux/task2618/wdl-shared-cost/plan.json",
        "search_started": False,
        "fitness_evaluation": False,
    }
    with (RUN / "registration.json").open("xb") as file:
        file.write((json.dumps(registration, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return registration


if __name__ == "__main__":
    print(json.dumps(register(), indent=2, sort_keys=True))
