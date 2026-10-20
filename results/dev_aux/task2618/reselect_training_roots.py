"""Prepare a deterministic v2 Chess training panel without v1-exposed roots.

This is a preparation audit only: it reads only exposure fields from v1 game
rows and never reads outcomes to select roots. It does not register or search.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2618"
TRAIN_PATH = ROOT / "results/dev_aux/task2619/prospective-training-roots.json"
EVAL_PATH = ROOT / "results/dev_aux/task2619/prospective-evaluation-roots.json"
AUDIT_PATH = ROOT / "results/dev_aux/task2618/learning-input-audit-v2.json"
EXPOSED_PATH = TASK / "learner-comparison-v1/games.jsonl"
OUTPUT_DIR = TASK / "learner-comparison-v2-prep-verified"
PANEL_SIZE = 120
SEED_NAMESPACE = "DEV_AUX_TASK2618_CHESS_TRAINING_ROOT_PANEL_V2"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def panel_seed() -> int:
    return int.from_bytes(hashlib.sha256(SEED_NAMESPACE.encode()).digest()[:4], "big")


def started_family_ids(games_raw: bytes) -> set[int]:
    exposed: set[int] = set()
    for line in games_raw.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        # Deliberately project only the exposure marker and family key.
        if row.get("unstarted") is not True:
            family = row.get("family")
            if not isinstance(family, int):
                raise ValueError("started v1 row has no integer family id")
            exposed.add(family)
    return exposed


def build_panel(training_doc: dict, evaluation_doc: dict, audit: dict,
                games_raw: bytes, source_hashes: dict[str, str]) -> dict:
    selection = audit["selection"]
    train_start, train_end = selection["training_root_indices_remaining"]
    candidates = training_doc["roots"][train_start:train_end]
    expected_count = selection.get("training_root_count_remaining", train_end - train_start)
    if len(candidates) != expected_count or len({row["family"] for row in candidates}) != expected_count:
        raise ValueError("eligible training pool differs from the audited exact root set")
    exposed = started_family_ids(games_raw)
    known = {row["family"] for row in candidates}
    if not exposed or not exposed <= known:
        raise ValueError("v1 exposure set is empty or contains roots outside the audited pool")
    available = [row for row in candidates if row["family"] not in exposed]
    if len(available) < PANEL_SIZE:
        raise ValueError("not enough unexposed training roots for the frozen v2 panel")
    ordered = sorted(available, key=lambda row: row["family"])
    random.Random(panel_seed()).shuffle(ordered)
    selected = ordered[:PANEL_SIZE]
    selected_keys = {canonical(row["record"]) for row in selected}
    eval_keys = {canonical(row["record"]) for row in evaluation_doc["roots"]}
    if selected_keys & eval_keys:
        raise ValueError("v2 training panel overlaps the frozen evaluation panel")
    return {
        "status": "PREPARATION_ONLY_NOT_REGISTERED",
        "task": "DEV_AUX2618_CHESS_LEARNER_COMPARISON_V2_ROOT_PANEL",
        "selection_method": "Sort eligible roots by family, seeded shuffle with fixed namespace, take first 120; same panel is paired across all learner seeds and methods.",
        "selection_seed_namespace": SEED_NAMESPACE,
        "selection_seed": panel_seed(),
        "panel_size": PANEL_SIZE,
        "source_training_range": [train_start, train_end],
        "exposed_family_ids_excluded": sorted(exposed),
        "eligible_unexposed_count": len(available),
        "evaluation_root_count": len(evaluation_doc["roots"]),
        "training_evaluation_exact_record_overlap": 0,
        "selected_exact_record_set_sha256": sha(b"\n".join(
            canonical(row["record"]) for row in selected
        )),
        "sources": {**source_hashes, "v1_games_exposure_file_sha256": sha(games_raw)},
        "exposure_field_projection": ["unstarted", "family"],
        "search_started": False,
        "outcome_fields_used_for_selection": False,
        "roots": selected,
    }


def prepare() -> dict:
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"write-once v2 root-panel output already exists: {OUTPUT_DIR}")
    training_doc = json.loads(TRAIN_PATH.read_text(encoding="utf-8"))
    evaluation_doc = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    games_raw = EXPOSED_PATH.read_bytes()
    panel = build_panel(
        training_doc, evaluation_doc, audit, games_raw,
        source_hashes={
            "training_roots_sha256": sha(TRAIN_PATH.read_bytes()),
            "evaluation_roots_sha256": sha(EVAL_PATH.read_bytes()),
            "input_audit_sha256": sha(AUDIT_PATH.read_bytes()),
            "root_selector_source_sha256": sha(Path(__file__).read_bytes()),
        },
    )
    OUTPUT_DIR.mkdir()
    raw = (json.dumps(panel, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    with (OUTPUT_DIR / "root-selection.json").open("xb") as stream:
        stream.write(raw)
        stream.flush()
    return {
        "status": panel["status"],
        "root_selection_sha256": sha(raw),
        "panel_size": panel["panel_size"],
        "excluded_exposed_roots": len(panel["exposed_family_ids_excluded"]),
        "eligible_unexposed_roots": panel["eligible_unexposed_count"],
        "evaluation_overlap": panel["training_evaluation_exact_record_overlap"],
        "search_started": panel["search_started"],
    }


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2, sort_keys=True))
