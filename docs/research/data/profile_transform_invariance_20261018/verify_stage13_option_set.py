"""Independent check of results_stage13_option_set.json.

This file does not import the scan under test.  It walks the same six stored
game files with its own loop, rebuilds every position from the stored move list,
re-derives the contact set and recomputes each contact's option set directly
from ``legal_actions``.  Counts, per-seed rows, per-event option records, the
decision rule and the absence of the withdrawn rate contrast are checked.
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
from generic_chess.core.coordinates import Square, square_to_index  # noqa: E402
from generic_chess.core.movegen import legal_actions  # noqa: E402
from generic_chess.core.transition import apply_action, initial_state, legal_successors  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

GAMES_DIR = ROOT / ".local_agent" / "hand-utility-games-20261018"
FILES = [
    "results_hand_term_match_served-blind_d2_n20000_s59-70.json",
    "results_hand_term_match_served-blind_d2_n20000_s71-94.json",
    "results_hand_term_match_served-blind_d3_n20000_s59-70.json",
    "results_hand_term_match_served-blind_d3_n20000_s71-94.json",
    "results_hand_term_match_served-served_d2_n20000_s59-70.json",
    "results_hand_term_match_served-served_d2_n20000_s71-94.json",
]
_NS = {"Square": Square, "BoardMove": BoardMove, "DropMove": DropMove}

PROMO = "played_move_is_the_promotion_from_the_paid_square"
SAME = "played_move_is_another_move_from_the_paid_square"
OTHER = "played_move_is_from_a_different_square"
NONE = "no_played_move_after_this_position"


def load(text):
    return eval(compile(ast.parse(text, mode="eval"), "<m>", "eval"), {"__builtins__": {}}, _NS)


def start_for(compiled, seed):
    for offset in range(4):
        rng = random.Random(seed * 1009 + offset)
        state = initial_state(compiled)
        while state.ply_count < 60 and not state.terminal_status.is_terminal:
            if state.ply_count >= 8:
                kids = legal_successors(state, compiled)
                if len(legal_actions(state, compiled)) >= 6:
                    if not any(child.terminal_status.is_terminal for _, child in kids):
                        return state
            kids = legal_successors(state, compiled)
            if not kids:
                break
            _, state = rng.choice(kids)
    return None


def main() -> int:
    stored = json.loads((HERE / "results_stage13_option_set.json").read_text(encoding="utf-8"))
    stage12 = json.loads((HERE / "results_stage12_contact_choice.json").read_text(encoding="utf-8"))
    checks: list[dict] = []

    def check(name: str, passed: bool, detail=None) -> None:
        checks.append(dict(check=name, passed=bool(passed), detail=detail))

    seen = set()
    recomputed = Counter()
    per_seed: dict[int, Counter] = {}
    per_event: dict[tuple, dict] = {}
    replay_mismatch = 0
    illegal_played = 0
    games = 0

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
            size = compiled.board_size
            cfg = EvaluationConfig()
            evaluator = Evaluator(compiled, build_ruleset_profile(compiled, cfg), cfg)
            state = start_for(compiled, seed)
            if state is None:
                continue
            start_ply = state.ply_count
            moves = [load(text) for text in game["moves"]]
            ply = 0
            ok = True
            while True:
                legal = legal_actions(state, compiled)
                legal_set = set(legal)
                promo_squares = {
                    square_to_index(a.from_square, size)
                    for a in legal
                    if isinstance(a, BoardMove) and a.promotion_target_id is not None
                }
                played = moves[ply] if ply < len(moves) else None
                if played is not None and played not in legal_set:
                    illegal_played += 1
                moving = state.position.side_to_move
                for idx, piece in enumerate(state.position.board):
                    if piece is None or piece.owner != moving or idx not in promo_squares:
                        continue
                    base = piece.base_type_id
                    if piece.promoted or base not in evaluator._profile.promotion_gain_by_type:
                        continue
                    if evaluator._profile.promotion_gain_by_type[base] <= 0:
                        continue
                    zone = evaluator._zones.get((base, piece.owner))
                    if zone is None or idx not in zone:
                        continue
                    if played is None:
                        klass = NONE
                    elif not isinstance(played, BoardMove):
                        klass = OTHER
                    elif square_to_index(played.from_square, size) != idx:
                        klass = OTHER
                    elif played.promotion_target_id is not None:
                        klass = PROMO
                    else:
                        klass = SAME
                    total = 0
                    from_square = 0
                    promotions = 0
                    for a in legal:
                        total += 1
                        if isinstance(a, BoardMove) and square_to_index(a.from_square, size) == idx:
                            from_square += 1
                            if a.promotion_target_id is not None:
                                promotions += 1
                    recomputed[klass] += 1
                    per_seed.setdefault(seed, Counter())[klass] += 1
                    if klass == PROMO and total == 1 and promotions == 1:
                        recomputed["forced"] += 1
                    if klass == PROMO and from_square - promotions >= 1:
                        recomputed["sibling"] += 1
                    per_event[(seed, depth, game["game_index"], ply, idx)] = dict(
                        legal_actions_total=total,
                        actions_from_paid_square=from_square,
                        promotions_from_paid_square=promotions,
                        promotion_is_only_legal_action=total == 1 and promotions == 1,
                        promotion_is_only_action_from_square=from_square == promotions
                        and promotions >= 1,
                        has_unpromoted_sibling=from_square - promotions >= 1,
                        played_class=klass,
                    )
                if played is None or not ok:
                    break
                try:
                    state = apply_action(state, played, compiled)
                except Exception:  # noqa: BLE001 - counted, not hidden
                    ok = False
                    break
                ply += 1
            if not ok:
                replay_mismatch += 1
                continue
            status = state.terminal_status
            replayed = {
                "status": status.status.value if status.is_terminal else "watchdog",
                "winner": status.winner if status.is_terminal else None,
                "plies": state.ply_count - start_ply,
            }
            if replayed != {
                "status": game["status"],
                "winner": game["winner"],
                "plies": game["plies"],
            }:
                replay_mismatch += 1
            games += 1

    summary = stored["summary"]
    check(
        "recomputed_classes_match_summary",
        all(recomputed[k] == summary[k] for k in (PROMO, SAME, OTHER, NONE)),
        {k: [recomputed[k], summary[k]] for k in (PROMO, SAME, OTHER, NONE)},
    )
    check(
        "forced_count_matches_summary",
        recomputed["forced"] == summary["played_promotion_was_forced"],
        [recomputed["forced"], summary["played_promotion_was_forced"]],
    )
    check(
        "sibling_count_matches_summary",
        recomputed["sibling"] == summary["played_promotion_had_an_unpromoted_sibling"],
        [recomputed["sibling"], summary["played_promotion_had_an_unpromoted_sibling"]],
    )
    check(
        "contact_total_reconciles",
        sum(summary[k] for k in (PROMO, SAME, OTHER, NONE)) == summary["in_zone_contact"],
        summary["in_zone_contact"],
    )
    check(
        "contact_total_matches_stage_12",
        summary["in_zone_contact"] == stage12["summary"]["in_zone_contact"]
        and all(summary[k] == stage12["summary"][k] for k in (PROMO, SAME, OTHER, NONE)),
        summary["in_zone_contact"],
    )
    check("no_replay_mismatches", replay_mismatch == 0 and summary["replay_mismatches"] == 0, replay_mismatch)
    check("every_played_move_is_legal_in_the_reconstruction", illegal_played == 0, illegal_played)
    check("games_scanned_reconciles", games == summary["games_scanned"], [games, summary["games_scanned"]])

    stored_events = {
        (e["seed"], e["depth"], e["game_index"], e["ply"], e["square"]): e for e in stored["events"]
    }
    missing = sorted(set(per_event) - set(stored_events))
    extra = sorted(set(stored_events) - set(per_event))
    field_mismatch = {}
    for key, mine in per_event.items():
        theirs = stored_events.get(key)
        if theirs is None:
            continue
        diff = {k: [mine[k], theirs.get(k)] for k in mine if mine[k] != theirs.get(k)}
        if diff:
            field_mismatch[key] = diff
    check(
        "every_event_option_set_matches_independent_walk",
        not missing and not extra and not field_mismatch,
        dict(missing=missing[:5], extra=extra[:5], mismatched=list(field_mismatch.items())[:5]),
    )
    check("event_count_matches_contacts", len(stored["events"]) == summary["in_zone_contact"], len(stored["events"]))
    check(
        "single_legal_action_contacts_reconciles",
        sum(1 for e in stored["events"] if e["legal_actions_total"] == 1)
        == summary["contacts_with_a_single_legal_action"],
        summary["contacts_with_a_single_legal_action"],
    )

    per_seed_stored = {row["seed"]: row for row in stored["per_seed"]}
    mismatched = {
        seed: {
            k: [counts.get(k, 0), per_seed_stored.get(seed, {}).get(k, 0)]
            for k in (PROMO, SAME, OTHER, NONE)
            if counts.get(k, 0) != per_seed_stored.get(seed, {}).get(k, 0)
        }
        for seed, counts in per_seed.items()
    }
    mismatched = {seed: diff for seed, diff in mismatched.items() if diff}
    check(
        "per_seed_rows_match_independent_walk",
        not mismatched and not (set(per_seed_stored) - set(per_seed)),
        dict(mismatched=mismatched, seeds_only_in_result=sorted(set(per_seed_stored) - set(per_seed))),
    )
    per_game_sum = sum(row["in_zone_contact"] for row in stored["per_game"])
    check("per_game_rows_sum_to_total", per_game_sum == summary["in_zone_contact"], per_game_sum)

    promoted = summary[PROMO]
    forced = summary["played_promotion_was_forced"]
    if promoted == 0:
        expected = "no_played_promotions_to_classify"
    elif forced == promoted:
        expected = "every_played_contact_promotion_was_forced"
    elif forced == 0:
        expected = "no_played_contact_promotion_was_forced"
    else:
        expected = "played_contact_promotions_are_a_mixture_of_forced_and_optional"
    check("decision_rule_reproduces", expected == summary["decision"], expected)

    blob = (HERE / "results_stage13_option_set.json").read_text(encoding="utf-8").lower()
    check(
        "withdrawn_rate_contrast_absent",
        "outside_zone" not in blob and "in_zone_rate_outside" not in blob,
        [],
    )

    verdict = "all_checks_passed" if all(c["passed"] for c in checks) else "checks_failed"
    payload = dict(
        role="DEEPSEEK_AUX",
        verifier="verify_stage13_option_set.py",
        verdict=verdict,
        checks=checks,
        independent_recomputation=dict(recomputed),
        scope="board 4, classic_like, the six stored Stage-8 files; replay only",
    )
    (HERE / "verification_stage13_option_set.json").write_text(
        json.dumps(payload, indent=1) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=1))
    return 0 if verdict == "all_checks_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
