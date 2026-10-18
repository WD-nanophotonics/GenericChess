"""Post-hoc A3 follow-up: full 180-degree rotation of the whole rule geometry.

The pre-registered plan ``plan.json`` (sha 9892ac75) applied transform A1, which
rotates only the movement atoms and leaves the generator's initial position and
per-owner masks untouched.  Seven of eighty transformed rulesets were refused by
the compiler with ``INITIAL_NO_LEGAL_MOVE``, so the pre-written decision could
not be reached and the prior verdict stands as ``inconclusive``.

This follow-up was written after that result and is labelled post-hoc in
``plan_a3.json``.  A3 rotates the *whole* geometry by one board automorphism
``sigma(f, r) = (n-1-f, n-1-r)``: movement atoms, initial position, drop masks
and promotion masks.  It then asks three questions per rule:

  1. does the rotated RuleSet compile at all;
  2. is the one-ply legal-action set at the initial position a bijection under
     ``sigma`` (a bounded legality check, not game-tree equivalence);
  3. is the served static profile still exactly equal under the identity type-id
     map.

It also records one mechanism fact: the served leaf evaluator derives its
promotion zone from ``empty_forward_mobility``, which is defined against an
absolute rank direction and is therefore a candidate asymmetry that the static
profile does not share.  No search, no evaluation of positions, no learning.
"""

from __future__ import annotations

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
sys.path.insert(0, str(HERE))

import scan_profile_transform as base  # noqa: E402

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.core.actions import (  # noqa: E402
    BoardMove,
    DropMove,
    PassAction,
)
from generic_chess.core.coordinates import Square  # noqa: E402
from generic_chess.core.movegen import legal_actions  # noqa: E402
from generic_chess.core.transition import initial_state  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402
from generic_chess.rules.compiler import compile_ruleset  # noqa: E402

OUT = HERE / "results_profile_transform_a3.json"
SEEDS = base.SEEDS
SIZES = base.SIZES
HAND_WEIGHT = base.HAND_WEIGHT

SOURCE_FILES = base.SOURCE_FILES + (
    "generic_chess/core/actions.py",
    "generic_chess/core/movegen.py",
    "generic_chess/core/transition.py",
    "generic_chess/rules/compiled.py",
    "generic_chess/rules/schema.py",
)


def sigma(square, n: int):
    return Square(n - 1 - square.file, n - 1 - square.rank)


def rotate_position(rows, n: int | None = None):
    """180-degree rotation: reverse the row order and every row."""
    return tuple(tuple(reversed(row)) for row in reversed(tuple(rows)))


def transform_a3(ruleset):
    n = ruleset.board_size
    drop = {
        key: tuple(tuple(reversed(mask)) for mask in per_owner)
        for key, per_owner in ruleset.drop_allowed.items()
    }
    promotion_allowed = {
        key: tuple(
            frozenset((sigma(src, n), sigma(dst, n)) for src, dst in pairs)
            for pairs in per_owner
        )
        for key, per_owner in ruleset.promotion_allowed.items()
    }
    promotion_forced = {
        key: tuple(
            frozenset(sigma(square, n) for square in squares)
            for squares in per_owner
        )
        for key, per_owner in ruleset.promotion_forced.items()
    }
    transformed = replace(
        ruleset,
        piece_types=base.rotated_atom_types(ruleset),
        initial_position=rotate_position(ruleset.initial_position),
        drop_allowed=drop,
        promotion_allowed=promotion_allowed,
        promotion_forced=promotion_forced,
        initial_setup_options=tuple(
            replace(option, position=rotate_position(option.position))
            for option in ruleset.initial_setup_options
        ),
    )
    return transformed, {"piece_types": lambda type_id: type_id}


def rotate_action(action, n: int):
    """Map one legacy action through sigma; None when unsupported."""
    if isinstance(action, BoardMove):
        return BoardMove(
            sigma(action.from_square, n),
            sigma(action.to_square, n),
            action.promotion_target_id,
        )
    if isinstance(action, DropMove):
        return DropMove(action.base_type_id, sigma(action.to_square, n))
    if isinstance(action, PassAction):
        return PassAction()
    return None


