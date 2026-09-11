"""Freeze and run the F87A ruleset-qualification toolbox foundation.

F87A deliberately stops at compiler/core correctness, shared structural
diagnostics, and a tiny generator-independent Common-Tape calibration.  No
native search, Arena, training, or Heavy work belongs in this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from generic_chess.benchmark.qualification import (
    STATUS_DEFER,
    STATUS_PASS,
    STATUS_UNMEASURED,
    calibration_reason_codes,
    common_tape_games,
    qualification_report,
    structural_profile,
)
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


BASELINE_SHA = "a33ff404d33aef1d6717fc62e05337ae92691540"
ARTIFACT_DIR = Path("artifacts/f87a_ruleset_qualification")
PREP_PATH = ARTIFACT_DIR / "manifest.json"
SUMMARY_PATH = ARTIFACT_DIR / "summary.json"
REPORTS_PATH = ARTIFACT_DIR / "reports.json"
PAIR_COUNT = 2
MAX_PLY = 32
TAPE_LENGTH = 32
SEED = 8701

EXPECTED_FINGERPRINTS = {
    "F86C legacy V4-3": "7e2ff9e15c2a0d1be5faa8c6697f22e488976a2d2ae9f077b85c6e71f95ff400",
    "F86I full-reverse V4-3": "8ca58376a52e539c7c8519e902b8dd9e6991b002586d36d846a7a864fffea05d",
    "F86N-R1 boundary V4-3": "856a810d3a21eec779f9ba8300ce602cd24d3e8850ba895e39579603fd4ff3e2",
    "F86N-R1 boundary V5-3": "e8528688a64bce3f39231d9e4f38d5d200ade57c6f517ae33ce9b71b9f75ebe5",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_controls(root: Path) -> list[dict[str, Any]]:
    f86c_path = root / "artifacts/f86c_generator_viability/rulesets.json"
    f86c = _load_json(f86c_path)
    f86c_row = next(row for row in f86c["sample"] if row["sample_id"] == "V4-3")

    f86i_path = root / "artifacts/f86i_reversibility_rescue/manifest.json"
    f86i = _load_json(f86i_path)
    f86i_row = next(row for row in f86i["entries"] if row["sample_id"] == "V4-3")

    f86n_path = root / "artifacts/f86n_r1_transport_aware_signed_sampler/manifest.json"
    f86n = _load_json(f86n_path)
    f86n_rows = {row["sample_id"]: row for row in f86n["entries"]}

    return [
        {
            "name": "F86C legacy V4-3",
            "class": "negative",
            "source_kind": "F86C_LEGACY_V4_3",
            "source_path": f86c_path.relative_to(root).as_posix(),
            "source_sha256": _sha256(f86c_path),
            "ruleset": f86c_row["ruleset"],
            "expected_fingerprint": EXPECTED_FINGERPRINTS["F86C legacy V4-3"],
        },
        {
            "name": "F86I full-reverse V4-3",
            "class": "negative",
            "source_kind": "F86I_FULL_REVERSE_V4_3",
            "source_path": f86i_path.relative_to(root).as_posix(),
            "source_sha256": _sha256(f86i_path),
            "ruleset": f86i_row["candidate_ruleset"],
            "expected_fingerprint": EXPECTED_FINGERPRINTS["F86I full-reverse V4-3"],
        },
        {
            "name": "F86N-R1 boundary V4-3",
            "class": "boundary",
            "source_kind": "F86N_R1_BOUNDARY_V4_3",
            "source_path": f86n_path.relative_to(root).as_posix(),
            "source_sha256": _sha256(f86n_path),
            "ruleset": f86n_rows["V4-3"]["candidate_ruleset"],
            "expected_fingerprint": EXPECTED_FINGERPRINTS["F86N-R1 boundary V4-3"],
        },
        {
            "name": "F86N-R1 boundary V5-3",
            "class": "boundary",
            "source_kind": "F86N_R1_BOUNDARY_V5_3",
            "source_path": f86n_path.relative_to(root).as_posix(),
            "source_sha256": _sha256(f86n_path),
            "ruleset": f86n_rows["V5-3"]["candidate_ruleset"],
            "expected_fingerprint": EXPECTED_FINGERPRINTS["F86N-R1 boundary V5-3"],
        },
    ]


def _builtin_controls() -> list[dict[str, Any]]:
    return [
        {
            "name": "Built-in Western Chess",
            "class": "positive_semantic",
            "source_kind": "BUILTIN_WESTERN_CHESS",
            "source_path": "generic_chess.rules.western_chess.build_western_chess_ruleset",
            "source_sha256": "builtin",
            "builder": build_western_chess_ruleset,
        },
        {
            "name": "Built-in Standard Shogi",
            "class": "positive_semantic",
            "source_kind": "BUILTIN_STANDARD_SHOGI",
            "source_path": "generic_chess.rules.standard_shogi.build_standard_shogi_ruleset",
            "source_sha256": "builtin",
            "builder": build_standard_shogi_ruleset,
        },
    ]


def _controls(root: Path) -> list[dict[str, Any]]:
    return _artifact_controls(root) + _builtin_controls()


def _expected_role(control: dict[str, Any]) -> dict[str, Any]:
    if control["class"] == "negative":
        if control["name"].startswith("F86I"):
            return {"layer_b": "FAIL_KNOWN_NEGATIVE", "reason_codes": ["HIGH_LOCAL_REVERSIBILITY", "TERMINAL_TEMPLATE_TRANSPORT_INSUFFICIENT"]}
        return {"layer_b": "FAIL_KNOWN_NEGATIVE", "reason_codes": ["LATTICE_RANK_DEFICIT", "ONE_WAY_TRANSPORT", "CALIBRATION_NEGATIVE_ENVIRONMENT_AUTHORITY"]}
    if control["class"] == "boundary":
        return {"layer_b": "BOUNDARY_WITNESS_DEFER", "reason_codes": ["STRUCTURAL_BACKBONE_WITNESS", "BOUNDARY_NOT_ADMISSION"]}
    return {"layer_b": "SEMANTIC_MOVEMENT_DEFER", "reason_codes": ["SEMANTIC_MOVEMENT_NOT_APPLICABLE"]}


def _semantic_type_ids(control: dict[str, Any]) -> set[str]:
    if "builder" not in control:
        return set()
    return {type_id for action in control["builder"]().semantic_actions for type_id in action.type_ids}


def _terminal_transport(root: Path, compiled) -> dict[str, Any]:
    authority_path = root / "artifacts/f86l_mate_template_transport_support/diagnosis.json"
    if not authority_path.exists():
        return {"status": STATUS_DEFER, "reason_code": "TERMINAL_TRANSPORT_AUTHORITY_UNAVAILABLE", "applicability": "DEFER"}
    authority = _load_json(authority_path)
    if authority.get("f86i_full_closure_fingerprint") != compiled.ruleset_fingerprint:
        return {"status": STATUS_DEFER, "reason_code": "TERMINAL_TRANSPORT_NOT_APPLICABLE", "applicability": "DEFER"}
    census = authority["authorized_census"]
    return {
        "status": STATUS_DEFER,
        "reason_code": "TERMINAL_TEMPLATE_TRANSPORT_INSUFFICIENT",
        "applicability": "APPLICABLE",
        "authority_source": "artifacts/f86l_mate_template_transport_support/diagnosis.json",
        "validated_template_count": census["validated_templates"],
        "complete_template_count": len(authority["full_closure_reference"]["complete_template_ids"]),
        "routing": authority["routing"],
        "census_truncated": census["truncation"],
    }


def _calibration_authority(root: Path, control: dict[str, Any], compiled) -> dict[str, Any] | None:
    if control["class"] != "negative":
        return None
    if control["name"].startswith("F86I"):
        authority_path = root / "artifacts/f86l_mate_template_transport_support/diagnosis.json"
        return {
            "status": "FAIL",
            "authority_kind": "F86L_FROZEN_TERMINAL_TRANSPORT_COUNTEREXAMPLE",
            "authority_path": authority_path.relative_to(root).as_posix(),
            "authority_sha256": _sha256(authority_path),
            "authority_fingerprint": compiled.ruleset_fingerprint,
            "reason_code": "TERMINAL_TEMPLATE_TRANSPORT_INSUFFICIENT",
            "applicability": "APPLICABLE",
            "evidence_status": "frozen_authority",
        }
    authority_path = root / "artifacts/f86c_generator_viability/results.json"
    authority = _load_json(authority_path)
    row = next(row for row in authority["quality"] if row["sample_id"] == "V4-3" and row["ruleset_fingerprint"] == compiled.ruleset_fingerprint)
    return {
        "status": "FAIL",
        "authority_kind": "F86C_FROZEN_DYNAMIC_NEGATIVE_CONTROL",
        "authority_path": authority_path.relative_to(root).as_posix(),
        "authority_sha256": _sha256(authority_path),
        "authority_fingerprint": compiled.ruleset_fingerprint,
        "reason_code": "CALIBRATION_NEGATIVE_ENVIRONMENT_AUTHORITY",
        "applicability": "APPLICABLE",
        "evidence_status": "frozen_authority",
        "historical_terminal_distribution": row["terminal_distribution"],
        "historical_stalemate_fraction": authority["stalemate_fraction"],
        "historical_played_game_count": authority["played_game_count"],
    }


def _compiled(control: dict[str, Any]):
    if "builder" in control:
        ruleset = control["builder"]()
    else:
        ruleset = ruleset_from_dict(control["ruleset"])
    compiled = compile_ruleset(ruleset, allow_semantic_actions=bool(ruleset.semantic_actions))
    expected = control.get("expected_fingerprint")
    if expected is not None and compiled.ruleset_fingerprint != expected:
        raise RuntimeError(
            f"{control['name']} fingerprint mismatch: "
            f"expected {expected}, got {compiled.ruleset_fingerprint}"
        )
    return compiled


def _dynamic_supported(control: dict[str, Any]) -> bool:
    """Legacy GameSession cannot execute the built-ins' semantic-action DSL."""
    if "builder" not in control:
        return True
    return not bool(control["builder"]().semantic_actions)


