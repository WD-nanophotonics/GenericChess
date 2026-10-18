"""DEEPSEEK_AUX post-hoc robustness for the movement-signature similarity study.

Appends matched-reference evidence to results_signature_similarity.json.
Descriptive only: no new decision is attached and the pre-registered decision is
not recomputed.  Reference pairs are matched to the tied pairs on the exact
unordered pair of movement-signature token-set sizes, which removes the
token-count composition difference between the two groups.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCAN = ROOT / "docs" / "research" / "data" / "profile_tie_risk_20261018" / "results_tie_risk.json"
GAP = ROOT / ".local_agent" / "profile-tie-risk-20261018" / "results_gap_headroom.json"
RESULTS = HERE / "results_signature_similarity.json"
PAIRS_OUT = HERE / "tied_pairs.json"

scan = json.loads(SCAN.read_text(encoding="utf-8"))
gap = json.loads(GAP.read_text(encoding="utf-8"))

token_sets: dict[tuple[int, int, str], frozenset] = {}
token_lists: dict[tuple[int, int, str], list] = {}
token_raw: dict[tuple[int, int, str], str] = {}
for block in scan["blocks"]:
    for rule in block["rules"]:
        for typ in rule["ordinary_types"]:
            entries = [tuple(e) for e in json.loads(typ["signature"])]
            key = (block["board_size"], rule["seed"], typ["type_id"])
            token_sets[key] = frozenset(entries)
            token_lists[key] = entries
            token_raw[key] = typ["signature"]


def set_jaccard(left: frozenset, right: frozenset) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def multiset_jaccard(left: list, right: list) -> float:
    a, b = Counter(left), Counter(right)
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / union if union else 1.0


def log_choose(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p-value, summed in log space.

    Table layout: [[a, b], [c, d]] with fixed margins.
    """
    row1, row2 = a + b, c + d
    col1 = a + c
    total = row1 + row2
    observed = log_choose(row1, a) + log_choose(row2, c) - log_choose(total, col1)
    logs = []
    for x in range(max(0, col1 - row2), min(row1, col1) + 1):
        logs.append(log_choose(row1, x) + log_choose(row2, col1 - x) - log_choose(total, col1))
    peak = max(logs)
    p = math.exp(peak) * sum(math.exp(v - peak) for v in logs if v <= observed + 1e-12)
    return min(1.0, p)


tied = []
reference = []
for cell in gap["cells"]:
    size = cell["board_size"]
    for pair in cell["pairs"]:
        left_key = (size, pair["seed"], pair["pair"][0])
        right_key = (size, pair["seed"], pair["pair"][1])
        left, right = token_sets[left_key], token_sets[right_key]
        record = {
            "board_size": size,
            "seed": pair["seed"],
            "types": list(pair["pair"]),
            "sizes": sorted([len(left), len(right)]),
            "set_jaccard": set_jaccard(left, right),
            "multiset_jaccard": multiset_jaccard(token_lists[left_key], token_lists[right_key]),
            "same_token_set": left == right,
            "same_move_multiset": sorted(token_lists[left_key]) == sorted(token_lists[right_key]),
            "same_signature_string": token_raw[left_key] == token_raw[right_key],
            "is_tied": False,
        }
        reference.append(record)
        if pair["tied"] and pair["distinct_raw"] and pair["exact_gap"] < 1:
            record["is_tied"] = True
            record["raw_ratio"] = pair["raw_ratio"]
            record["exact_gap"] = pair["exact_gap"]
            tied.append(record)

matched_sizes = {tuple(r["sizes"]) for r in tied}
matched = [r for r in reference if tuple(r["sizes"]) in matched_sizes]