def one_ply_bijection(original_compiled, rotated_compiled, n: int) -> dict:
    original_actions = legal_actions(
        initial_state(original_compiled), original_compiled
    )
    rotated_actions = legal_actions(initial_state(rotated_compiled), rotated_compiled)
    rotated_set = set(rotated_actions)
    mapped = []
    unsupported_kinds = set()
    for action in original_actions:
        moved = rotate_action(action, n)
        if moved is None:
            unsupported_kinds.add(type(action).__name__)
            continue
        mapped.append(moved)
    missing = [item for item in mapped if item not in rotated_set]
    return {
        "original_actions": len(original_actions),
        "rotated_actions": len(rotated_actions),
        "count_match": len(original_actions) == len(rotated_actions),
        "mapped_actions": len(mapped),
        "mapped_missing_in_rotated": len(missing),
        "unsupported_action_kinds": sorted(unsupported_kinds),
        "injective": len(set(mapped)) == len(mapped),
        "bijection": (
            not unsupported_kinds
            and len(original_actions) == len(rotated_actions)
            and len(mapped) == len(original_actions)
            and not missing
        ),
        "sample_missing": [repr(item) for item in missing[:4]],
    }


def forward_zone_check(compiled) -> dict:
    """Is the evaluator's promotion zone invariant under sigma?"""
    n = compiled.board_size
    area = n * n
    rows = []
    for piece_type in compiled.piece_types:
        if not piece_type.is_promotable:
            continue
        for owner in (0, 1):
            mobility = compiled.empty_forward_mobility[piece_type.type_id][owner]
            zone = frozenset(idx for idx in range(area) if not mobility[idx])
            mirrored = frozenset(area - 1 - idx for idx in zone)
            rows.append(
                {
                    "type_id": piece_type.type_id,
                    "owner": owner,
                    "zone_size": len(zone),
                    "rotation_invariant": zone == mirrored,
                    "symmetric_difference": len(zone ^ mirrored),
                }
            )
    return {
        "entries": rows,
        "all_invariant": bool(rows) and all(row["rotation_invariant"] for row in rows),
        "non_invariant_entries": sum(not row["rotation_invariant"] for row in rows),
        "entries_checked": len(rows),
    }


def scan_rule(seed: int, size: int) -> dict:
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
    )
    ruleset = game.ruleset
    compiled = game.compiled_ruleset
    config = EvaluationConfig(hand_weight=HAND_WEIGHT)
    original = build_ruleset_profile(compiled, config)

    record = {
        "seed": seed,
        "board_size": size,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "status": "supported",
        "error": None,
        "fingerprint_changed": None,
        "comparison": None,
        "one_ply": None,
        "profile_median_non_anchor": int(original.median_non_anchor_value),
    }
    try:
        rotated_ruleset, keys = transform_a3(ruleset)
        rotated_compiled = compile_ruleset(rotated_ruleset)
        record["fingerprint_changed"] = (
            rotated_compiled.ruleset_fingerprint != compiled.ruleset_fingerprint
        )
        rotated_profile = build_ruleset_profile(rotated_compiled, config)
        record["comparison"] = base.compare_profiles(
            original,
            rotated_profile,
            match_key=keys["piece_types"],
            signature_check="negated",
        )
        record["one_ply"] = one_ply_bijection(compiled, rotated_compiled, size)
    except Exception as exc:  # feasibility gate: record, never fabricate
        record["status"] = "unsupported"
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["traceback_tail"] = traceback.format_exc().splitlines()[-6:]
    record["forward_zone"] = forward_zone_check(compiled)
    return record


