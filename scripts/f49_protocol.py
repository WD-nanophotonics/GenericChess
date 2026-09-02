"""Validation-only authority for the pre-registered F49 H49A protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from generic_chess.learning.serialization import canonical_json


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "h49a_learning_signal_architecture_protocol_manifest.json"
F48_BASELINE_SHA = "4bd25d405af0890668c2940eefc8b68faae1b594"
RULESET_FINGERPRINTS = {
    "A_CANONICAL_WESTERN_CHESS": "7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35",
    "B_CANONICAL_STANDARD_SHOGI": "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635",
    "C_H48B_SELECTED_GENERATED": "9f7e7201a19f8f0ee6c0eacc766c2ac3a6c313e06bbc960d5d6dfb89137db923",
}


def _manifest_sha(manifest: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()


def load_h49a_manifest() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_h49a_manifest(manifest)
    return manifest


def validate_h49a_manifest(manifest: dict[str, Any]) -> None:
    if _manifest_sha(manifest) != manifest.get("manifest_sha256"):
        raise RuntimeError("H49A manifest hash mismatch")
    if manifest.get("baseline_sha") != F48_BASELINE_SHA:
        raise RuntimeError("H49A baseline drift")
    if manifest.get("protocol_status") != "PRE_REGISTERED_NO_OBSERVED_RESULTS":
        raise RuntimeError("H49A is not a no-observations protocol checkpoint")
    if manifest.get("observed_results_present") or manifest.get("measurements_invoked") or manifest.get("learning_invoked"):
        raise RuntimeError("H49A contains observed or executed work")
    if manifest.get("production_diff_required") != "ZERO" or manifest.get("master_promotion") is not False:
        raise RuntimeError("H49A production or promotion scope drift")
    if manifest.get("f49_status") != "DIAGNOSIS_ONLY" or manifest.get("f50_status") != "NOT_STARTED":
        raise RuntimeError("H49A stage status drift")
    if manifest["authority"]["rulesets"] != RULESET_FINGERPRINTS:
        raise RuntimeError("H49A RuleSet fingerprint drift")
    if manifest["authority"]["resolved_seed_triple"] != {"training": 480700, "holdout": 480703, "arena": 480708}:
        raise RuntimeError("H49A H48C seed drift")
    if manifest["control_corpus"]["preserve_results"] is not True:
        raise RuntimeError("H49A does not preserve the F48 control")
    strata = manifest["diagnostic_strata"]
    if set(strata) != {"S49-M", "S49-E"} or any(strata[name]["count"] != 64 for name in strata):
        raise RuntimeError("H49A structural strata drift")
    if any(strata[name]["attempt_cap"] != 100000 for name in strata):
        raise RuntimeError("H49A structural attempt cap drift")
    if manifest["leverage_surfaces"]["L49-0"]["budgets"] != [500, 2000, 8000] or manifest["leverage_surfaces"]["L49-1"]["budgets"] != [500, 2000, 8000]:
        raise RuntimeError("H49A leverage budget surface drift")
    if manifest["teacher_stability_surface"]["adjacent_budget_pairs"] != [[10000, 20000], [20000, 40000], [40000, 80000]]:
        raise RuntimeError("H49A teacher stability surface drift")
    classification = manifest["classification"]
    if classification["precedence"] != list(classification["mapping"]):
        raise RuntimeError("H49A classification precedence is not frozen")
    if manifest["authority"]["f48_r4_erratum"]["fresh_r4_partition_root"] != ".generic_chess_flow/f48-r4-prerequisite-closure-final-v3":
        raise RuntimeError("H49A F48 R4 root erratum drift")
    if len(manifest["authority"]["f48_r4_erratum"]["actual_diff_files"]) != 6:
        raise RuntimeError("H49A F48 R4 diff erratum is incomplete")


if __name__ == "__main__":
    value = load_h49a_manifest()
    print(json.dumps({"status": "PASS", "kind": value["kind"], "next_boundary": value["next_authorized_boundary"]}))
