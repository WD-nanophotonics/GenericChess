"""Compare generated and saved rule movement under exact finite-board paths.

This is a movement-semantic inventory only. It does not inspect outcomes or
admit histories as training/evaluation roots.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2633"
INDEX = TASK / "generated/candidate-index.json"
OUT = TASK / "finite-board-movement-equivalence.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def semantic_type_signature(board_size: int, piece_type: dict) -> str:
    """Hash all source->target plus ray-intervening-square relations."""
    n = board_size
    sources = []
    for r in range(n):
        for f in range(n):
            actions = set()
            for atom in piece_type["movement_atoms"]:
                if atom["kind"] == "leap":
                    df, dr = atom["offset"]
                    tf, tr = f + df, r + dr
                    if 0 <= tf < n and 0 <= tr < n:
                        actions.add((tf * n + tr, ()))
                elif atom["kind"] == "ray":
                    df, dr = atom["direction"]
                    max_steps = atom.get("max_steps")
                    tf, tr = f, r
                    path = []
                    steps = 0
                    while max_steps is None or steps < max_steps:
                        tf += df
                        tr += dr
                        steps += 1
                        if not (0 <= tf < n and 0 <= tr < n):
                            break
                        path.append(tf * n + tr)
                        actions.add((tf * n + tr, tuple(path[:-1])))
                else:
                    raise ValueError(f"unknown movement atom {atom!r}")
            sources.append(sorted((target, list(intervening)) for target, intervening in actions))
    canonical = json.dumps(sources, separators=(",", ":")).encode()
    return sha(canonical)


def load_rules(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), sha(raw)


def setup_is_owner_rotationally_symmetric(rules: dict) -> bool:
    setup = rules["initial_position"]
    n = rules["board_size"]
    for r in range(n):
        for f in range(n):
            left = setup[r][f]
            right = setup[n - 1 - r][n - 1 - f]
            if left is None or right is None:
                if left is not None or right is not None:
                    return False
                continue
            if left["owner"] == right["owner"]:
                return False
            for key in ("base_type_id", "current_type_id", "promoted"):
                if left[key] != right[key]:
                    return False
    return True


def main() -> dict:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    candidates = []
    for row in index["rows"]:
        path = ROOT / row["source_file"]
        rules, digest = load_rules(path)
        if digest != row["ruleset_sha256"]:
            raise ValueError(f"candidate hash mismatch: {path}")
        candidates.append((path, digest, rules))

    saved = []
    for pattern in ("rules*.json", "rule-*.json"):
        for path in (ROOT / "results/dev_aux").rglob(pattern):
            if TASK in path.parents:
                continue
            try:
                rules, digest = load_rules(path)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(rules, dict) and isinstance(rules.get("piece_types"), list):
                saved.append((path, digest, rules))

    signatures = defaultdict(list)
    for path, digest, rules in saved:
        n = rules["board_size"]
        for pt in rules["piece_types"]:
            sig = semantic_type_signature(n, pt)
            signatures[(n, sig)].append({"file": path.relative_to(ROOT).as_posix(), "sha256": digest, "type_id": pt["type_id"]})

    candidate_rows = []
    owner_asymmetry = Counter()
    rotationally_symmetric_setups = 0
    saved_equivalent_type_hits = 0
    candidate_behaviors = defaultdict(list)
    for path, digest, rules in candidates:
        n = rules["board_size"]
        type_sigs = {pt["type_id"]: semantic_type_signature(n, pt) for pt in rules["piece_types"]}
        for tid, sig in type_sigs.items():
            candidate_behaviors[(n, sig)].append({"seed": rules.get("metadata", {}).get("seed"), "type_id": tid})
        counts = {owner: Counter() for owner in (0, 1)}
        for row in rules["initial_position"]:
            for cell in row:
                if cell is not None:
                    counts[cell["owner"]][cell["base_type_id"]] += 1
        asymmetry = {tid: counts[0][tid] - counts[1][tid] for tid in sorted(type_sigs) if counts[0][tid] != counts[1][tid]}
        if asymmetry:
            owner_asymmetry["nonmirror_type_counts"] += 1
        symmetric_setup = setup_is_owner_rotationally_symmetric(rules)
        if symmetric_setup:
            rotationally_symmetric_setups += 1
        hits = []
        for tid, sig in type_sigs.items():
            matches = signatures.get((n, sig), [])
            if matches:
                saved_equivalent_type_hits += 1
                hits.append({"type_id": tid, "matches": matches})
        candidate_rows.append({
            "seed": rules.get("metadata", {}).get("seed"),
            "ruleset_sha256": digest,
            "movement_signature_sha256": next(r["movement_signature_sha256"] for r in index["rows"] if r["ruleset_sha256"] == digest),
            "owner_piece_counts": {str(owner): dict(sorted(counts[owner].items())) for owner in (0, 1)},
            "owner_count_asymmetry": asymmetry,
            "setup_owner_swap_180_symmetric": symmetric_setup,
            "piece_type_count": len(type_sigs),
            "piece_types_with_saved_finite_board_equivalent": hits,
        })

    result = {
        "status": "COMPLETE",
        "question": "Do raw-novel generated movement signatures collapse to saved exact finite-board movement/path behavior, and does the setup contain owner-count asymmetry?",
        "candidate_count": len(candidates),
        "saved_rule_files_scanned": len(saved),
        "saved_distinct_finite_board_type_behaviors": len(signatures),
        "candidate_piece_type_count": sum(row["piece_type_count"] for row in candidate_rows),
        "candidate_distinct_finite_board_type_behaviors": len(candidate_behaviors),
        "candidate_nonanchor_distinct_behaviors": len({
            sig for (board_size, sig), members in candidate_behaviors.items()
            if any(member["type_id"] != "K" for member in members)
        }),
        "candidate_piece_types_matching_saved_behavior": saved_equivalent_type_hits,
        "candidate_behavior_collisions_within_batch": [
            {"board_size": board_size, "signature_sha256": sig, "members": members}
            for (board_size, sig), members in candidate_behaviors.items() if len(members) > 1
        ],
        "candidates_with_owner_count_asymmetry": owner_asymmetry["nonmirror_type_counts"],
        "candidates_with_exact_owner_swap_180_symmetric_setup": rotationally_symmetric_setups,
        "candidate_index_sha256": sha(INDEX.read_bytes()),
        "saved_input_manifest_sha256": sha(json.dumps(
            sorted((path.relative_to(ROOT).as_posix(), digest) for path, digest, _ in saved),
            separators=(",", ":"),
        ).encode()),
        "scope": "Movement-only exact finite-board source/target and ray-path behavior; saved result artifacts only. No complete-game equivalence, built-in rules, legal-history exposure, playout, WDL, search, learning or strength claim.",
        "limitations": [
            "The saved corpus is not a population sample and excludes built-in Chess/Western rules.",
            "Equivalent individual movement behavior does not imply whole-ruleset equivalence.",
            "The generator rotates player1 setup; this candidate batch does not test arbitrary ownership allocation.",
            "No full-history exposure audit was performed; candidate roots remain inadmissible to a pool.",
        ],
        "candidates": candidate_rows,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "candidates"}, indent=2))
    return result


if __name__ == "__main__":
    main()
