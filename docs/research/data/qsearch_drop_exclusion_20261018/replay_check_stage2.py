"""DEEPSEEK_AUX replay check: recompute four stage-2 seeds from source and compare."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location("probe_stage2", HERE / "probe_stage2.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
stage1 = probe.stage1

SEEDS = [124, 127, 147, 150]
FIELDS = [
    "offset",
    "ply",
    "legal_actions",
    "excluded_drops",
    "checking_drops",
    "terminal_drops",
    "blind_threat_drops",
    "profitable_blind_threat_drops",
    "d2_score",
    "d3_score",
    "d2_action",
    "d3_action",
    "action_equal_2_3",
    "abs_score_delta_2_3",
    "mate_bound",
]


def main() -> int:
    stored = {
        p["seed"]: p
        for p in json.loads(
            (HERE / "results_stage2_fresh_seeds.json").read_text(encoding="utf-8")
        )["positions"]
    }
    rows = []
    for seed in SEEDS:
        compiled = stage1.generated_compiled(seed)
        state, offset = probe.sample_start2(compiled, seed)
        evaluator, profile = stage1.make_searcher(compiled)
        record = probe.analyze_position2(
            seed, compiled, profile, evaluator, state, offset
        )
        differences = {
            field: {"stored": stored[seed][field], "replay": record[field]}
            for field in FIELDS
            if stored[seed][field] != record[field]
        }
        rows.append(
            {
                "seed": seed,
                "differences": differences,
                "matches": not differences,
            }
        )
        print(seed, "match" if not differences else differences, flush=True)
    payload = {
        "role": "DEEPSEEK_AUX",
        "seeds": SEEDS,
        "fields_compared": FIELDS,
        "all_match": all(r["matches"] for r in rows),
        "rows": rows,
        "source_script_sha256": stage1.sha256_file(Path(__file__)),
        "probe_script_sha256": stage1.sha256_file(HERE / "probe_stage2.py"),
        "stage1_module_sha256": stage1.sha256_file(
            HERE / "check_qsearch_drop_exclusion.py"
        ),
    }
    (HERE / "replay_check_stage2.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0 if payload["all_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
