"""Write the pre-reference Chess/Shogi first-action service artifact.

The Xiangqi human holdout and all human material references are absent.
Run after the numerical implementation is committed and published.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.first_action_service_pilot import audit_first_action_service

OUTPUT = ROOT / "docs/research/data/first_action_service_chess_shogi_preref.json"
INPUTS = (
    "docs/research/FIRST_ACTION_SERVICE_PILOT_PROTOCOL.md",
    "scripts/freeze_first_action_service_pilot.py",
    "scripts/first_action_service_pilot.py",
    "scripts/intrinsic_action_events.py",
    "scripts/intrinsic_occupancy_cubes.py",
    "scripts/audit_static_semantic_material_prior_v2c.py",
    "generic_chess/rules/western_chess.py",
    "generic_chess/rules/standard_shogi.py",
)


def _fraction_map(mapping: dict) -> dict[str, str]:
    return {key: f"{value.numerator}/{value.denominator}"
            for key, value in sorted(mapping.items())}


def _project(result: dict) -> dict:
    return {
        "ruleset_fingerprint": result["ruleset_fingerprint"],
        "board_area": result["area"],
        "raw_board_exact": _fraction_map(result["raw_board"]),
        "normalized_board_exact": _fraction_map(result["normalized_board"]),
        "raw_held_exact": _fraction_map(result["raw_held"]),
        "normalized_held_exact": _fraction_map(result["normalized_held"]),
        "held_empty_probability_exact": (
            None if result["held_empty_probability"] is None
            else f"{result['held_empty_probability'].numerator}/"
                 f"{result['held_empty_probability'].denominator}"
        ),
        "gauge_exact": f"{result['gauge'].numerator}/{result['gauge'].denominator}",
        "positive_board_events": result["positive_board_events"],
        "occupancy_probability_cache_size": result["occupancy_probability_cache_size"],
        "board_coverage": result["board_coverage"],
        "held_coverage": {
            type_id: {
                "coarse_event_count": row["coarse_event_count"],
                "excluded_state_constraints": row["excluded_state_constraints"],
                "excluded_dynamic": row["excluded_dynamic"],
            }
            for type_id, row in sorted(result["held_coverage"].items())
        },
    }


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/sandbox"],
                                     cwd=ROOT, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain"],
                                     cwd=ROOT, text=True)
    if head != remote or status:
        raise RuntimeError("freeze requires a clean, published sandbox HEAD")
    manifest = {
        "schema_version": 1,
        "classification": "FIRST_ACTION_SERVICE_CHESS_SHOGI_PREREFERENCE",
        "implementation_commit": head,
        "input_sha256": {
            relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in INPUTS
        },
        "human_reference_imported": False,
        "xiangqi_material_reference_imported": False,
        "rulesets": {},
    }
    for name, builder in (("western_chess", build_western_chess_ruleset),
                          ("standard_shogi", build_standard_shogi_ruleset)):
        result = audit_first_action_service(compile_semantic_ruleset(builder()),
                                            max_seconds=60)
        manifest["rulesets"][name] = _project(result)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True,
                                 ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} for {head}")


if __name__ == "__main__":
    main()
