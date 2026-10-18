"""Independent check of results_zone_promotion_source_classification.json.

DEEPSEEK_AUX verifier.  It replays the same stored games with its own copy of the
start-position walker and its own bucket derivation, and never imports the scan
script under test.  Failures are reported, not repaired.
"""

from __future__ import annotations

import ast
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _worktree_root(start: Path) -> Path:
    """Locate the checkout root by marker.  The private study directory sits at
    ``<repo>/.local_agent/<study>`` while the published copy sits at
    ``<repo>/docs/research/data/<study>``, so a fixed parent depth is wrong for
    one of them and the earlier ``HERE.parents[3]`` failed from the private
    directory."""
    for candidate in (start, *start.parents):
        if (candidate / "generic_chess").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise SystemExit(f"cannot locate the worktree root above {start}")


ROOT = _worktree_root(HERE)
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.core.actions import BoardMove, DropMove  # noqa: E402
from generic_chess.core.coordinates import Square, index_to_square, square_to_index  # noqa: E402
from generic_chess.core.movegen import _expanded_pseudo_actions, legal_actions  # noqa: E402
from generic_chess.core.transition import apply_action, initial_state, legal_successors  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

RESULT = HERE / "results_zone_promotion_source_classification.json"
PUBLIC = ROOT / "docs" / "research" / "data" / "profile_transform_invariance_20261018"
# The Stage 8 and disjointness inputs live in the published evidence copy; the
# private study directory does not carry a duplicate of them.
STAGE8 = HERE / "results_bind_reachability_to_decisions.json"
if not STAGE8.exists():
    STAGE8 = PUBLIC / "results_bind_reachability_to_decisions.json"
DISJOINT = HERE / "results_zone_promotion_disjointness.json"
if not DISJOINT.exists():
    DISJOINT = PUBLIC / "results_zone_promotion_disjointness.json"
GAMES_DIR = ROOT / ".local_agent" / "hand-utility-games-20261018"
FILES = [
    "results_hand_term_match_served-blind_d2_n20000_s59-70.json",
    "results_hand_term_match_served-blind_d2_n20000_s71-94.json",
    "results_hand_term_match_served-blind_d3_n20000_s59-70.json",
    "results_hand_term_match_served-blind_d3_n20000_s71-94.json",
    "results_hand_term_match_served-served_d2_n20000_s59-70.json",
    "results_hand_term_match_served-served_d2_n20000_s71-94.json",
]
START_PLY = 8
MIN_START_ACTIONS = 6
NAMESPACE = {"Square": Square, "BoardMove": BoardMove, "DropMove": DropMove}
BUCKETS = (
    "in_zone_contact",
    "zone_geometry_no_source",
    "no_reachable_allowed_destination",
    "dead_promotion_target",
    "pseudo_promotion_filtered_by_legal_safety",
    "would_promote_but_not_to_move",
)


def parse_move(text: str):
    expression = ast.parse(text, mode="eval")
    return eval(compile(expression, "<stored-move>", "eval"), {"__builtins__": {}}, NAMESPACE)


def walk_start(compiled, seed: int):
    """Copy of the stored-game start walker; kept local so this file never
    imports the code it verifies."""
    for offset in range(4):
        rng = random.Random(seed * 1009 + offset)
        state = initial_state(compiled)
        while state.ply_count < 60:
            if state.terminal_status.is_terminal:
                break
            if state.ply_count >= START_PLY:
                children = legal_successors(state, compiled)
                if len(legal_actions(state, compiled)) >= MIN_START_ACTIONS:
                    if not any(child.terminal_status.is_terminal for _, child in children):
                        return state
            children = legal_successors(state, compiled)
            if not children:
                break
            _, state = rng.choice(children)
    return None


def zones_of(evaluator, piece):
    base = piece.base_type_id
    if piece.promoted or base not in evaluator._profile.promotion_gain_by_type:
        return None
    if evaluator._profile.promotion_gain_by_type[base] <= 0:
        return None
    return evaluator._zones.get((base, piece.owner))


