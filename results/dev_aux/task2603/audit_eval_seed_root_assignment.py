from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "results/dev_aux/task2594/root-manifest.json"
PLAN = ROOT / "results/dev_aux/task2594/eval-plan.json"
OUTPUT = Path(__file__).with_name("root-assignment.json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    by_seed = {int(seed): sorted(set(map(int, ids))) for seed, ids in manifest["eval_families_by_seed"].items()}
    slots_by_seed: dict[int, list[list[Any]]] = defaultdict(list)
    for slot in plan["slots"]:
        # Frozen slot schema: [rule_index, seed, family_id, color, endpoint, foe].
        slots_by_seed[int(slot[1])].append(slot)
    summaries = {}
    assert set(slots_by_seed) == set(by_seed), "seed set mismatch between manifest and plan"
    for seed, roots in sorted(by_seed.items()):
        slots = slots_by_seed[seed]
        per_root = Counter(int(slot[2]) for slot in slots)
        colors_by_root: dict[int, set[int]] = defaultdict(set)
        endpoints_by_root: dict[int, set[str]] = defaultdict(set)
        for slot in slots:
            colors_by_root[int(slot[2])].add(int(slot[3]))
            endpoints_by_root[int(slot[2])].add(str(slot[4]))
        summaries[str(seed)] = {
            "root_count": len(roots), "root_min": min(roots), "root_max": max(roots), "roots": roots,
            "slot_count": len(slots), "slots_per_root_counts": dict(sorted(Counter(per_root.values()).items())),
            "colors_per_root_counts": dict(sorted(Counter(len(v) for v in colors_by_root.values()).items())),
            "endpoints_per_root_counts": dict(sorted(Counter(len(v) for v in endpoints_by_root.values()).items())),
        }
        assert set(roots) == set(per_root), f"manifest/plan root mismatch for {seed}"
    seeds = sorted(by_seed)
    overlaps = {f"{a}:{b}": len(set(by_seed[a]) & set(by_seed[b])) for i,a in enumerate(seeds) for b in seeds[i+1:]}
    union = set().union(*(set(v) for v in by_seed.values()))
    return {
        "task_id": 2603, "status": "POST_HOC_ROOT_ALLOCATION_CORRECTION",
        "sources": {"root_manifest_sha256": sha256(MANIFEST), "eval_plan_sha256": sha256(PLAN), "fields_used": ["eval_families_by_seed", "slots", "scope"]},
        "plan_scope": plan["scope"], "per_seed": summaries, "pairwise_root_overlap_counts": overlaps,
        "total_seed_root_assignments": sum(len(v) for v in by_seed.values()), "total_distinct_roots": len(union),
        "interpretation": "The 128 roots are four disjoint 32-root blocks, one per seed. Within-seed method comparisons remain paired on the same root/color slots; cross-seed differences combine initialization and root-block differences.",
        "scope_exclusions": ["No W/L/D outcomes or eval summaries read.", "No query traces or learner weights read.", "No replay, training, or rerun of the frozen evaluation."],
    }


if __name__ == "__main__":
    result = audit()
    if OUTPUT.exists(): raise SystemExit(f"refusing to overwrite {OUTPUT.name}")
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"distinct_roots": result["total_distinct_roots"], "overlaps": result["pairwise_root_overlap_counts"]}, separators=(",", ":")))