tied_same_set = sum(1 for r in tied if r["set_jaccard"] == 1.0)
tied_same_set_field = sum(1 for r in tied if r["same_token_set"])
tied_same_multiset = sum(1 for r in tied if r["same_move_multiset"])
tied_same_string = sum(1 for r in tied if r["same_signature_string"])
assert tied_same_set == tied_same_set_field
matched_same_set = sum(1 for r in matched if r["set_jaccard"] == 1.0)
matched_non_tied = [r for r in matched if not r["is_tied"]]
matched_non_tied_same = sum(1 for r in matched_non_tied if r["set_jaccard"] == 1.0)
p_value = fisher_two_sided(
    tied_same_set, len(tied) - tied_same_set,
    matched_non_tied_same, len(matched_non_tied) - matched_non_tied_same,
)

tied_set = [r["set_jaccard"] for r in tied]
matched_set = [r["set_jaccard"] for r in matched]
tied_multi = [r["multiset_jaccard"] for r in tied]
matched_multi = [r["multiset_jaccard"] for r in matched]

payload = json.loads(RESULTS.read_text(encoding="utf-8"))
payload["post_hoc_matched_reference"] = {
    "note": "added after the pre-registered run; descriptive only, no new decision",
    "matching_rule": (
        "reference pair is matched when its unordered pair of token-set sizes equals "
        "the size pair of a tied pair; tied size pairs are "
        + ", ".join(f"{a}v{b}" for a, b in sorted(matched_sizes))
    ),
    "tied_same_token_set": {"count": tied_same_set, "n": len(tied),
                            "share": tied_same_set / len(tied)},
    "matched_reference_same_token_set": {"count": matched_same_set, "n": len(matched),
                                         "share": matched_same_set / len(matched)},
    "matched_reference_excluding_tied_same_token_set": {
        "count": matched_non_tied_same,
        "n": len(matched_non_tied),
        "share": matched_non_tied_same / len(matched_non_tied),
    },
    "all_reference_same_token_set": {
        "count": sum(1 for r in reference if r["set_jaccard"] == 1.0),
        "n": len(reference),
        "share": sum(1 for r in reference if r["set_jaccard"] == 1.0) / len(reference),
    },
    "exactness_reconciliation": {
        "same_token_set": tied_same_set_field,
        "same_move_multiset": tied_same_multiset,
        "same_signature_string": tied_same_string,
        "matches_stored_post_hoc_exactness": (
            tied_same_set_field == payload.get("post_hoc_exactness", {}).get("same_token_set")
            and tied_same_multiset == payload.get("post_hoc_exactness", {}).get("same_move_multiset")
            and tied_same_string == payload.get("post_hoc_exactness", {}).get("same_signature_string")
        ),
    },
    "fisher_two_sided_p": p_value,
    "fisher_note": "tied pairs versus matched reference pairs that are not tied; shared "
                   "types and rules make this descriptive, not an independent-sample test",
    "set_jaccard": {
        "tied_median": statistics.median(tied_set),
        "matched_median": statistics.median(matched_set),
        "all_median": statistics.median([r["set_jaccard"] for r in reference]),
        "tied_median_percentile_in_matched": sum(1 for x in matched_set if x <= statistics.median(tied_set)) / len(matched_set),
    },
    "multiset_jaccard": {
        "tied_median": statistics.median(tied_multi),
        "matched_median": statistics.median(matched_multi),
        "tied_median_percentile_in_matched": sum(1 for x in matched_multi if x <= statistics.median(tied_multi)) / len(matched_multi),
    },
    "pair_size": {
        "definition": "unordered pair of distinct-token counts (token-set sizes)",
        "tied_distribution": dict(sorted(Counter(
            f"{r['sizes'][0]}v{r['sizes'][1]}" for r in tied).items())),
        "matched_n": len(matched),
        "all_n": len(reference),
    },
}
RESULTS.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
PAIRS_OUT.write_text(json.dumps({"role": "DEEPSEEK_AUX", "tied_pairs": tied}, indent=1) + "\n",
                     encoding="utf-8")
print(json.dumps(payload["post_hoc_matched_reference"], indent=1))