def reachable_squares(state, compiled, idx, piece) -> list[int]:
    """Geometric destinations of one piece, independent of whose turn it is."""
    from generic_chess.core.movement import LeapAtom

    n = compiled.board_size
    side = piece.owner
    tid = piece.current_type_id
    atoms = compiled.types_by_id[tid].movement_atoms
    leap_row = compiled.leap_targets[tid][side][idx]
    ray_row = compiled.ray_paths[tid][side][idx]
    out: list[int] = []
    for a_idx, atom in enumerate(atoms):
        row = leap_row[a_idx] if isinstance(atom, LeapAtom) else ray_row[a_idx]
        for target in row:
            occupant = state.position.board[square_to_index(target, n)]
            if occupant is None:
                out.append(square_to_index(target, n))
            elif occupant.owner != side and not compiled.types_by_id[
                occupant.current_type_id
            ].is_anchor:
                out.append(square_to_index(target, n))
            if not isinstance(atom, LeapAtom) and occupant is not None:
                break
    return out


def bucket_of(
    state,
    compiled,
    idx,
    piece,
    contact_from,
    mover,
    plain_mover,
    legal_set,
    cache,
    problems,
    sub,
):
    if idx in contact_from:
        return "in_zone_contact"
    base, side = piece.base_type_id, piece.owner
    key = (compiled.ruleset_fingerprint, base, side)
    if key not in cache:
        pairs = compiled.promotion_allowed[base][side]
        cache[key] = (
            {square_to_index(start, compiled.board_size) for start, _ in pairs},
            {square_to_index(dest, compiled.board_size) for _, dest in pairs},
        )
    sources, dests = cache[key]
    if idx not in sources:
        return "zone_geometry_no_source"
    reach = reachable_squares(state, compiled, idx, piece)
    pairs = [t for t in reach if t in dests]
    if not pairs:
        return "no_reachable_allowed_destination"
    alive = any(
        compiled.empty_mobility[tid][side][t]
        for t in pairs
        for tid in compiled.types_by_id[base].promotion_target_ids
    )
    if not alive:
        return "dead_promotion_target"
    library = {square_to_index(t, compiled.board_size) for t in mover.get(idx, ())}
    # _expanded_pseudo_actions only ever yields actions of the side to move, so
    # an idle-side piece can never have a library variant here; that absence is
    # turn order, not a movegen defect.
    if side == state.position.side_to_move and not library & set(pairs):
        problems.append(f"square {idx}: reachable alive promotion but no library variant")
    if side != state.position.side_to_move:
        return "would_promote_but_not_to_move"
    # Pseudo-legal and alive, yet no legal promotion from this square: the
    # promotion was refused by the legality filter, not by structure.  Record
    # whether an unpromoted sibling from the same square survived that filter;
    # if one did, the refusal is promotion-specific rather than a refutation of
    # the whole parent move.
    has_legal_sibling = any(
        BoardMove(index_to_square(idx, compiled.board_size), target) in legal_set
        for target in plain_mover.get(idx, ())
    )
    sub["legal_unpromoted_sibling" if has_legal_sibling else "no_legal_unpromoted_sibling"] += 1
    return "pseudo_promotion_filtered_by_legal_safety"


