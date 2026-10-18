"""Repeat the truncation stratification on distinct positions.

Zero searches. Reads only the primary judge file, collapses the 45 judged
seed-depth cells onto the position identity already used by
summarize_judged_divergence.py, and reports per-stratum verdicts, seed-level
majorities and group splits on that unit.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIMARY = HERE / "results_judged_divergence.json"
OUT = HERE / "results_judged_divergence_distinct_strata.json"
GROUP_OF = {"sweep": "config_decided", "blind": "config_decided", "split": "divergent_split"}
EXPECTED_DISTINCT = 35


def sha_prefix(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8].upper()


def position_key(record: dict) -> tuple:
    moves = record["saved_moves_at_divergence"]
    return (
        record["seed"],
        record["first_diff_ply"],
        record["divergence_side"],
        moves.get("served"),
        moves.get("blind"),
    )


def stratum(record: dict) -> str:
    reasons = (record["oracle"]["blind"]["reason"], record["oracle"]["served"]["reason"])
    done = [reason == "completed_depth" for reason in reasons]
    if all(done):
        return "both_completed"
    return "both_truncated" if not any(done) else "one_truncated"


def majority(counter: Counter) -> str:
    served, blind = counter.get("served_better", 0), counter.get("blind_better", 0)
    if served > blind:
        return "served_better"
    if blind > served:
        return "blind_better"
    return "mixed"


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite existing result {OUT.name}")

    data = json.loads(PRIMARY.read_text(encoding="utf-8"))
    judged = [record for record in data["records"] if record["status"] == "judged"]
    if len(judged) != 45:
        raise SystemExit(f"expected 45 judged cells, found {len(judged)}")

    first_seen: dict[tuple, dict] = {}
    duplicates: list[dict] = []
    for record in sorted(judged, key=lambda r: (r["depth"], r["seed"])):
        key = position_key(record)
        if key in first_seen:
            kept = first_seen[key]
            duplicates.append(
                {
                    "seed": record["seed"],
                    "kept_depth": kept["depth"],
                    "extra_depth": record["depth"],
                    "kept_stratum": stratum(kept),
                    "extra_stratum": stratum(record),
                    "verdict_equal": kept["verdict"] == record["verdict"],
                    "delta_equal": kept["delta"] == record["delta"],
                }
            )
            continue
        first_seen[key] = record

    if len(first_seen) != EXPECTED_DISTINCT:
        raise SystemExit(
            f"distinct positions {len(first_seen)} != recorded {EXPECTED_DISTINCT}"
        )

    positions = list(first_seen.values())
    stratum_conflicts = sum(1 for row in duplicates if row["kept_stratum"] != row["extra_stratum"])

    d1 = defaultdict(Counter)
    for record in positions:
        d1[GROUP_OF[record["pair_kind"]]][stratum(record)] += 1

    d2 = defaultdict(Counter)
    for record in positions:
        d2[stratum(record)][record["verdict"]] += 1
    d2_excl = defaultdict(Counter)
    for record in positions:
        if record.get("tie_break"):
            continue
        d2_excl[stratum(record)][record["verdict"]] += 1

    d3 = defaultdict(lambda: defaultdict(Counter))
    for record in positions:
        d3[stratum(record)][record["seed"]][record["verdict"]] += 1
    d3_out = {}
    for name, seeds in sorted(d3.items()):
        tally = Counter(majority(counter) for counter in seeds.values())
        d3_out[name] = {
            "seeds": len(seeds),
            "seed_majority": dict(sorted(tally.items())),
        }

    payload = {
        "written_at_utc": "2026-10-18T11:30:00Z",
        "plan": "judged-divergence/plan-distinct-position-strata.json (written before this analysis)",
        "question": "does the truncation stratification hold on distinct positions rather than correlated seed-depth cells?",
        "input": {"results_judged_divergence.json": sha_prefix(PRIMARY)},
        "counts": {
            "judged_cells": len(judged),
            "distinct_positions": len(first_seen),
            "duplicate_cells": len(duplicates),
            "duplicate_stratum_conflicts": stratum_conflicts,
        },
        "D1_group_by_stratum": {g: dict(sorted(c.items())) for g, c in sorted(d1.items())},
        "D2_verdicts_by_stratum": {k: dict(sorted(c.items())) for k, c in sorted(d2.items())},
        "D2b_verdicts_by_stratum_excluding_tiebreak": {
            k: dict(sorted(c.items())) for k, c in sorted(d2_excl.items())
        },
        "D3_seed_level_by_stratum": d3_out,
        "duplicates": duplicates,
        "no_significance_statement": "descriptive counts only; each seed contributes one start and the duplicate cells are the same positions judged at two arm depths",
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("counts", "D1_group_by_stratum",
                                              "D2_verdicts_by_stratum",
                                              "D2b_verdicts_by_stratum_excluding_tiebreak",
                                              "D3_seed_level_by_stratum")}, indent=1))
    print("output", OUT.name, sha_prefix(OUT))


if __name__ == "__main__":
    main()
