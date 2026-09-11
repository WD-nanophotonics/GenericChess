"""F81-R2 audit and time-budget cap-contract corrective harness."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning import arena as arena_module  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f81_r1_eight_lane_final_strength_confirmation as f81r1  # noqa: E402


WORK_ORDER = "GENERICCHESS-F81-R2-TIME-BUDGET-CAP-CORRECTIVE"
BASELINE_SHA = "55c7bbcccb21d78d0398e0deecbfd5301e059392"
PROGRESS = ROOT / ".generic_chess_flow" / "f81-r1-eight-lane-final-confirmation" / "progress"
CORPUS_PATH = ROOT / "artifacts" / "f81_final_confirmation" / "openings.json"
AUDIT_PATH = ROOT / "artifacts" / "f81_final_confirmation" / "f81_r1_time_cap_audit.json"
CAP_LIKE_REASONS = {"time_budget", "time_limit", "timeout", "deadline", "cancelled", "canceled"}


def _load_manifest_and_corpus(compiled):
    manifest = json.loads((PROGRESS / "manifest.json").read_text(encoding="utf-8"))
    corpus_payload = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    corpus = f81r1.ArenaOpeningCorpus.from_dict(corpus_payload["corpus"])
    corpus.validate(compiled)
    if corpus.corpus_id != f81r1.CORPUS_ID or corpus_payload.get("corpus_id") != f81r1.CORPUS_ID:
        raise RuntimeError("F81-R2 corpus identity mismatch")
    return manifest, corpus, corpus_payload


def _cap_like(reason: str) -> bool:
    normalized = reason.strip().lower()
    return normalized in CAP_LIKE_REASONS or "deadline" in normalized


def audit_r1_progress() -> dict:
    if not native_available():
        raise RuntimeError("F81-R2 requires the native extension for legal replay audit")
    compiled, _native, _profile = f59._ruleset(f81r1.LABEL)
    manifest, corpus, corpus_payload = _load_manifest_and_corpus(compiled)
    if manifest.get("schema") != arena_module.ARENA_GAME_PROGRESS_SCHEMA:
        raise RuntimeError("F81-R2 manifest schema mismatch")
    identity = manifest["identity"]
    if identity.get("parent_checkpoint_id") != f81r1.PARENT_SHA or identity.get("child_checkpoint_id") != f81r1.CHILD_SHA:
        raise RuntimeError("F81-R2 manifest checkpoint identity mismatch")
    config, caps = f81r1._config_and_caps()
    if identity.get("ordered_openings") != corpus.to_dict()["openings"]:
        raise RuntimeError("F81-R2 manifest corpus ordering mismatch")
    expected_config = arena_module.asdict(config)
    if identity.get("config") != expected_config:
        raise RuntimeError("F81-R2 manifest config mismatch")
    expected_caps = arena_module.asdict(caps)
    if identity.get("execution_caps") != expected_caps:
        raise RuntimeError("F81-R2 manifest caps mismatch")
    files = sorted(PROGRESS.glob("game-*.json"))
    expected_names = {f"game-{pair:06d}-owner-{owner}.json" for pair in range(8) for owner in (0, 1)}
    if {path.name for path in files} != expected_names:
        raise RuntimeError("F81-R2 expected exactly sixteen F81-R1 game files")
    games = {}
    failures = []
    for path in files:
        match = re.fullmatch(r"game-(\d{6})-owner-([01])\.json", path.name)
        pair_index, owner = int(match.group(1)), int(match.group(2))
        payload = json.loads(path.read_text(encoding="utf-8"))
        expected = arena_module._game_progress_identity_for(identity, config, caps, corpus.to_dict()["openings"][pair_index], pair_index, owner, capture_search_metrics=True)
        try:
            game = arena_module._validate_game_progress(compiled, corpus.openings[pair_index], payload, expected_identity=expected, identity_sha256=manifest["identity_sha256"], config=config, capture_search_metrics=True, pair_index=pair_index, child_owner=owner)
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")
            continue
        reasons = Counter(str(row.get("termination_reason", "")).strip().lower() for row in game.search_metrics)
        cap_reasons = sorted(reason for reason in reasons if _cap_like(reason))
        games[(pair_index, owner)] = game
        games.setdefault((pair_index, "audit"), {})
        games[(pair_index, "audit")][owner] = {
            "path": str(path.relative_to(ROOT)),
            "progress_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "opening_id": game.opening_id,
            "child_owner": owner,
            "result": game.result,
            "winner": game.winner,
            "child_points": game.child_points,
            "plies": game.plies,
            "telemetry_row_count": len(game.search_metrics),
            "trusted_elapsed_total_seconds": sum(float(row.get("elapsed_seconds", 0.0)) for row in game.search_metrics),
            "termination_reason_counts": dict(sorted(reasons.items())),
            "termination_reason_set": sorted(reasons),
            "max_search_nodes": max((int(row.get("nodes", 0)) for row in game.search_metrics), default=0),
            "all_root_window_pruning_true": bool(game.search_metrics) and all(row.get("root_window_pruning") is True for row in game.search_metrics),
            "missing_root_window_pruning_rows": sum("root_window_pruning" not in row for row in game.search_metrics),
            "cap_contaminated": bool(cap_reasons),
            "cap_like_reasons": cap_reasons,
        }
    pair_rows = []
    contaminated = []
    for pair_index in range(8):
        pair_games = games.get((pair_index, "audit"), {})
        if set(pair_games) != {0, 1}:
            failures.append(f"pair {pair_index} does not have both owners")
            continue
        contaminated_pair = any(pair_games[owner]["cap_contaminated"] for owner in (0, 1))
        if contaminated_pair:
            contaminated.append(pair_index)
        pair_rows.append({"pair_index": pair_index, "opening_id": pair_games[0]["opening_id"], "game_child_owner0": pair_games[0], "game_child_owner1": pair_games[1], "pair_score": (pair_games[0]["child_points"] + pair_games[1]["child_points"]) / 2.0, "cap_contaminated": contaminated_pair})
    audit = {
        "schema": "generic-chess-f81-r1-time-cap-audit-v1",
        "work_order": WORK_ORDER,
        "baseline_sha": BASELINE_SHA,
        "source_progress": str(PROGRESS.relative_to(ROOT)),
        "manifest_identity_sha256": manifest["identity_sha256"],
        "corpus_path": str(CORPUS_PATH.relative_to(ROOT)),
        "corpus_id": corpus.corpus_id,
        "corpus_content_sha256": hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest(),
        "parent_checkpoint_id": f81r1.PARENT_SHA,
        "child_checkpoint_id": f81r1.CHILD_SHA,
        "candidate_model_sha256": f81r1.CANDIDATE_MODEL_SHA,
        "opening_count": len(corpus.openings),
        "game_file_count": len(files),
        "validated_game_count": len([key for key in games if isinstance(key[1], int)]),
        "pair_count": len(pair_rows),
        "pairs": pair_rows,
        "contaminated_pair_indices": contaminated,
        "contract_failures": failures,
        "audit_classification": "TIME_BUDGET_CAP_CONTAMINATION_FOUND" if contaminated else "HARNESS_MISMATCH",
        "frozen_corpus_payload_sha256": hashlib.sha256(json.dumps(corpus_payload, sort_keys=True).encode()).hexdigest(),
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main() -> None:
    audit = audit_r1_progress()
    print(json.dumps({"audit_classification": audit["audit_classification"], "contaminated_pair_indices": audit["contaminated_pair_indices"], "game_file_count": audit["game_file_count"], "pair_count": audit["pair_count"], "contract_failures": audit["contract_failures"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