def recompute():
    totals: Counter = Counter()
    sub: Counter = Counter()
    per_seed: dict[int, Counter] = {}
    contact_from_all: Counter = Counter()
    seen: set[tuple] = set()
    cache: dict = {}
    problems: list[str] = []
    for name in FILES:
        payload = json.loads((GAMES_DIR / name).read_text(encoding="utf-8"))
        depth = payload["design"]["search"]["max_depth"]
        for game in payload["games"]:
            key = (game["seed"], depth, game["game_index"], tuple(game["moves"]))
            if key in seen:
                continue
            seen.add(key)
            seed = game["seed"]
            compiled = generate_game(
                GeneratorConfig(seed=seed, board_size=4, setup_preset="classic_like")
            ).compiled_ruleset
            config = EvaluationConfig()
            evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
            state = walk_start(compiled, seed)
            if state is None:
                continue
            start_ply = state.ply_count
            counts = per_seed.setdefault(seed, Counter())

            def scan(state) -> None:
                actions = legal_actions(state, compiled)
                legal_set = set(actions)
                contact_from = {
                    square_to_index(a.from_square, compiled.board_size)
                    for a in actions
                    if isinstance(a, BoardMove) and a.promotion_target_id is not None
                }
                mover: dict[int, list[Square]] = {}
                plain_mover: dict[int, list[Square]] = {}
                for a in _expanded_pseudo_actions(state.position, compiled):
                    if not isinstance(a, BoardMove):
                        continue
                    key_idx = square_to_index(a.from_square, compiled.board_size)
                    if a.promotion_target_id is not None:
                        mover.setdefault(key_idx, []).append(a.to_square)
                    else:
                        plain_mover.setdefault(key_idx, []).append(a.to_square)
                for idx, piece in enumerate(state.position.board):
                    if piece is None:
                        continue
                    zone = zones_of(evaluator, piece)
                    if zone is None or idx not in zone:
                        continue
                    bucket = bucket_of(
                        state,
                        compiled,
                        idx,
                        piece,
                        contact_from,
                        mover,
                        plain_mover,
                        legal_set,
                        cache,
                        problems,
                        sub,
                    )
                    totals["in_zone_paid_observations"] += 1
                    totals[bucket] += 1
                    counts[bucket] += 1
                    _ = legal_set
                    contact_from_all.update(contact_from)

            scan(state)
            ok = True
            for text in game["moves"]:
                try:
                    state = apply_action(state, parse_move(text), compiled)
                except Exception:  # noqa: BLE001
                    ok = False
                    break
                scan(state)
            status = state.terminal_status
            replayed = {
                "status": status.status.value if status.is_terminal else "watchdog",
                "winner": status.winner if status.is_terminal else None,
                "plies": state.ply_count - start_ply,
            }
            if not ok or replayed != {
                "status": game["status"],
                "winner": game["winner"],
                "plies": game["plies"],
            }:
                totals["replay_mismatch"] += 1
    return totals, per_seed, problems, sub