def build_prep(root: Path, output: Path = PREP_PATH) -> dict[str, Any]:
    controls = []
    for control in _controls(root):
        compiled = _compiled(control)
        controls.append({
            "name": control["name"],
            "class": control["class"],
            "source_kind": control["source_kind"],
            "source_path": control["source_path"],
            "source_sha256": control["source_sha256"],
            "ruleset_fingerprint": compiled.ruleset_fingerprint,
            "expected_role": _expected_role(control),
        })
    prep = {
        "schema_version": 1,
        "experiment": "GENERICCHESS-F87A-RULESET-QUALIFICATION-TOOLBOX-FOUNDATION",
        "status": "PREP_FROZEN",
        "baseline_sha": BASELINE_SHA,
        "controls": controls,
        "allowed_statuses": ["PASS", "FAIL", "DEFER", "UNMEASURED"],
        "provenance_classes": [
            "LITERATURE_SUPPORTED", "GENERICCHESS_SPECIFIC", "EMPIRICAL_GATE", "UNVALIDATED_HEURISTIC"
        ],
        "layers": {
            "A": {"name": "compiler/core correctness", "hard_gate": "PASS", "qualification_note": "Layer A is necessary, not sufficient"},
            "B": {"name": "shared structural probe", "hard_gate": "diagnostic; no universal rank/index gate"},
            "C": {"name": "bounded Common-Tape dynamics", "hard_gate": "replay identity and metric completeness"},
            "D": {"name": "paired strength response", "hard_gate": "DEFERRED_IN_F87A"},
            "E": {"name": "learning/evaluator adapter", "hard_gate": "DEFERRED_IN_F87A"},
        },
        "metric_definitions": {
            "ongoing_at_max_ply": "CENSORED/UNRESOLVED; never a draw",
            "lattice": "displacement generators, integer rank, lattice index/residue",
            "transport": "finite-board reachability, SCC/component, sink fraction, reverse-edge fraction",
            "opening_transport": "opening-source reachable coverage, same-type union coverage, component diversity",
            "material": "materialized type profile from opening position",
            "dynamic": "terminal/completion/checkmate/decisive/stalemate/repetition/censored, game length, branching, legal-action collapse, capture/check density, side bias, opening identity sensitivity",
            "universal_gate": "not applied; F86N rank-2/index-1 is diagnostic and empirical only",
            "canonical_actions": "sorted action_to_dict JSON with sort_keys and compact separators before PolicyTape indexing",
            "side_bias": "CENSORED games have null scores and do not enter the score denominator",
            "opening_sensitivity": "UNMEASURED when fewer than two opening identities are present",
            "qualification_target": "PLAYABILITY requires Layers A-C; replay identity is integrity-only",
        },
        "budgets": {
            "pair_count": PAIR_COUNT,
            "max_ply": MAX_PLY,
            "tape_length": TAPE_LENGTH,
            "search_nodes": 0,
            "arena_games": 0,
            "training_steps": 0,
            "heavy_jobs": 0,
        },
        "expectations": {
            "overall_status": "CALIBRATION_MIXED_OUTCOMES",
            "negative_control_status": "FAIL",
            "boundary_control_status": "DEFER",
            "semantic_control_status": "DEFER",
            "negative_controls_not_fully_qualified": True,
            "f86n_boundary_status": "DEFER",
            "builtins_not_universally_failed_by_piece_local_heuristic": True,
            "terminal_probe": "DEFER if semantic contract is not applicable or insufficient",
        },
        "prohibited_compute": ["native search", "large Arena", "training", "Heavy", "large Gen1-to-GenN", "C2", "F85", "full QD/MAP-Elites"],
    }
    _write_json(output, prep)
    return prep


