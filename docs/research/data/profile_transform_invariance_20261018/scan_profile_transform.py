"""Zero-search transform-invariance scan of the served static profile.

Pre-registered plan: ``plan.json`` (its SHA-256 is recorded in the output).
Transforms, all on the 40 already-used deterministic seeds 292001-292040 at
board sizes 6 and 8 (``classic_like``, ``hand_weight=0.9``):

  A1 (primary)  180-degree rotation of every movement atom
                (``coordinates.rotate_offset``); every other RuleSet field is
                left exactly as the generator emitted it.  Type ids are kept.
  A2 (secondary) the same atom rotation, but the generator-owned drop masks
                and promotion zones are re-derived from the rotated atoms, so
                the transformed ruleset is self-consistent.  Recorded apart
                and not part of the pre-written decision.
  B  (primary)  relabeling of type ids by a fixed permutation that also
                reverses id order, remapping every id-keyed field (piece
                types, promotion targets, initial position, drop/promotion
                masks).  Atoms and geometry are untouched.

Endpoint: per-type ``normalized_board_value``, ``normalized_hand_value``,
``promotion_option_value`` and the per-rule ``median_non_anchor_value``.
A violation is any mismatch under the bijection that preserves the movement
signature multiset.  No search, no learning, no fitness, no new seeds.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
import traceback
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.core.coordinates import rotate_offset  # noqa: E402
from generic_chess.core.movement import LeapAtom, RayAtom  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.drop_derivation import derive_drop_mask  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402
from generic_chess.generation.promotion_derivation import (  # noqa: E402
    derive_promotion_data,
)
from generic_chess.rules.compiler import compile_ruleset  # noqa: E402
from generic_chess.rules.schema import (  # noqa: E402
    ruleset_from_dict,
    ruleset_to_dict,
)

SEEDS = tuple(range(292001, 292041))
SIZES = (6, 8)
HAND_WEIGHT = 0.9
OUT = HERE / "results_profile_transform.json"
SOURCE_FILES = (
    "generic_chess/ai/evaluation/config.py",
    "generic_chess/ai/evaluation/profile.py",
    "generic_chess/ai/evaluation/analyzer.py",
    "generic_chess/ai/evaluation/mobility.py",
    "generic_chess/ai/evaluation/movement_graph.py",
    "generic_chess/core/coordinates.py",
    "generic_chess/core/movement.py",
    "generic_chess/generation/generator.py",
    "generic_chess/generation/drop_derivation.py",
    "generic_chess/generation/promotion_derivation.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rotate_atom(atom):
    if isinstance(atom, LeapAtom):
        return LeapAtom(rotate_offset(atom.offset))
    return RayAtom(rotate_offset(atom.direction), atom.max_steps)


def signature_entries(signature: str) -> list[list]:
    return sorted([list(item) for item in json.loads(signature)])


def negated_signature_entries(signature: str) -> list[list]:
    out = []
    for kind, df, dr, *rest in signature_entries(signature):
        out.append([kind, -df, -dr, *rest])
    return sorted(out)


def profile_rows(profile) -> dict:
    rows = {}
    for type_id, item in sorted(profile.piece_profiles.items()):
        rows[type_id] = {
            "board": int(item.normalized_board_value),
            "hand": int(item.normalized_hand_value),
            "promotion": int(item.promotion_option_value),
            "raw": float(item.raw_capability_score),
            "signature": item.movement_signature,
            "drop_freedom": float(item.drop_freedom_ratio),
            "drop_mobility": float(item.drop_mobility),
            "is_anchor": bool(item.is_anchor),
            "is_promotable": bool(item.is_promotable),
        }
    return rows


def compare_profiles(
    original, transformed, *, match_key, signature_check: str
) -> dict:
    """Compare two profiles under ``match_key(original_type_id) -> transformed id``."""
    orig_rows = profile_rows(original)
    new_rows = profile_rows(transformed)
    violations = []
    signature_failures = []
    raw_delta = 0.0
    raw_exact = 0
    drop_delta_types = []
    for type_id, row in orig_rows.items():
        mapped = match_key(type_id)
        if mapped not in new_rows:
            violations.append(
                {
                    "type_id": type_id,
                    "field": "missing_type",
                    "expected": mapped,
                    "actual": None,
                }
            )
            continue
        other = new_rows[mapped]
        if signature_check == "negated":
            expected_signature = negated_signature_entries(row["signature"])
            ok = expected_signature == signature_entries(other["signature"])
        else:
            expected_signature = signature_entries(row["signature"])
            ok = expected_signature == signature_entries(other["signature"])
        if not ok:
            signature_failures.append(
                {
                    "type_id": type_id,
                    "expected": expected_signature,
                    "actual": signature_entries(other["signature"]),
                }
            )
        for field in ("board", "hand", "promotion", "is_anchor", "is_promotable"):
            if row[field] != other[field]:
                violations.append(
                    {
                        "type_id": type_id,
                        "mapped_type_id": mapped,
                        "field": field,
                        "expected": row[field],
                        "actual": other[field],
                        "is_anchor": row["is_anchor"],
                        "is_promotable": row["is_promotable"],
                    }
                )
        delta = abs(row["raw"] - other["raw"])
        raw_delta = max(raw_delta, delta)
        if row["raw"] == other["raw"]:
            raw_exact += 1
        if (
            row["drop_freedom"] != other["drop_freedom"]
            or row["drop_mobility"] != other["drop_mobility"]
        ):
            drop_delta_types.append(type_id)
    median_match = original.median_non_anchor_value == transformed.median_non_anchor_value
    if not median_match:
        violations.append(
            {
                "type_id": None,
                "field": "median_non_anchor_value",
                "expected": int(original.median_non_anchor_value),
                "actual": int(transformed.median_non_anchor_value),
            }
        )
    return {
        "types": len(orig_rows),
        "violations": violations,
        "signature_failures": signature_failures,
        "median_non_anchor_value": {
            "original": int(original.median_non_anchor_value),
            "transformed": int(transformed.median_non_anchor_value),
            "match": median_match,
        },
        "raw_exact_matches": raw_exact,
        "raw_max_abs_delta": raw_delta,
        "drop_term_changed_types": drop_delta_types,
    }


def rotated_atom_types(ruleset):
    return tuple(
        replace(
            piece_type,
            movement_atoms=tuple(rotate_atom(atom) for atom in piece_type.movement_atoms),
        )
        for piece_type in ruleset.piece_types
    )


def transform_a1(ruleset):
    """Rotate movement atoms only; leave derived masks untouched."""
    return replace(ruleset, piece_types=rotated_atom_types(ruleset)), {
        "piece_types": lambda type_id: type_id
    }


def transform_a2(ruleset):
    """Rotate atoms and re-derive the generator-owned mask data."""
    n = ruleset.board_size
    types = rotated_atom_types(ruleset)
    drop = {}
    promotion_allowed = {}
    promotion_forced = {}
    for piece_type in types:
        if piece_type.is_anchor:
            continue
        drop[piece_type.type_id] = (
            derive_drop_mask(n, 0, piece_type.movement_atoms),
            derive_drop_mask(n, 1, piece_type.movement_atoms),
        )
        if piece_type.is_promotable:
            pa0, pf0 = derive_promotion_data(n, 0, piece_type.movement_atoms)
            pa1, pf1 = derive_promotion_data(n, 1, piece_type.movement_atoms)
            promotion_allowed[piece_type.type_id] = (pa0, pa1)
            promotion_forced[piece_type.type_id] = (pf0, pf1)
    return (
        replace(
            ruleset,
            piece_types=types,
            drop_allowed=drop,
            promotion_allowed=promotion_allowed,
            promotion_forced=promotion_forced,
        ),
        {"piece_types": lambda type_id: type_id},
    )


def relabel_map(ruleset) -> dict:
    ids = sorted(piece_type.type_id for piece_type in ruleset.piece_types)
    return {
        type_id: f"z{index:02d}" for index, type_id in enumerate(reversed(ids))
    }


def transform_b(ruleset):
    """Relabel every type id by a fixed order-reversing permutation."""
    mapping = relabel_map(ruleset)
    inverse = {value: key for key, value in mapping.items()}

    def remap_id(type_id):
        return mapping[type_id]

    types = tuple(
        replace(
            piece_type,
            type_id=remap_id(piece_type.type_id),
            name=f"renamed:{piece_type.name}",
            promotion_target_ids=tuple(
                remap_id(target) for target in piece_type.promotion_target_ids
            ),
        )
        for piece_type in ruleset.piece_types
    )

    def remap_position(rows):
        return tuple(
            tuple(
                None
                if cell is None
                else replace(
                    cell,
                    base_type_id=remap_id(cell.base_type_id),
                    current_type_id=remap_id(cell.current_type_id),
                )
                for cell in row
            )
            for row in rows
        )

    transformed = replace(
        ruleset,
        piece_types=types,
        initial_position=remap_position(ruleset.initial_position),
        drop_allowed={
            remap_id(key): value for key, value in ruleset.drop_allowed.items()
        },
        promotion_allowed={
            remap_id(key): value for key, value in ruleset.promotion_allowed.items()
        },
        promotion_forced={
            remap_id(key): value for key, value in ruleset.promotion_forced.items()
        },
        initial_setup_options=tuple(
            replace(option, position=remap_position(option.position))
            for option in ruleset.initial_setup_options
        ),
    )
    return transformed, {"piece_types": lambda type_id: mapping[type_id], "inverse": inverse}


TRANSFORMS = (
    ("A1_atom_rotation", transform_a1, "negated"),
    ("A2_rotation_rederived", transform_a2, "negated"),
    ("B_type_relabel", transform_b, "identical"),
)


def scan_rule(seed: int, size: int) -> dict:
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
    )
    ruleset = game.ruleset
    compiled = game.compiled_ruleset
    config = EvaluationConfig(hand_weight=HAND_WEIGHT)
    original = build_ruleset_profile(compiled, config)

    # Control: a serialize/parse round-trip must be value-identical.
    round_trip = compile_ruleset(ruleset_from_dict(ruleset_to_dict(ruleset)))
    round_trip_profile = build_ruleset_profile(round_trip, config)
    control = {
        "fingerprint_match": round_trip.ruleset_fingerprint
        == compiled.ruleset_fingerprint,
        "profile_identical": profile_rows(round_trip_profile) == profile_rows(original),
        "median_identical": round_trip_profile.median_non_anchor_value
        == original.median_non_anchor_value,
    }

    results = {}
    for name, builder, signature_check in TRANSFORMS:
        record = {
            "status": "supported",
            "error": None,
            "fingerprint_changed": None,
            "comparison": None,
        }
        try:
            transformed_ruleset, keys = builder(ruleset)
            transformed = compile_ruleset(transformed_ruleset)
            record["fingerprint_changed"] = (
                transformed.ruleset_fingerprint != compiled.ruleset_fingerprint
            )
            transformed_profile = build_ruleset_profile(transformed, config)
            match_key = keys["piece_types"]
            comparison = compare_profiles(
                original,
                transformed_profile,
                match_key=match_key,
                signature_check=signature_check,
            )
            record["comparison"] = comparison
            if comparison["signature_failures"]:
                record["status"] = "transform_mismatch"
        except Exception as exc:  # feasibility gate: record, never fabricate
            record["status"] = "unsupported"
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["traceback_tail"] = traceback.format_exc().splitlines()[-6:]
        results[name] = record

    return {
        "seed": seed,
        "board_size": size,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "piece_types": [
            {
                "type_id": piece_type.type_id,
                "anchor": piece_type.is_anchor,
                "promotable": piece_type.is_promotable,
                "atoms": [str(atom) for atom in piece_type.movement_atoms],
            }
            for piece_type in ruleset.piece_types
        ],
        "round_trip_control": control,
        "transforms": results,
    }


def decide(rules: list[dict]) -> dict:
    """Apply the pre-written decision rule to the primary transforms."""
    summary = {}
    for name in ("A1_atom_rotation", "B_type_relabel"):
        supported = [
            rule
            for rule in rules
            if rule["transforms"][name]["status"] == "supported"
        ]
        unsupported = [
            rule
            for rule in rules
            if rule["transforms"][name]["status"] == "unsupported"
        ]
        mismatched = [
            rule
            for rule in rules
            if rule["transforms"][name]["status"] == "transform_mismatch"
        ]
        violations = [
            dict(item, seed=rule["seed"], board_size=rule["board_size"])
            for rule in rules
            for item in (rule["transforms"][name]["comparison"] or {}).get(
                "violations", []
            )
        ]
        summary[name] = {
            "rules_supported": len(supported),
            "rules_unsupported": len(unsupported),
            "rules_transform_mismatch": len(mismatched),
            "rules_with_violation": len(
                {
                    (item["seed"], item["board_size"]) for item in violations
                }
            ),
            "violation_count": len(violations),
            "violations": violations[:40],
            "types_compared": sum(
                (rule["transforms"][name]["comparison"] or {}).get("types", 0)
                for rule in rules
            ),
            "raw_exact_matches": sum(
                (rule["transforms"][name]["comparison"] or {}).get(
                    "raw_exact_matches", 0
                )
                for rule in rules
            ),
            "raw_max_abs_delta": max(
                (
                    (rule["transforms"][name]["comparison"] or {}).get(
                        "raw_max_abs_delta", 0.0
                    )
                    for rule in rules
                ),
                default=0.0,
            ),
            "rules_with_drop_term_change": sum(
                bool(
                    (rule["transforms"][name]["comparison"] or {}).get(
                        "drop_term_changed_types"
                    )
                )
                for rule in rules
            ),
            "median_mismatch_rules": sum(
                not (rule["transforms"][name]["comparison"] or {}).get(
                    "median_non_anchor_value", {"match": True}
                )["match"]
                for rule in rules
            ),
        }

    secondary = {}
    name = "A2_rotation_rederived"
    secondary[name] = {
        "rules_supported": sum(
            rule["transforms"][name]["status"] == "supported" for rule in rules
        ),
        "rules_unsupported": sum(
            rule["transforms"][name]["status"] == "unsupported" for rule in rules
        ),
        "violation_count": sum(
            len((rule["transforms"][name]["comparison"] or {}).get("violations", []))
            for rule in rules
        ),
        "rules_with_drop_term_change": sum(
            bool(
                (rule["transforms"][name]["comparison"] or {}).get(
                    "drop_term_changed_types"
                )
            )
            for rule in rules
        ),
        "types_compared": sum(
            (rule["transforms"][name]["comparison"] or {}).get("types", 0)
            for rule in rules
        ),
        "raw_max_abs_delta": max(
            (
                (rule["transforms"][name]["comparison"] or {}).get(
                    "raw_max_abs_delta", 0.0
                )
                for rule in rules
            ),
            default=0.0,
        ),
    }

    primary_ok = all(
        summary[name]["rules_unsupported"] == 0
        and summary[name]["rules_transform_mismatch"] == 0
        and summary[name]["violation_count"] == 0
        for name in ("A1_atom_rotation", "B_type_relabel")
    )
    any_violation = any(
        summary[name]["violation_count"] > 0
        for name in ("A1_atom_rotation", "B_type_relabel")
    )
    if primary_ok:
        decision = "profile_transform_invariant"
    elif any_violation:
        decision = "transform_sensitive_with_mechanism"
    else:
        decision = "inconclusive"
    return {"primary": summary, "secondary": secondary, "decision": decision}


def main() -> int:
    started = time.time()
    rules = []
    for size in SIZES:
        for seed in SEEDS:
            rules.append(scan_rule(seed, size))
    verdict = decide(rules)

    controls_ok = all(
        rule["round_trip_control"]["fingerprint_match"]
        and rule["round_trip_control"]["profile_identical"]
        and rule["round_trip_control"]["median_identical"]
        for rule in rules
    )

    payload = {
        "role": "DEEPSEEK_AUX",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "plan_sha256": sha256_file(HERE / "plan.json"),
        "source_sha256": {path: sha256_file(ROOT / path) for path in SOURCE_FILES},
        "git_head": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
        "design": {
            "seeds": list(SEEDS),
            "board_sizes": list(SIZES),
            "setup_preset": "classic_like",
            "hand_weight": HAND_WEIGHT,
            "search": False,
            "transforms": {
                "A1_atom_rotation": "rotate every LeapAtom.offset / RayAtom.direction by coordinates.rotate_offset; all other fields unchanged",
                "A2_rotation_rederived": "A1 plus re-derived drop masks and promotion zones from the rotated atoms (secondary, not part of the decision)",
                "B_type_relabel": "fixed order-reversing permutation of type ids with every id-keyed field remapped",
            },
            "endpoint": "per-type normalized_board_value / normalized_hand_value / promotion_option_value and per-rule median_non_anchor_value; violation = any mismatch under the bijection preserving the movement-signature multiset",
            "decision_rule": "0 violations and 0 unsupported/mismatched rules in both primary transforms -> profile_transform_invariant; any violation -> transform_sensitive_with_mechanism; otherwise inconclusive",
            "serialize_parse_round_trip_control": "compile(ruleset_from_dict(ruleset_to_dict(ruleset))) must keep fingerprint and profile identical",
        },
        "round_trip_controls_all_pass": controls_ok,
        "verdict": verdict,
        "rules": rules,
        "nonclaims": [
            "no strength, utility or game-outcome claim",
            "invariance of a static profile under a transform is not evidence that the values are good",
            "rotation invariance is only defined on square boards and is tested on one generator family",
            "the primary A1 transform leaves generator-derived drop/promotion masks fixed, so a drop-term change is expected there and reported separately",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    elapsed = time.time() - started
    print(
        json.dumps(
            {
                "out": str(OUT),
                "elapsed_seconds": round(elapsed, 2),
                "decision": verdict["decision"],
                "round_trip_controls_all_pass": controls_ok,
                "primary": verdict["primary"],
                "secondary": verdict["secondary"],
                "sha256": sha256_file(OUT),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