def decide(rules: list[dict]) -> dict:
    supported = [rule for rule in rules if rule["status"] == "supported"]
    unsupported = [rule for rule in rules if rule["status"] == "unsupported"]
    violations = [
        dict(item, seed=rule["seed"], board_size=rule["board_size"])
        for rule in supported
        for item in rule["comparison"]["violations"]
    ]
    signature_failures = [
        dict(item, seed=rule["seed"], board_size=rule["board_size"])
        for rule in supported
        for item in rule["comparison"]["signature_failures"]
    ]
    bijection_failures = [
        {"seed": rule["seed"], "board_size": rule["board_size"],
         "one_ply": rule["one_ply"]}
        for rule in supported
        if not rule["one_ply"]["bijection"]
    ]
    if unsupported:
        decision = "unsupported"
    elif bijection_failures:
        decision = "transform_not_a_rule_isomorphism"
    elif violations or signature_failures:
        decision = "profile_not_a_function_of_rule_structure"
    else:
        decision = "rotation_is_a_rule_isomorphism_and_profile_invariant"
    zones = [
        dict(entry, seed=rule["seed"], board_size=rule["board_size"])
        for rule in rules
        for entry in rule["forward_zone"]["entries"]
    ]
    return {
        "decision": decision,
        "rules_total": len(rules),
        "rules_supported": len(supported),
        "rules_unsupported": len(unsupported),
        "unsupported_errors": [
            {"seed": rule["seed"], "board_size": rule["board_size"],
             "error": rule["error"]}
            for rule in unsupported
        ],
        "fingerprints_changed": sum(bool(rule["fingerprint_changed"]) for rule in supported),
        "types_compared": sum(
            (rule["comparison"] or {}).get("types", 0) for rule in supported
        ),
        "raw_exact_matches": sum(
            (rule["comparison"] or {}).get("raw_exact_matches", 0) for rule in supported
        ),
        "raw_max_abs_delta": max(
            ((rule["comparison"] or {}).get("raw_max_abs_delta", 0.0)
             for rule in supported),
            default=0.0,
        ),
        "violation_count": len(violations),
        "violations": violations[:40],
        "signature_failure_count": len(signature_failures),
        "signature_failures": signature_failures[:10],
        "bijection_failures": bijection_failures[:10],
        "bijection_rules_passed": len(supported) - len(bijection_failures),
        "actions_checked": sum(rule["one_ply"]["original_actions"] for rule in supported),
        "median_mismatch_rules": sum(
            not ((rule["comparison"] or {}).get("median_non_anchor_value") or {"match": True})["match"]
            for rule in supported
        ),
        "mechanism_forward_zone": {
            "entries_checked": len(zones),
            "non_invariant_entries": sum(
                1 for entry in zones if not entry["rotation_invariant"]
            ),
            "rules_with_any_non_invariant_zone": len(
                {
                    (entry["seed"], entry["board_size"])
                    for entry in zones
                    if not entry["rotation_invariant"]
                }
            ),
            "non_invariant_types": sorted(
                {entry["type_id"] for entry in zones if not entry["rotation_invariant"]}
            ),
            "sample": [
                entry for entry in zones if not entry["rotation_invariant"]
            ][:8],
        },
    }


def main() -> int:
    started = time.time()
    rules = [scan_rule(seed, size) for size in SIZES for seed in SEEDS]
    verdict = decide(rules)
    payload = {
        "role": "DEEPSEEK_AUX",
        "provenance": (
            "post-hoc A3 follow-up to the pre-registered plan.json (sha prefix "
            "9892ac75); written after A1's feasibility gate fired on 7/80 rules"
        ),
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "plan_sha256": base.sha256_file(HERE / "plan_a3.json"),
        "prior_plan_sha256": base.sha256_file(HERE / "plan.json"),
        "prior_results_sha256": base.sha256_file(HERE / "results_profile_transform.json"),
        "source_sha256": {path: base.sha256_file(ROOT / path) for path in SOURCE_FILES},
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
            "transform_A3": "sigma(f,r)=(n-1-f,n-1-r) applied to movement atoms, initial position, drop masks and promotion masks; type ids and flags unchanged",
            "endpoint": "compile status; one-ply legal-action bijection at the initial position; exact equality of normalized board/hand/promotion values and median_non_anchor_value",
            "decision_rule": "all 80 compile and 80/80 one-ply bijections and 0 value mismatches -> rotation_is_a_rule_isomorphism_and_profile_invariant; any compile failure -> unsupported; any bijection failure -> transform_not_a_rule_isomorphism; bijection holds but a value differs -> profile_not_a_function_of_rule_structure",
            "mechanism_check": "is the evaluator promotion zone (squares without empty forward mobility) invariant under sigma",
        },
        "verdict": verdict,
        "rules": rules,
        "nonclaims": [
            "no strength, utility or game-outcome claim",
            "the one-ply bijection is a bounded legality check, not game-tree equivalence",
            "one generator family, square boards 6 and 8, 40 seeds",
            "profile invariance does not imply that the served evaluator is invariant, and the mechanism check only records the forward-zone structure",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "elapsed_seconds": round(time.time() - started, 2),
                "decision": verdict["decision"],
                "rules_supported": verdict["rules_supported"],
                "rules_unsupported": verdict["rules_unsupported"],
                "violation_count": verdict["violation_count"],
                "bijection_rules_passed": verdict["bijection_rules_passed"],
                "actions_checked": verdict["actions_checked"],
                "raw_max_abs_delta": verdict["raw_max_abs_delta"],
                "forward_zone": verdict["mechanism_forward_zone"],
                "sha256": base.sha256_file(OUT),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
