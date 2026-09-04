"""Post-process F59 frozen-root overlap and D1/D2 sensitivity evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


NAMES = ("D0_RANDOM_REACHABLE", "D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR")


def overlap_matrix(distributions):
    keys = {name: [row["position_key"] for row in distributions[name]["roots_metadata"]]
            for name in NAMES}
    return {left: {right: len(set(keys[left]) & set(keys[right])) for right in NAMES} for left in NAMES}


def unique_indices(distributions, name):
    own = [row["position_key"] for row in distributions[name]["roots_metadata"]]
    other_keys = set().union(*(set(row["position_key"] for row in distributions[other]["roots_metadata"])
                               for other in NAMES if other != name))
    return [index for index, key in enumerate(own) if key not in other_keys]


def _subset_regret(distributions, name, indices, evaluator):
    rows = distributions[name]["roots_metadata"]
    values = [rows[index]["root"][f"{evaluator}_action_regret_q20"] for index in indices]
    return {"count": len(values), "mean": float(np.mean(values)) if values else None,
            "median": float(np.median(values)) if values else None}


def analyze(payload):
    distributions = payload["results"][0]["distributions"]
    matrix = overlap_matrix(distributions)
    unique = {name: unique_indices(distributions, name) for name in NAMES}
    d1 = unique["D1_V2_SELFPLAY"]
    d2 = unique["D2_V2_PV_CORRIDOR"]
    return {
        "ruleset": payload["results"][0]["label"],
        "overlap_matrix": matrix,
        "unique_indices_excluding_other_distributions": unique,
        "frozen_membership_unchanged": all(
            len(distributions[name]["roots_metadata"]) == 36 for name in NAMES
        ),
        "d1_d2_sensitivity": {
            "shared_count": matrix["D1_V2_SELFPLAY"]["D2_V2_PV_CORRIDOR"],
            "shared_comparison_status": "EXPLORATORY_CORRELATED_SAMPLES",
            "D1_only": {
                "v2": _subset_regret(distributions, "D1_V2_SELFPLAY", d1, "v2"),
                "v4": _subset_regret(distributions, "D1_V2_SELFPLAY", d1, "v4"),
            },
            "D2_only": {
                "v2": _subset_regret(distributions, "D2_V2_PV_CORRIDOR", d2, "v2"),
                "v4": _subset_regret(distributions, "D2_V2_PV_CORRIDOR", d2, "v4"),
            },
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(payload)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
