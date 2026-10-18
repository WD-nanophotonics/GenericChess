"""DEEPSEEK_AUX: movement-signature similarity of rounding-tied pairs.

Pre-registered in plan.json (plan_sha in plan-log.json).  Reads only stored
results; generates no rule and runs no search.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN = ROOT / "docs" / "research" / "data" / "profile_tie_risk_20261018" / "results_tie_risk.json"
GAP = ROOT / ".local_agent" / "profile-tie-risk-20261018" / "results_gap_headroom.json"
OUT = Path(__file__).resolve().parent / "results_signature_similarity.json"

scan = json.loads(SCAN.read_text(encoding="utf-8"))
gap = json.loads(GAP.read_text(encoding="utf-8"))

sig: dict[tuple[int, int, str], frozenset] = {}
for block in scan["blocks"]:
    for rule in block["rules"]:
        for typ in rule["ordinary_types"]:
            tokens = frozenset(tuple(entry) for entry in json.loads(typ["signature"]))
            sig[(block["board_size"], rule["seed"], typ["type_id"])] = tokens


def jaccard(left: frozenset, right: frozenset) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def percentile_of(value: float, reference: list[float]) -> float:
    return sum(1 for x in reference if x <= value) / len(reference)


pooled_tied = []
pooled_ref = []
by_size = {}
for cell in gap["cells"]:
    size = cell["board_size"]
    tied = []
    ref = []
    for pair in cell["pairs"]:
        left = sig[(size, pair["seed"], pair["pair"][0])]
        right = sig[(size, pair["seed"], pair["pair"][1])]
        value = jaccard(left, right)
        ref.append(value)
        if pair["tied"] and pair["distinct_raw"] and pair["exact_gap"] < 1:
            tied.append(value)
    pooled_tied.extend(tied)
    pooled_ref.extend(ref)
    by_size.setdefault(size, {"tied": [], "ref": []})
    by_size[size]["tied"].extend(tied)
    by_size[size]["ref"].extend(ref)


def summarise(tied: list[float], ref: list[float]) -> dict:
    med = statistics.median(tied)
    return {
        "tied_n": len(tied),
        "reference_n": len(ref),
        "tied_median": med,
        "tied_q1": statistics.quantiles(tied, n=4)[0] if len(tied) > 1 else med,
        "tied_q3": statistics.quantiles(tied, n=4)[2] if len(tied) > 1 else med,
        "reference_median": statistics.median(ref),
        "reference_p90": statistics.quantiles(ref, n=10)[8],
        "tied_median_percentile_in_reference": percentile_of(med, ref),
        "tied_histogram": dict(sorted(Counter(round(x, 3) for x in tied).items())),
    }


pooled = summarise(pooled_tied, pooled_ref)
if pooled["tied_median_percentile_in_reference"] >= 0.90:
    decision = "benign_concentration"
elif pooled["tied_median_percentile_in_reference"] <= 0.75:
    decision = "dissimilar_ties"
else:
    decision = "inconclusive_similarity"

payload = {
    "role": "DEEPSEEK_AUX",
    "plan_sha256": json.loads(
        (Path(__file__).resolve().parent / "plan-log.json").read_text(encoding="utf-8")
    )["plan_sha256"],
    "inputs": {
        "scan": str(SCAN.relative_to(ROOT)).replace("\\", "/"),
        "gap": ".local_agent/profile-tie-risk-20261018/results_gap_headroom.json",
    },
    "new_rules": 0,
    "search": "none",
    "pooled": pooled,
    "by_board_size": {str(k): summarise(v["tied"], v["ref"]) for k, v in sorted(by_size.items())},
    "decision": decision,
    "nonclaims": [
        "syntactic movement similarity is not strategic equivalence",
        "small tied set (31 pairs, 22 signature classes)",
        "one generator family, hand_weight 0.9",
        "no strength, utility or human-price claim",
    ],
}
OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
print(json.dumps({"decision": decision, "pooled": pooled,
                  "by_board_size": payload["by_board_size"]}, indent=1))
