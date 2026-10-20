"""Bounded source-pinned, outcome-free generic movement candidate discovery."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.generation.config import GeneratorConfig, GenerationError
from generic_chess.generation.generator import generate_game
from generic_chess.rules.serialization import serialize_ruleset

TASK = ROOT / "results/dev_aux/task2633"
OUT = TASK / "generated"
SOURCE_PINS = json.loads((TASK / "plan.json").read_text(encoding="utf-8"))["source_sha256"]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def movement_signature(data: dict) -> str:
    projection = {
        "board_size": data["board_size"],
        "piece_types": sorted(({
            "type_id": p["type_id"],
            "movement_atoms": p["movement_atoms"],
            "is_promotable": p["is_promotable"],
            "promotion_target_ids": p["promotion_target_ids"],
        } for p in data["piece_types"]), key=lambda x: x["type_id"]),
    }
    raw = json.dumps(projection, sort_keys=True, separators=(",", ":")).encode()
    return sha(raw)


def saved_rule_signatures() -> tuple[set[str], int]:
    signatures: set[str] = set()
    count = 0
    for path in (ROOT / "results/dev_aux").rglob("rules*.json"):
        if TASK in path.parents:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("piece_types"), list):
            signatures.add(movement_signature(data))
            count += 1
    for path in (ROOT / "results/dev_aux").rglob("rule-*.json"):
        if TASK in path.parents:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("piece_types"), list):
            signatures.add(movement_signature(data))
            count += 1
    return signatures, count


def main() -> dict:
    if OUT.exists():
        raise FileExistsError("candidate batch is write-once")
    OUT.mkdir(parents=True)
    plan_raw = (TASK / "plan.json").read_bytes()
    plan = json.loads(plan_raw)
    for path, expected in plan["source_sha256"].items():
        if sha((ROOT / path).read_bytes()) != expected:
            raise ValueError(f"pinned generator source changed: {path}")
    known, saved_files = saved_rule_signatures()
    started = time.perf_counter()
    rows = []
    novel = Counter()
    cfg_data = dict(plan["config"])
    for seed in plan["seeds"]:
        if time.perf_counter() - started >= plan["hard_wall_cap_seconds"]:
            break
        try:
            game = generate_game(GeneratorConfig(seed=seed, **cfg_data))
        except GenerationError as exc:
            rows.append({"seed": seed, "status": "REJECTED_BY_GENERATOR", "reason": str(exc)})
            continue
        raw = serialize_ruleset(game.ruleset).encode("utf-8")
        data = json.loads(raw)
        movement_sha = movement_signature(data)
        is_novel = movement_sha not in known
        novel["novel" if is_novel else "matches_saved_movement_signature"] += 1
        candidate_path = OUT / f"seed-{seed}.rules.json"
        candidate_path.write_bytes(raw)
        reports = game.generation_report.piece_type_reports
        rows.append({
            "seed": seed,
            "status": "GENERATED_AND_COMPILED",
            "ruleset_sha256": sha(raw),
            "movement_signature_sha256": movement_sha,
            "movement_signature_novel_vs_saved_rule_files": is_novel,
            "source_file": candidate_path.relative_to(ROOT).as_posix(),
            "opening_legal_move_count": game.generation_report.opening_legal_move_count,
            "generation_attempts": game.generation_report.generation_attempts,
            "piece_types": [{
                "type_id": p.type_id,
                "movement_atoms": list(p.movement_atoms),
                "promotable": p.is_promotable,
                "average_mobility": p.average_mobility,
            } for p in reports],
        })
    result = {
        "status": "COMPLETE" if len(rows) == len(plan["seeds"]) else "PARTIAL_WALL_CAP",
        "plan_sha256": sha(plan_raw),
        "runner_sha256": sha(Path(__file__).read_bytes()),
        "source_sha256": plan["source_sha256"],
        "saved_rule_files_scanned": saved_files,
        "saved_distinct_movement_signatures": len(known),
        "candidate_count": len(rows),
        "candidate_status_counts": dict(Counter(row["status"] for row in rows)),
        "movement_novelty_counts": dict(novel),
        "wall_seconds": time.perf_counter() - started,
        "rows": rows,
        "scope": "Generation, rule compilation and generator soft-playability checks only. No legal playout, WDL, search, training, evaluation, or full-history exposure admission.",
        "ownership_limit": "The existing generator rotates player1's setup 180 degrees; this batch does not vary arbitrary owner allocation.",
    }
    (OUT / "candidate-index.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    return result


if __name__ == "__main__":
    main()