def main() -> int:
    results = json.loads(RESULT.read_text(encoding="utf-8"))
    summary = results["summary"]
    stage8 = json.loads(STAGE8.read_text(encoding="utf-8"))["summary"]
    disjoint = json.loads(DISJOINT.read_text(encoding="utf-8"))
    checks: list[dict] = []

    def check(name: str, passed: bool, detail) -> None:
        checks.append(dict(check=name, passed=bool(passed), detail=detail))

    # Every named bucket is part of the partition, including the idle-side
    # would_promote_but_not_to_move mass, which is descriptive but still counted.
    total = sum(summary[b] for b in BUCKETS)
    check(
        "all_buckets_sum_to_observation_total",
        total == summary["in_zone_paid_observations"],
        dict(buckets=list(BUCKETS), sum=total, total=summary["in_zone_paid_observations"]),
    )
    moving = (
        summary["to_move_zone_geometry_no_source"]
        + summary["to_move_no_reachable_allowed_destination"]
        + summary["to_move_dead_promotion_target"]
        + summary["to_move_pseudo_promotion_filtered_by_legal_safety"]
    )
    check(
        "side_split_reconciles",
        summary["to_move_observations"] + summary["idle_observations"]
        == summary["in_zone_paid_observations"]
        and summary["to_move_observations"] - summary["in_zone_contact"] == moving
        and moving == summary["to_move_mass_used_by_the_decision_rule"],
        dict(
            to_move=summary["to_move_observations"],
            idle=summary["idle_observations"],
            contact=summary["in_zone_contact"],
            moving=moving,
            recorded=summary["to_move_mass_used_by_the_decision_rule"],
        ),
    )
    check(
        "contact_equals_stage8",
        summary["in_zone_contact"] == stage8["in_zone_with_legal_promotion"],
        dict(here=summary["in_zone_contact"], stage8=stage8["in_zone_with_legal_promotion"]),
    )
    check(
        "observations_equal_stage8",
        summary["in_zone_paid_observations"] == stage8["promotable_in_zone_observations"],
        dict(
            here=summary["in_zone_paid_observations"],
            stage8=stage8["promotable_in_zone_observations"],
        ),
    )
    check("no_problems_recorded", summary["problems"] == [], summary["problems"])
    per_seed_sums = Counter()
    for row in results["per_seed"]:
        for bucket in BUCKETS:
            per_seed_sums[bucket] += row.get(bucket, 0)
    check(
        "per_seed_rows_match_summary",
        all(per_seed_sums[b] == summary[b] for b in BUCKETS),
        {b: [per_seed_sums[b], summary[b]] for b in BUCKETS if per_seed_sums[b] != summary[b]},
    )
    opportunity = disjoint["opportunity_seeds_whose_zone_is_disjoint"]
    bad = {
        row["seed"]: {b: row.get(b, 0) for b in BUCKETS if b != "zone_geometry_no_source" and row.get(b, 0)}
        for row in results["per_seed"]
        if row["seed"] in opportunity
    }
    check(
        "disjoint_seeds_are_geometry_only",
        all(not v for v in bad.values()),
        dict(seeds=opportunity, offending={k: v for k, v in bad.items() if v}),
    )
    if moving == 0:
        fired = "no_missing_contact_mass_to_classify"
    elif summary["to_move_zone_geometry_no_source"] >= 0.5 * moving:
        fired = "missing_contact_is_mostly_zone_geometry"
    elif (
        summary["to_move_no_reachable_allowed_destination"]
        + summary["to_move_dead_promotion_target"]
        >= 0.5 * moving
    ):
        fired = "missing_contact_is_mostly_destination_side"
    else:
        fired = "missing_contact_is_split_without_a_majority"
    check("decision_rule_reproduces", fired == summary["decision"], dict(fired=fired))
    # The withdrawn contrast is a specific pair of arms with a ratio, not the
    # word "outside": the result legitimately states in its nonclaims that no
    # such contrast is computed, and a bare word scan would reject that
    # negation.  Look for the rate fields themselves instead.
    text = RESULT.read_text(encoding="utf-8")
    forbidden = (
        "not_in_zone_observations",
        "not_in_zone_with_legal_promotion",
        "not_in_zone_legal_promotion_rate",
        "promotable_not_in_zone_observations",
        "rate_ratio",
        "outside_zone_rate",
    )
    check(
        "withdrawn_rate_contrast_absent",
        not any(word in text for word in forbidden),
        [word for word in forbidden if word in text],
    )
    check(
        "defect_corrections_recorded",
        len(results.get("defect_corrections", [])) == 1,
        results.get("defect_corrections"),
    )

    totals, per_seed, problems, sub = recompute()
    independent = {
        bucket: totals[bucket] for bucket in BUCKETS
    }
    independent["replay_mismatch"] = totals["replay_mismatch"]
    reported = {bucket: summary[bucket] for bucket in BUCKETS}
    check(
        "independent_replay_matches_all_buckets",
        all(independent[b] == reported[b] for b in BUCKETS)
        and independent["replay_mismatch"] == 0,
        {b: [independent[b], reported[b]] for b in BUCKETS if independent[b] != reported[b]}
        | {"replay_mismatch": independent["replay_mismatch"]},
    )
    check("independent_expansion_uniform", problems == [], problems[:5])
    check(
        "filtered_cases_have_no_legal_unpromoted_sibling",
        sub["legal_unpromoted_sibling"]
        == summary["of_which_promotion_specific_legal_filter"]
        and sub["no_legal_unpromoted_sibling"]
        == summary["of_which_parent_move_refuted_by_anchor_safety"]
        and totals["pseudo_promotion_filtered_by_legal_safety"]
        == summary["to_move_pseudo_promotion_filtered_by_legal_safety"],
        dict(
            legal_sibling=sub["legal_unpromoted_sibling"],
            no_legal_sibling=sub["no_legal_unpromoted_sibling"],
            recorded_promotion_specific=summary["of_which_promotion_specific_legal_filter"],
            recorded_parent_move=summary["of_which_parent_move_refuted_by_anchor_safety"],
            filtered_total=totals["pseudo_promotion_filtered_by_legal_safety"],
        ),
    )
    check(
        "independent_per_seed_contact_matches",
        all(
            row.get("in_zone_contact", 0)
            == per_seed.get(row["seed"], Counter())["in_zone_contact"]
            for row in results["per_seed"]
        ),
        None,
    )

    verdict = "all_checks_passed" if all(c["passed"] for c in checks) else "checks_failed"
    payload = dict(role="DEEPSEEK_AUX", verifier="verify_zone_promotion_source_classification.py", verdict=verdict, checks=checks)
    (HERE / "verification_zone_promotion_source_classification.json").write_text(
        json.dumps(payload, indent=1) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=1))
    return 0 if verdict == "all_checks_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
