"""DEEPSEEK_AUX: recompute every headline claim in the public similarity report.

Reads the stored scan/gap results, the private and public result copies and the
published README hashes.  Prints failures and exits non-zero if any check fails.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIV = Path(__file__).resolve().parent
PUB = ROOT / "docs" / "research" / "data" / "profile_tie_similarity_20261018"
SCAN = ROOT / "docs" / "research" / "data" / "profile_tie_risk_20261018" / "results_tie_risk.json"
GAP = ROOT / ".local_agent" / "profile-tie-risk-20261018" / "results_gap_headroom.json"

checks = []


def check(name: str, ok: bool, detail: object = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


scan = json.loads(SCAN.read_text(encoding="utf-8"))
gap = json.loads(GAP.read_text(encoding="utf-8"))
res = json.loads((PRIV / "results_signature_similarity.json").read_text(encoding="utf-8"))
pairs = json.loads((PRIV / "tied_pairs.json").read_text(encoding="utf-8"))["tied_pairs"]
plan = json.loads((PRIV / "plan.json").read_text(encoding="utf-8"))
plan_log = json.loads((PRIV / "plan-log.json").read_text(encoding="utf-8"))
readme = (PUB / "README.md").read_text(encoding="utf-8")

# Plan provenance
check("plan hash matches plan-log", sha(PRIV / "plan.json") == plan_log["plan_sha256"],
      plan_log["plan_sha256"])
check("plan-log says written_before_run", plan_log["status"] == "written_before_run")
check("plan written at 13:17:30Z", plan_log["written_at_utc"] == "2026-10-18T13:17:30Z")
check("result embeds plan hash", res["plan_sha256"] == plan_log["plan_sha256"])
check("pre-written decision present",
      plan["pre_written_decision"]["benign_concentration"].startswith("tied-pair median"))
check("new rules is zero", res["new_rules"] == 0)
check("search is none", res["search"] == "none")

# Recompute the pre-registered blocks from the stored scan
token_sets = {}
token_lists = {}
token_raw = {}
for block in scan["blocks"]:
    for rule in block["rules"]:
        for typ in rule["ordinary_types"]:
            key = (block["board_size"], rule["seed"], typ["type_id"])
            token_lists[key] = [tuple(e) for e in json.loads(typ["signature"])]
            token_sets[key] = frozenset(token_lists[key])
            token_raw[key] = typ["signature"]


def set_jaccard(a: frozenset, b: frozenset) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def multiset_jaccard(a: list, b: list) -> float:
    left, right = Counter(a), Counter(b)
    union = sum((left | right).values())
    return sum((left & right).values()) / union if union else 1.0


reference = []
ties = []
for cell in gap["cells"]:
    size = cell["board_size"]
    for pair in cell["pairs"]:
        lk = (size, pair["seed"], pair["pair"][0])
        rk = (size, pair["seed"], pair["pair"][1])
        rec = {
            "sizes": tuple(sorted((len(token_sets[lk]), len(token_sets[rk])))),
            "set": set_jaccard(token_sets[lk], token_sets[rk]),
            "multi": multiset_jaccard(token_lists[lk], token_lists[rk]),
            "same_set": token_sets[lk] == token_sets[rk],
            "same_multi": sorted(token_lists[lk]) == sorted(token_lists[rk]),
            "same_string": token_raw[lk] == token_raw[rk],
            "tied": bool(pair["tied"] and pair["distinct_raw"] and pair["exact_gap"] < 1),
            "equal_score": pair["raw_ratio"] == 1.0,
            "distinct_raw": bool(pair["distinct_raw"]),
            "gap_below_1": pair["exact_gap"] < 1,
        }
        reference.append(rec)
        if rec["tied"]:
            ties.append(rec)

tied_set = [r["set"] for r in ties]
ref_set = [r["set"] for r in reference]
check("tied n is 31", len(ties) == 31, len(ties))
check("reference n is 6811", len(reference) == 6811, len(reference))
check("tied median 1.0", statistics.median(tied_set) == 1.0)
check("reference median 0.72727", abs(statistics.median(ref_set) - 0.7272727272727273) < 1e-12)
check("reference p90 1.0", statistics.quantiles(ref_set, n=10)[8] == 1.0)
check("tied percentile 1.0",
      sum(1 for x in ref_set if x <= 1.0) / len(ref_set) == 1.0)

hist = Counter(round(x, 3) for x in tied_set)
check("histogram 25 at 1.0", hist[1.0] == 25, hist[1.0])
check("histogram 2 at 0.9", hist[0.9] == 2, hist[0.9])
check("histogram 1 at 0.889", hist[0.889] == 1, hist[0.889])
check("histogram 2 at 0.778", hist[0.778] == 2, hist[0.778])
check("histogram 1 at 0.7", hist[0.7] == 1, hist[0.7])

by_size = Counter((r["sizes"],) for r in ties)
size_counts = {}
for cell in gap["cells"]:
    size = cell["board_size"]
    n_tied = sum(1 for p in cell["pairs"]
                 if p["tied"] and p["distinct_raw"] and p["exact_gap"] < 1)
    prev_tied, prev_pairs = size_counts.get(size, (0, 0))
    size_counts[size] = (prev_tied + n_tied, prev_pairs + len(cell["pairs"]))
check("size 4 counts 4/1074", size_counts[4] == (4, 1074), size_counts[4])
check("size 6 counts 12/2152", size_counts[6] == (12, 2152), size_counts[6])
check("size 8 counts 15/3585", size_counts[8] == (15, 3585), size_counts[8])
tied_by_size = {}
for cell in gap["cells"]:
    size = cell["board_size"]
    vals = []
    for pair in cell["pairs"]:
        if pair["tied"] and pair["distinct_raw"] and pair["exact_gap"] < 1:
            lk = (size, pair["seed"], pair["pair"][0])
            rk = (size, pair["seed"], pair["pair"][1])
            vals.append(set_jaccard(token_sets[lk], token_sets[rk]))
    tied_by_size.setdefault(size, []).extend(vals)
for size in (4, 6, 8):
    check(f"size {size} tied median 1.0", statistics.median(tied_by_size[size]) == 1.0)

check("reference same token set 778", sum(1 for r in reference if r["same_set"]) == 778,
      sum(1 for r in reference if r["same_set"]))
check("reference same token set share 11.42%",
      abs(sum(1 for r in reference if r["same_set"]) / 6811 - 0.11422698575833211) < 1e-12)

# Exactness decomposition
check("same signature string 0", sum(1 for r in ties if r["same_string"]) == 0)
check("same multiset 15", sum(1 for r in ties if r["same_multi"]) == 15,
      sum(1 for r in ties if r["same_multi"]))
check("same token set 25", sum(1 for r in ties if r["same_set"]) == 25,
      sum(1 for r in ties if r["same_set"]))
check("six pairs below 1.0", sum(1 for r in ties if r["set"] < 1.0) == 6)
classes = {tuple(sorted((token_raw[(t["board_size"], t["seed"], t["types"][0])],
                         token_raw[(t["board_size"], t["seed"], t["types"][1])])))
           for t in pairs}
check("22 unordered signature classes", len(classes) == 22, len(classes))
check("published tied_pairs count 31", len(pairs) == 31)
check("published pairs match private set_jaccard",
      all(abs(p["set_jaccard"] - r["set"]) < 1e-12 for p, r in zip(pairs, ties)))
check("published pairs match private multiset",
      all(abs(p["multiset_jaccard"] - r["multi"]) < 1e-12 for p, r in zip(pairs, ties)))
check("published pair flags match",
      all(p["same_token_set"] == r["same_set"] and
          p["same_move_multiset"] == r["same_multi"] and
          p["same_signature_string"] == r["same_string"] for p, r in zip(pairs, ties)))

# Matched reference
size_pairs = {r["sizes"] for r in ties}
matched = [r for r in reference if r["sizes"] in size_pairs]
matched_non_tied = [r for r in matched if not r["tied"]]
check("matched all n 4992", len(matched) == 4992, len(matched))
check("matched non-tied n 4961", len(matched_non_tied) == 4961, len(matched_non_tied))
check("matched non-tied same set 601",
      sum(1 for r in matched_non_tied if r["same_set"]) == 601)
check("matched non-tied share 12.11%",
      abs(sum(1 for r in matched_non_tied if r["same_set"]) / len(matched_non_tied)
          - 0.12114493045756904) < 1e-12)
check("matched median set 0.77778",
      abs(statistics.median([r["set"] for r in matched]) - 0.7777777777777778) < 1e-12)
check("matched median multiset 0.5375",
      abs(statistics.median([r["multi"] for r in matched]) - 0.5375) < 1e-12)
check("tied multiset median 0.97674",
      abs(statistics.median([r["multi"] for r in ties]) - 0.9767441860465116) < 1e-12)
check("tied multiset percentile 0.992", abs(
    sum(1 for r in matched if r["multi"] <= statistics.median([x["multi"] for x in ties]))
    / len(matched) - 0.9921875) < 1e-12)
check("tied size-pair distribution",
      Counter(f"{a}v{b}" for a, b in (r["sizes"] for r in ties)) ==
      Counter({"8v8": 16, "9v9": 11, "8v9": 2, "9v10": 2}),
      dict(Counter(f"{a}v{b}" for a, b in (r["sizes"] for r in ties))))

# Escaped groups
equal_escaped = [r for r in reference if r["equal_score"]]
distinct_escaped = [r for r in reference
                    if r["distinct_raw"] and r["gap_below_1"] and not r["tied"]]
check("equal-score escaped 17", len(equal_escaped) == 17, len(equal_escaped))
check("distinct-score escaped 5", len(distinct_escaped) == 5, len(distinct_escaped))
check("equal escaped set median 1.0",
      statistics.median([r["set"] for r in equal_escaped]) == 1.0)
check("equal escaped multiset median 1.0",
      statistics.median([r["multi"] for r in equal_escaped]) == 1.0)
check("distinct escaped set median 0.727",
      abs(statistics.median([r["set"] for r in distinct_escaped]) - 0.7272727272727273) < 1e-12)
check("distinct escaped multiset median ~0.5857",
      abs(statistics.median([r["multi"] for r in distinct_escaped]) - 0.5857142857142857) < 1e-12)

# Stored post-hoc block agrees with recomputation
block = res["post_hoc_matched_reference"]
check("stored tied same set", block["tied_same_token_set"]["count"] == 25)
check("stored matched non-tied same set",
      block["matched_reference_excluding_tied_same_token_set"]["count"] == 601)
check("stored non-tied n",
      block["matched_reference_excluding_tied_same_token_set"]["n"] == 4961)
check("stored exactness reconciliation",
      block["exactness_reconciliation"]["matches_stored_post_hoc_exactness"] is True)
check("stored fisher value", abs(block["fisher_two_sided_p"] - 6.568752517523626e-18) < 1e-30)

# Public copy equals private
for name in ("plan.json", "plan-log.json", "analyze_signature_similarity.py",
             "posthoc_matched_reference.py", "results_signature_similarity.json",
             "tied_pairs.json"):
    check(f"public {name} equals private", sha(PUB / name) == sha(PRIV / name))

# README hashes
for line in readme.splitlines():
    if line.startswith("| `"):
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) == 3:
            name = parts[0].strip("`")
            stated = parts[2].strip("`")
            check(f"README hash {name}", sha(PUB / name) == stated, sha(PUB / name))

failures = [c for c in checks if not c["ok"]]
report = {"checks": len(checks), "failures": len(failures),
          "failed": failures, "role": "DEEPSEEK_AUX"}
(PRIV / "results_consistency_audit.json").write_text(
    json.dumps(report, indent=1) + "\n", encoding="utf-8")
print(json.dumps(report, indent=1))
raise SystemExit(1 if failures else 0)
