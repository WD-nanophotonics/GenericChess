"""Freeze the complete pre-reference rule-support source-prior candidate."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_static_material_v2h_rule_support_source_prior import OUTPUT, audit
from scripts.audit_static_material_v2f_lifetime_reachability import _sha

FREEZE = ROOT / ".generic_chess_flow/static-material-v2h-rule-support-source-prior-freeze.json"
FILES = (
    "docs/architecture/ADR-133-rule-support-conditioned-source-prior.md",
    "scripts/audit_static_material_v2h_rule_support_source_prior.py",
    "scripts/freeze_static_material_v2h_rule_support_source_prior.py",
    "tests/test_static_material_v2h_rule_support_source_prior.py",
    ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json",
    ".generic_chess_flow/static-semantic-material-prior-v2c-board.json",
    ".generic_chess_flow/static-semantic-material-prior-v2d-freeze.json",
    ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json",
    ".generic_chess_flow/static-material-domain-fragmentation-freeze.json",
    ".generic_chess_flow/static-material-domain-fragmentation-topology.json",
)


def freeze() -> dict[str, Any]:
    if not OUTPUT.is_file():
        raise RuntimeError("Rule-support source-prior candidate is missing")
    candidate = json.loads(OUTPUT.read_text(encoding="utf-8"))
    reproduced = audit()
    if candidate != reproduced:
        raise RuntimeError("Candidate differs from deterministic frozen-input reconstruction")
    if candidate.get("classification") != "STATIC_MATERIAL_RULE_SUPPORT_CONDITIONED_SOURCE_PRIOR_COMPLETE":
        raise RuntimeError("Cannot freeze an incomplete source-prior candidate")
    for key in ("human_reference_imported", "human_validation_performed", "production_evaluator_modified"):
        if candidate.get(key) is not False:
            raise RuntimeError(f"Candidate crosses the pre-reference boundary: {key}")
    if candidate.get("games_played") != 0:
        raise RuntimeError("Candidate phase must remain zero-game")
    output = {
        "kind": "STATIC_MATERIAL_RULE_SUPPORT_CONDITIONED_SOURCE_PRIOR_PRE_REFERENCE_FREEZE",
        "classification": candidate["classification"],
        "candidate_sha256": _sha(OUTPUT),
        "human_reference_read": False,
        "human_validation_performed": False,
        "games_played": 0,
        "support_gates_pass": candidate["support_gates_pass"],
        "reconstruction_complete": candidate["reconstruction_complete"],
        "input_sha256": candidate["input_sha256"],
        "source_sha256": {relative: _sha(ROOT / relative) for relative in FILES},
        "candidate_vectors": {
            ruleset: {type_id: {
                "u_support_exact": row["u_support_exact"],
                "c_support_exact": row["c_support_exact"],
                "b_support_exact": row["b_support_exact"],
            } for type_id, row in data["types"].items()}
            for ruleset, data in candidate["rulesets"].items()
        },
        "support_set_digests": {
            ruleset: data["support_digests"] for ruleset, data in candidate["rulesets"].items()
        },
    }
    FREEZE.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main() -> int:
    frozen = freeze()
    print(json.dumps({"freeze": str(FREEZE), "candidate_sha256": frozen["candidate_sha256"],
                      "classification": frozen["classification"],
                      "human_reference_read": frozen["human_reference_read"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
