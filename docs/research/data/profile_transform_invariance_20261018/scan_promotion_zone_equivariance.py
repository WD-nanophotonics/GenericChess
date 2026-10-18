"""Does the served promotion-potential term survive the A3 full rotation when it
actually fires?

Pre-registered in ``plan_a4.json`` (written after A3, after the initial-position
evaluator null, and after a two-rule zone probe recorded in that plan).

The earlier evaluator scan compared only each rule's initial position, where no
promotable piece is inside or forward-adjacent to its own zone, so the
promotion term contributed 0 on both sides and the null could not test it.  This
scan builds three explicit placements per owner - inside the zone, one step
forward of it, and far from it - and compares the original rule against its A3
rotation under four configurations, so the promotion term is isolated.

No search, no learning, no new seeds, no position sampling: one relocation per
case from the rule's own initial board.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import scan_profile_transform as base  # noqa: E402
import scan_profile_transform_a3 as a3  # noqa: E402

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.core.transition import initial_state  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402
from generic_chess.rules.compiler import compile_ruleset  # noqa: E402

OUT = HERE / "results_promotion_zone_equivariance.json"
SEEDS = base.SEEDS
SIZES = base.SIZES
PROFILE_HAND_WEIGHT = base.HAND_WEIGHT

CONFIGURATIONS = {
    "material_only": EvaluationConfig(
        hand_weight=PROFILE_HAND_WEIGHT,
        dynamic_mobility_weight=0,
        anchor_escape_weight=0,
        promotion_potential_weight=0,
    ),
    "promotion_only": EvaluationConfig(
        hand_weight=PROFILE_HAND_WEIGHT,
        dynamic_mobility_weight=0,
        anchor_escape_weight=0,
        promotion_potential_weight=3,
    ),
    "no_promotion": EvaluationConfig(
        hand_weight=PROFILE_HAND_WEIGHT,
        dynamic_mobility_weight=2,
        anchor_escape_weight=5,
        promotion_potential_weight=0,
    ),
    "default": EvaluationConfig(hand_weight=PROFILE_HAND_WEIGHT),
}

KINDS = ("in_zone", "near_zone", "far")

SOURCE_FILES = base.SOURCE_FILES + (
    "generic_chess/ai/evaluation/evaluator.py",
    "generic_chess/core/position.py",
    "generic_chess/core/transition.py",
)


def sigma_idx(idx: int, n: int) -> int:
    file_, rank_ = idx % n, idx // n
    return (n - 1 - rank_) * n + (n - 1 - file_)


def zone_and_forward(compiled, base_type: str, owner: int):
    n = compiled.board_size
    forward = compiled.empty_forward_mobility[base_type][owner]
    zone = {
        idx for idx in range(n * n)
        if not forward[idx]
    }
    return zone, forward


def forward_indices(forward_row, n: int) -> list[int]:
    return [square.rank * n + square.file for square in forward_row]


def piece_multiset(position) -> list:
    items = [
        (piece.owner, piece.current_type_id, piece.base_type_id, piece.promoted)
        for piece in position.board
        if piece is not None
    ]
    for owner in (0, 1):
        for type_id, count in position.hands[owner].counts:
            items.append((owner, f"hand:{type_id}", count, False))
    return sorted(items, key=str)


def relocate(state, src: int, dst: int):
    board = list(state.position.board)
    piece = board[src]
    if piece is None or board[dst] is not None:
        return None
    board[src] = None
    board[dst] = piece
    return replace(state, position=replace(state.position, board=tuple(board)))


def score(state, compiled, profile) -> dict:
    return {
        name: Evaluator(compiled, profile, config).evaluate(state)
        for name, config in CONFIGURATIONS.items()
    }


def scan_rule(seed: int, size: int) -> dict:
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
    )
    original_compiled = game.compiled_ruleset
    rotated_ruleset, _keys = a3.transform_a3(game.ruleset)
    rotated_compiled = compile_ruleset(rotated_ruleset)
    profile_config = EvaluationConfig(hand_weight=PROFILE_HAND_WEIGHT)
    original_profile = build_ruleset_profile(original_compiled, profile_config)
    rotated_profile = build_ruleset_profile(rotated_compiled, profile_config)

    n = size
    original_state = initial_state(original_compiled)
    rotated_state = initial_state(rotated_compiled)
    original_board = original_state.position.board
    rotated_board = rotated_state.position.board

    promotable_types = [
        pt.type_id for pt in original_compiled.piece_types if pt.is_promotable
    ]
    on_board = {
        piece.base_type_id
        for piece in original_board
        if piece is not None and not piece.promoted
    }
    base_candidates = sorted(
        type_id
        for type_id in promotable_types
        if type_id in on_board
        and original_profile.promotion_gain_by_type.get(type_id, 0) > 0
    )

    structural = {}
    cases = []
    unsupported = []
    if not base_candidates:
        unsupported.append({"reason": "no_promotable_type_with_positive_gain_on_board"})
    for base_type in base_candidates:
        gain = original_profile.promotion_gain_by_type[base_type]
        unit = max(1, gain // 1000)
        for owner in (0, 1):
            src_original = next(
                idx for idx, piece in enumerate(original_board)
                if piece is not None
                and piece.owner == owner
                and piece.base_type_id == base_type
                and not piece.promoted
            )
            src_rotated = sigma_idx(src_original, n)
            piece_at_rotated = rotated_board[src_rotated]
            if (
                piece_at_rotated is None
                or piece_at_rotated.owner != owner
                or piece_at_rotated.base_type_id != base_type
                or piece_at_rotated.current_type_id
                != original_board[src_original].current_type_id
            ):
                unsupported.append(
                    {
                        "reason": "composition_mismatch",
                        "base_type": base_type,
                        "owner": owner,
                        "expected_square": src_rotated,
                    }
                )
                continue

            zone, forward = zone_and_forward(original_compiled, base_type, owner)
            rotated_zone, _rotated_forward = zone_and_forward(
                rotated_compiled, base_type, owner
            )
            structural[str(owner)] = {
                "base_type": base_type,
                "gain": gain,
                "unit": unit,
                "zone_squares": len(zone),
                "rotated_zone_squares": len(rotated_zone),
                "sigma_zone_equals_rotated_zone": {
                    sigma_idx(idx, n) for idx in zone
                } == rotated_zone,
                "zone_is_invariant_under_sigma": {
                    sigma_idx(idx, n) for idx in zone
                } == zone,
            }

            for kind in KINDS:
                candidates = []
                for idx in range(n * n):
                    if original_board[idx] is not None or idx == src_original:
                        continue
                    targets = set(forward_indices(forward[idx], n))
                    if kind == "in_zone":
                        ok = idx in zone
                    elif kind == "near_zone":
                        ok = idx not in zone and bool(targets & zone)
                    else:
                        ok = idx not in zone and not (targets & zone)
                    if not ok:
                        continue
                    if rotated_board[sigma_idx(idx, n)] is not None:
                        continue
                    candidates.append(idx)
                if not candidates:
                    cases.append(
                        {
                            "base_type": base_type,
                            "owner": owner,
                            "kind": kind,
                            "status": "no_candidate",
                        }
                    )
                    continue
                square_idx = min(candidates)
                mapped = sigma_idx(square_idx, n)
                original_case_state = relocate(
                    original_state, src_original, square_idx
                )
                rotated_case_state = relocate(rotated_state, src_rotated, mapped)
                if original_case_state is None or rotated_case_state is None:
                    cases.append(
                        {
                            "base_type": base_type,
                            "owner": owner,
                            "kind": kind,
                            "status": "relocation_failed",
                        }
                    )
                    continue
                original_scores = score(
                    original_case_state, original_compiled, original_profile
                )
                rotated_scores = score(
                    rotated_case_state, rotated_compiled, rotated_profile
                )
                material_equal = piece_multiset(
                    original_case_state.position
                ) == piece_multiset(rotated_case_state.position)
                differences = {
                    name: rotated_scores[name] - original_scores[name]
                    for name in CONFIGURATIONS
                }
                unstable = (not material_equal) or differences["material_only"] != 0
                cases.append(
                    {
                        "base_type": base_type,
                        "owner": owner,
                        "kind": kind,
                        "status": "instrument_unstable" if unstable else "ok",
                        "original_square": square_idx,
                        "rotated_square": mapped,
                        "square_in_zone": square_idx in zone,
                        "square_in_rotated_zone": mapped in rotated_zone,
                        "material_multiset_equal": material_equal,
                        "original_scores": original_scores,
                        "rotated_scores": rotated_scores,
                        "differences": differences,
                    }
                )

    return {
        "seed": seed,
        "board_size": size,
        "ruleset_fingerprint": original_compiled.ruleset_fingerprint,
        "rotated_fingerprint": rotated_compiled.ruleset_fingerprint,
        "promotable_types_with_gain": base_candidates,
        "structural": structural,
        "cases": cases,
        "unsupported": unsupported,
    }


def decide(rules: list[dict]) -> dict:
    usable = [
        case
        for rule in rules
        for case in rule["cases"]
        if case.get("status") == "ok"
    ]
    unstable = [
        case
        for rule in rules
        for case in rule["cases"]
        if case.get("status") == "instrument_unstable"
    ]
    no_candidate = [
        (rule["seed"], rule["board_size"], case)
        for rule in rules
        for case in rule["cases"]
        if case.get("status") == "no_candidate"
    ]

    def nonzero(name):
        return [
            {
                "seed": rule["seed"],
                "board_size": rule["board_size"],
                "base_type": case["base_type"],
                "owner": case["owner"],
                "kind": case["kind"],
                "difference": case["differences"][name],
            }
            for rule in rules
            for case in rule["cases"]
            if case.get("status") == "ok" and case["differences"][name] != 0
        ]

    hits = {name: nonzero(name) for name in CONFIGURATIONS}
    if not usable:
        decision = "instrument_failure"
    elif hits["no_promotion"]:
        decision = "evaluator_has_additional_orientation_dependence"
    elif hits["promotion_only"] or hits["default"]:
        decision = "promotion_term_breaks_rotation_equivariance"
    else:
        decision = "evaluator_is_rotation_equivariant_on_zone_states"

    by_kind = {
        kind: {
            "cases": sum(1 for case in usable if case["kind"] == kind),
            "promotion_nonzero": sum(
                1
                for case in usable
                if case["kind"] == kind
                and case["differences"]["promotion_only"] != 0
            ),
        }
        for kind in KINDS
    }
    by_owner = {
        str(owner): {
            "cases": sum(1 for case in usable if case["owner"] == owner),
            "promotion_nonzero": sum(
                1
                for case in usable
                if case["owner"] == owner
                and case["differences"]["promotion_only"] != 0
            ),
        }
        for owner in (0, 1)
    }
    rules_with_failure = sorted(
        {
            (rule["seed"], rule["board_size"])
            for rule in rules
            for case in rule["cases"]
            if case.get("status") == "ok" and case["differences"]["promotion_only"] != 0
        }
    )
    structural = [
        {
            "seed": rule["seed"],
            "board_size": rule["board_size"],
            "owner": owner,
            **record,
        }
        for rule in rules
        for owner, record in rule["structural"].items()
    ]
    return {
        "decision": decision,
        "rules_total": len(rules),
        "cases_usable": len(usable),
        "cases_instrument_unstable": len(unstable),
        "cases_no_candidate": len(no_candidate),
        "cases_by_kind": by_kind,
        "cases_by_owner": by_owner,
        "rules_with_promotion_difference": len(rules_with_failure),
        "rules_with_promotion_difference_sample": rules_with_failure[:12],
        "nonzero_by_configuration": {
            name: {"cases": len(items), "sample": items[:8]}
            for name, items in hits.items()
        },
        "distinct_promotion_differences": sorted(
            {
                case["differences"]["promotion_only"]
                for case in usable
            }
        ),
        "structural_summary": {
            "records": len(structural),
            "sigma_zone_equals_rotated_zone": sum(
                record["sigma_zone_equals_rotated_zone"] for record in structural
            ),
            "zone_is_invariant_under_sigma": sum(
                record["zone_is_invariant_under_sigma"] for record in structural
            ),
            "original_zone_sizes": sorted(
                {record["zone_squares"] for record in structural}
            ),
            "rotated_zone_sizes": sorted(
                {record["rotated_zone_squares"] for record in structural}
            ),
        },
        "unsupported": [
            {"seed": rule["seed"], "board_size": rule["board_size"], **item}
            for rule in rules
            for item in rule["unsupported"]
        ],
    }


def main() -> int:
    started = time.time()
    rules = [scan_rule(seed, size) for size in SIZES for seed in SEEDS]
    verdict = decide(rules)
    payload = {
        "role": "DEEPSEEK_AUX",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "plan_sha256": base.sha256_file(HERE / "plan_a4.json"),
        "a3_plan_sha256": base.sha256_file(HERE / "plan_a3.json"),
        "a3_results_sha256": base.sha256_file(
            HERE / "results_profile_transform_a3.json"
        ),
        "source_sha256": {
            path: base.sha256_file(ROOT / path) for path in SOURCE_FILES
        },
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
            "profile_hand_weight": PROFILE_HAND_WEIGHT,
            "search": False,
            "placements_per_owner": list(KINDS),
            "configurations": {
                name: {
                    "dynamic_mobility_weight": config.dynamic_mobility_weight,
                    "anchor_escape_weight": config.anchor_escape_weight,
                    "promotion_potential_weight": config.promotion_potential_weight,
                }
                for name, config in CONFIGURATIONS.items()
            },
            "endpoint": "score(rotated relocated state under the rotated rule) - score(original relocated state under the original rule), same side to move, per configuration",
            "decision_rule": "see plan_a4.json; promotion_only isolates the promotion-potential term because every other dynamic weight is 0 there",
        },
        "verdict": verdict,
        "rules": rules,
        "nonclaims": [
            "no strength, utility or game-outcome claim",
            "the constructed states are relocations of one piece from the rule's own initial board and are not claimed reachable in play",
            "one generator family, square boards 6 and 8, 40 seeds, one placement square per case",
            "a nonzero difference is a statement about the evaluation function under five configurations, not a distribution over positions",
            "no repair to evaluator.py or the compiler is proposed or implied",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "elapsed_seconds": round(time.time() - started, 2),
                "decision": verdict["decision"],
                "cases_usable": verdict["cases_usable"],
                "cases_instrument_unstable": verdict["cases_instrument_unstable"],
                "cases_no_candidate": verdict["cases_no_candidate"],
                "cases_by_kind": verdict["cases_by_kind"],
                "cases_by_owner": verdict["cases_by_owner"],
                "rules_with_promotion_difference": verdict[
                    "rules_with_promotion_difference"
                ],
                "nonzero_by_configuration": {
                    name: item["cases"]
                    for name, item in verdict["nonzero_by_configuration"].items()
                },
                "distinct_promotion_differences": verdict[
                    "distinct_promotion_differences"
                ],
                "structural_summary": verdict["structural_summary"],
                "sha256": base.sha256_file(OUT),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