def _load_prep(path: Path) -> dict[str, Any]:
    prep = _load_json(path)
    if prep.get("status") != "PREP_FROZEN" or prep.get("baseline_sha") != BASELINE_SHA:
        raise RuntimeError("F87A PREP manifest is not frozen at the authorized baseline")
    if len(prep.get("controls", [])) != 6:
        raise RuntimeError("F87A calibration suite must contain six controls")
    return prep


def run(root: Path, prep_path: Path = PREP_PATH, result_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    prep = _load_prep(prep_path)
    controls = {control["name"]: control for control in _controls(root)}
    reports: dict[str, Any] = {}
    for identity in prep["controls"]:
        control = controls[identity["name"]]
        compiled = _compiled(control)
        if compiled.ruleset_fingerprint != identity["ruleset_fingerprint"]:
            raise RuntimeError(f"F87A PREP fingerprint drift for {identity['name']}")
        if identity["expected_role"] != _expected_role(control):
            raise RuntimeError(f"F87A PREP qualitative expectation drift for {identity['name']}")
        structural = structural_profile(compiled, semantic_type_ids=_semantic_type_ids(control))
        terminal_transport = _terminal_transport(root, compiled)
        calibration_authority = _calibration_authority(root, control, compiled)
        reason_codes = calibration_reason_codes(
            structural,
            control_class=control["class"],
            terminal_transport=terminal_transport,
        )
        if _dynamic_supported(control):
            dynamic = common_tape_games(
                compiled,
                pair_count=PAIR_COUNT,
                max_ply=MAX_PLY,
                seed=SEED,
                tape_length=TAPE_LENGTH,
            )
            replay = common_tape_games(
                compiled,
                pair_count=PAIR_COUNT,
                max_ply=MAX_PLY,
                seed=SEED,
                tape_length=TAPE_LENGTH,
            )
            replay_equal = dynamic == replay
            dynamic_status = STATUS_PASS
        else:
            dynamic = {
                "status": "UNMEASURED",
                "reason": "semantic-action ruleset requires the semantic runtime; legacy Common-Tape is not applicable",
                "records": [],
                "censored_count": 0,
            }
            replay_equal = True
            dynamic_status = STATUS_UNMEASURED
        report = qualification_report(
            compiled=compiled,
            provenance=identity,
            experiment_identity=f"F87A/{identity['name']}",
            structural=structural,
            dynamic=dynamic,
            replay_equal=replay_equal,
            dynamic_status=dynamic_status,
            control_class=control["class"],
            control_name=control["name"],
            layer_b_reason_codes=reason_codes,
            terminal_transport=terminal_transport,
            calibration_authority=calibration_authority,
        ).to_dict()
        expected_overall = "FAIL" if control["class"] == "negative" else STATUS_DEFER
        if report["overall_status"] != expected_overall:
            raise RuntimeError(f"F87A expected {expected_overall} for {identity['name']}")
        expected_codes = set(identity["expected_role"]["reason_codes"])
        if not expected_codes.intersection(report["reason_codes"]):
            raise RuntimeError(f"F87A calibration expectation not observed for {identity['name']}: {report['reason_codes']}")
        reports[identity["name"]] = report

    summary = {
        "schema_version": 1,
        "experiment": prep["experiment"],
        "status": "RESULT_COMPLETE",
        "baseline_sha": BASELINE_SHA,
        "prep_manifest": str(prep_path),
        "controls": list(reports),
        "overall_status": "CALIBRATION_MIXED_OUTCOMES",
        "control_overall_status": {name: report["overall_status"] for name, report in reports.items()},
        "layer_status": {"A": STATUS_PASS, "B": "MIXED_FAIL_DEFER", "C": STATUS_DEFER, "D": STATUS_DEFER, "E": STATUS_DEFER},
        "compute_usage": {"search_nodes": 0, "arena_games": 0, "training_steps": 0, "heavy_jobs": 0},
        "calibration_expectations": prep["expectations"],
    }
    _write_json(result_dir / "summary.json", summary)
    _write_json(result_dir / "reports.json", reports)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--prep", action="store_true")
    parser.add_argument("--manifest-output", type=Path, default=None)
    parser.add_argument("--result", action="store_true")
    parser.add_argument("--result-dir", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.prep:
        output = args.manifest_output or (root / PREP_PATH)
        build_prep(root, output)
    if args.result:
        prep = root / PREP_PATH
        result_dir = args.result_dir or (root / ARTIFACT_DIR)
        run(root, prep, result_dir)
    if not args.prep and not args.result:
        parser.error("choose --prep or --result")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
