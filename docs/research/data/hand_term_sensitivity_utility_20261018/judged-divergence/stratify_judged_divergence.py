"""Stratify the saved judged-divergence records by whether the oracle actually
completed its prewritten depth-4/20k-node search.

Zero new searches. Reads three existing result files, verifies that they
describe the same 45 judged cells with the same candidate moves, verifies the
stored aggregate of the primary file, then reports:

  E1  truncation pattern counts per group and depth
  E2  verdict distribution per stratum and group (tie-break cells separated)
  E3  seed-level majority tally per stratum (descriptive, no p-values)
  E4  cross-weight agreement, with the 3-weight parameter-free majority over
      all 45 cells and restricted to the both-completed stratum

Guards: refuses to overwrite an existing output file, fails on any structural
disagreement between the three inputs, writes only the new strata file.
No p-values and no significance claims are produced anywhere in this script.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIMARY = HERE / "results_judged_divergence.json"
SERVED_JUDGE = HERE / "results_judged_divergence_servedjudge.json"
W18_JUDGE = HERE / "results_judged_divergence_w18judge.json"
OUT = HERE / "results_judged_divergence_strata.json"

WEIGHTS = [0.0, 0.9, 1.8]
GROUP_OF = {"sweep": "config_decided", "blind": "config_decided", "split": "divergent_split"}
MATE_SCALE = 100_000_000  # judge-reported mate-scale magnitudes observed earlier


def sha_prefix(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8].upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cell_key(record: dict) -> tuple[int, int]:
    return (record["seed"], record["depth"])


def judged(records: list[dict]) -> dict[tuple[int, int], dict]:
    out = {}
    for record in records:
        if record["status"] != "judged":
            continue
        key = cell_key(record)
        if key in out:
            raise SystemExit(f"duplicate judged cell {key}")
        out[key] = record
    return out


def stratum(record: dict) -> str:
    reasons = (record["oracle"]["blind"]["reason"], record["oracle"]["served"]["reason"])
    done = [reason == "completed_depth" for reason in reasons]
    if all(done):
        return "both_completed"
    if not any(done):
        return "both_truncated"
    return "one_truncated"


def majority(counter: Counter) -> str:
    served = counter.get("served_better", 0)
    blind = counter.get("blind_better", 0)
    if served > blind:
        return "served_better"
    if blind > served:
        return "blind_better"
    return "mixed"


def verify_primary_aggregate(primary: dict, cells: dict[tuple[int, int], dict]) -> None:
    stored = primary["aggregate"]
    if stored["total_records"] != len(primary["records"]):
        raise SystemExit("stored total_records disagrees with record count")
    statuses = Counter(record["status"] for record in primary["records"])
    if dict(statuses) != stored["statuses"]:
        raise SystemExit(f"stored statuses {stored['statuses']} != recomputed {dict(statuses)}")
    for name, block in stored["groups"].items():
        members = [c for c in cells.values() if GROUP_OF[c["pair_kind"]] == name]
        if len(members) != block["positions"]:
            raise SystemExit(f"group {name}: stored {block['positions']} != {len(members)}")
        verdicts = Counter(c["verdict"] for c in members)
        if dict(verdicts) != block["verdicts"]:
            raise SystemExit(f"group {name}: stored verdicts {block['verdicts']} != {dict(verdicts)}")


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite existing result {OUT.name}")

    files = {"0.0_primary": PRIMARY, "0.9_served": SERVED_JUDGE, "1.8_double": W18_JUDGE}
    inputs = {name: sha_prefix(path) for name, path in files.items()}
    data = {name: load(path) for name, path in files.items()}

    primary_cells = judged(data["0.0_primary"]["records"])
    per_weight_cells = {name: judged(frame["records"]) for name, frame in data.items()}
    key_set = set(primary_cells)
    for name, cells in per_weight_cells.items():
        if set(cells) != key_set:
            raise SystemExit(f"{name}: judged cell set differs from primary")
        for key in key_set:
            moves_a = primary_cells[key]["candidates"]
            moves_b = cells[key]["candidates"]
            for side in ("blind", "served"):
                if moves_a[side]["move"] != moves_b[side]["move"]:
                    raise SystemExit(f"{name}: candidate move mismatch at {key} side {side}")

    verify_primary_aggregate(data["0.0_primary"], primary_cells)

    # E1: truncation pattern counts per group and depth.
    e1 = defaultdict(Counter)
    for key, record in primary_cells.items():
        group = GROUP_OF[record["pair_kind"]]
        e1[group][(stratum(record), record["depth"])] += 1
    e1_out = {
        group: {
            f"{name}|d{depth}": count
            for (name, depth), count in sorted(counter.items())
        }
        for group, counter in sorted(e1.items())
    }

    # E2: verdict distribution per stratum and group.
    e2 = defaultdict(Counter)
    tiebreak_cells = []
    for key, record in primary_cells.items():
        group = GROUP_OF[record["pair_kind"]]
        name = stratum(record)
        e2[f"{group}|{name}"][record["verdict"]] += 1
        if record.get("tie_break"):
            tiebreak_cells.append(
                {
                    "seed": record["seed"],
                    "depth": record["depth"],
                    "group": group,
                    "stratum": name,
                    "verdict": record["verdict"],
                }
            )
    e2_out = {name: dict(sorted(counter.items())) for name, counter in sorted(e2.items())}

    # E2b: same distribution excluding the depth-6 tie-break cells entirely.
    e2b = defaultdict(Counter)
    for key, record in primary_cells.items():
        if record.get("tie_break"):
            continue
        name = stratum(record)
        e2b[name][record["verdict"]] += 1
    e2b_out = {name: dict(sorted(counter.items())) for name, counter in sorted(e2b.items())}

    # E3: seed-level tally inside each stratum (majority of that seed's cells).
    e3 = defaultdict(lambda: defaultdict(Counter))
    for key, record in primary_cells.items():
        name = stratum(record)
        e3[name][record["seed"]][record["verdict"]] += 1
    e3_out = {}
    for name, seeds in sorted(e3.items()):
        seed_verdicts = Counter(majority(counter) for counter in seeds.values())
        e3_out[name] = {
            "seeds": len(seeds),
            "seed_majority": dict(sorted(seed_verdicts.items())),
            "seed_majority_served": seed_verdicts.get("served_better", 0),
            "seed_majority_blind": seed_verdicts.get("blind_better", 0),
            "seed_majority_mixed": seed_verdicts.get("mixed", 0),
        }

    # E4: cross-weight agreement, and the parameter-free 3-weight majority.
    deltas = {
        weight: {key: per_weight_cells[name][key]["delta"] for key in key_set}
        for weight, name in zip(WEIGHTS, ("0.0_primary", "0.9_served", "1.8_double"))
    }

    def sign(value: int) -> int:
        return (value > 0) - (value < 0)

    votes = {}
    for key in key_set:
        tally = Counter()
        for weight in WEIGHTS:
            s = sign(deltas[weight][key])
            tally["served_better" if s > 0 else "blind_better" if s < 0 else "tie"] += 1
        votes[key] = tally
    majority_all = Counter(majority(tally) for tally in votes.values())
    unanimous = Counter()
    for tally in votes.values():
        nonzero = {name for name in tally if name != "tie" and tally[name]}
        if len(nonzero) == 1 and tally["tie"] == 0:
            unanimous[next(iter(nonzero))] += 1

    agree_primary = Counter()
    both_completed_agree = Counter()
    both_completed_majority = Counter()
    for key, record in primary_cells.items():
        name = stratum(record)
        if name == "both_completed":
            both_completed_majority[majority(votes[key])] += 1
        for weight in WEIGHTS:
            consensus = majority(votes[key])
            if consensus == "mixed":
                continue
            same = consensus == ("served_better" if deltas[weight][key] > 0 else "blind_better")
            if same:
                agree_primary[weight] += 1
                if name == "both_completed":
                    both_completed_agree[weight] += 1
    e4_out = {
        "majority_over_weights_all_45": dict(sorted(majority_all.items())),
        "unanimous_all_three_weights": dict(sorted(unanimous.items())),
        "weight_matches_3weight_majority": {str(w): agree_primary[w] for w in WEIGHTS},
        "both_completed_majority_over_weights": dict(sorted(both_completed_majority.items())),
        "both_completed_weight_matches_majority": {str(w): both_completed_agree[w] for w in WEIGHTS},
        "caveat": "the three judges are one correlated coefficient family over the same positions; agreement is a stability diagnostic, not independent evidence",
    }

    # Descriptive mate-scale counts per stratum.
    mate = Counter()
    kept_sign = 0
    for key, record in primary_cells.items():
        magnitudes = [abs(deltas[w][key]) for w in WEIGHTS]
        if max(magnitudes) >= MATE_SCALE:
            mate[stratum(record)] += 1
            signs = {sign(deltas[w][key]) for w in WEIGHTS}
            if len(signs) == 1:
                kept_sign += 1

    both_completed_n = sum(
        1 for record in primary_cells.values() if stratum(record) == "both_completed"
    )
    blind_majority_retained = majority(e3_out["both_completed"]["seed_majority"]) if "both_completed" in e3_out else "mixed"
    if both_completed_n >= 10:
        decision = (
            "blind_majority_retained_in_completed_stratum"
            if blind_majority_retained == "blind_better"
            else "no_blind_majority_in_completed_stratum"
        )
    else:
        decision = "completed_stratum_too_small_to_decide"

    payload = {
        "written_at_utc": "2026-10-18T11:14:00Z",
        "plan": "judged-divergence/plan-truncation-strata.json (written before this analysis)",
        "question": "Do the judged divergence verdicts survive when only fully completed depth-4/20k oracle evaluations are counted?",
        "inputs": inputs,
        "counts": {
            "judged_cells": len(primary_cells),
            "both_completed": both_completed_n,
            "one_truncated": sum(1 for r in primary_cells.values() if stratum(r) == "one_truncated"),
            "both_truncated": sum(1 for r in primary_cells.values() if stratum(r) == "both_truncated"),
        },
        "E1_truncation_by_group_depth": e1_out,
        "E2_verdicts_by_group_stratum": e2_out,
        "E2b_verdicts_by_stratum_excluding_tiebreak": e2b_out,
        "E2c_tiebreak_cells": tiebreak_cells,
        "E3_seed_level_by_stratum": e3_out,
        "E4_cross_weight": e4_out,
        "mate_scale_cells_by_stratum": dict(sorted(mate.items())),
        "mate_scale_cells_same_sign_all_weights": kept_sign,
        "decision": decision,
        "decision_basis": "prewritten rule in plan-truncation-strata.json; seed-level majority inside the both_completed stratum",
        "no_significance_statement": "no p-values are computed; cells within a seed and depth pair are correlated and the three judges are one coefficient family",
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(json.dumps({k: payload[k] for k in ("counts", "E1_truncation_by_group_depth",
                                              "E2_verdicts_by_group_stratum",
                                              "E2b_verdicts_by_stratum_excluding_tiebreak",
                                              "E3_seed_level_by_stratum", "E4_cross_weight",
                                              "mate_scale_cells_by_stratum",
                                              "mate_scale_cells_same_sign_all_weights",
                                              "decision")}, indent=1))
    print("output", OUT.name, sha_prefix(OUT))


if __name__ == "__main__":
    main()
