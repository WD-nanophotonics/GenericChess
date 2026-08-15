"""One bounded F21 production performance case/profile worker."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from scripts.audit_f21_native_legality_routing import (
    OUT,
    NativeSemanticLegalityProvider,
    corpus_specs,
    make_session,
    run_once,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", choices=("A", "B"))
    parser.add_argument("case_id")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    spec = next(row for row in corpus_specs() if row["id"] == args.case_id)
    provider = NativeSemanticLegalityProvider.try_create(make_session(spec).compiled)
    run_once(spec, args.profile, False)
    run_once(spec, args.profile, True, provider)
    rows = []
    for repeat in range(args.repeats):
        baseline = run_once(spec, args.profile, False)
        native = run_once(spec, args.profile, True, provider)
        parity_keys = ("action", "score", "pv", "termination_reason", "stats")
        mismatch_keys = [key for key in parity_keys if baseline[key] != native[key]]
        stat_differences = {}
        if baseline["stats"] != native["stats"]:
            names = set(baseline["stats"]) | set(native["stats"])
            stat_differences = {
                name: {"baseline": baseline["stats"].get(name), "native": native["stats"].get(name)}
                for name in sorted(names)
                if baseline["stats"].get(name) != native["stats"].get(name)
            }
        parity = not mismatch_keys
        rows.append({
            "case_id": args.case_id,
            "profile": args.profile,
            "repeat": repeat + 1,
            "baseline_us": baseline["elapsed_us"],
            "native_us": native["elapsed_us"],
            "gain": 1.0 - native["elapsed_us"] / baseline["elapsed_us"],
            "parity": parity,
            "mismatch_keys": mismatch_keys,
            "stat_differences": stat_differences,
        })
    result = {
        "case_id": args.case_id,
        "profile": args.profile,
        "repeats": rows,
        "baseline_median_us": statistics.median(row["baseline_us"] for row in rows),
        "native_median_us": statistics.median(row["native_us"] for row in rows),
        "gain": statistics.median(row["gain"] for row in rows),
        "parity": all(row["parity"] for row in rows),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"performance_{args.profile}_{args.case_id}.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
