"""Independent check of results_stage12_contact_choice.json.

This file does not import the scan under test.  It walks the same six stored game
files with its own loop, rebuilds every position from the stored move list, and
re-derives both the contact set and the played-action class.  Sizes, sums, the
decision rule and the absence of the withdrawn rate contrast are checked too.
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
    stored = json.loads((HERE / "results_stage12_contact_choice.json").read_text(encoding="utf-8"))
    stage11 = json.loads(
        (HERE / "results_zone_promotion_source_classification.json").read_text(encoding="utf-8")
    )
    checks: list[dict] = []

    def check(name: str, passed: bool, detail=None) -> None:
        checks.append(dict(check=name, passed=bool(passed), detail=detail))

    seen = set()
    recomputed = Counter()
    per_seed: dict[int, Counter] = {}
    replay_mismatch = 0
    illegal_played = 0
    class_contradictions = []
    missing_contact = 0
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
                    square_to_index(a.from_square, 4)
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
                    elif square_to_index(played.from_square, 4) != idx:
                        klass = OTHER
                    elif played.promotion_target_id is not None:
                        klass = PROMO
                    else:
                        klass = SAME
                    recomputed[klass] += 1
                    per_seed.setdefault(seed, Counter())[klass] += 1
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
    recorded_total = (
        summary[PROMO] + summary[SAME] + summary[OTHER] + summary[NONE]
    )
    check(
        "recomputed_classes_match_summary",
        all(recomputed[k] == summary[k] for k in (PROMO, SAME, OTHER, NONE)),
        {k: [recomputed[k], summary[k]] for k in (PROMO, SAME, OTHER, NONE)},
    )
    check("contact_total_reconciles", recorded_total == summary["in_zone_contact"], recorded_total)
    check(
        "contact_total_matches_stage_11",
        summary["in_zone_contact"] == stage11["summary"]["in_zone_contact"],
        [summary["in_zone_contact"], stage11["summary"]["in_zone_contact"]],
    )
    check("no_replay_mismatches", replay_mismatch == 0 and summary["replay_mismatches"] == 0, replay_mismatch)
    check("every_played_move_is_legal_in_the_reconstruction", illegal_played == 0, illegal_played)
    check("games_scanned_reconciles", games == summary["games_scanned"], [games, summary["games_scanned"]])

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
    extra = set(per_seed_stored) - set(per_seed)
    check("per_seed_rows_match_independent_walk", not mismatched and not extra, dict(mismatched=mismatched, seeds_only_in_result=sorted(extra)))

    per_game_sum = sum(row["in_zone_contact"] for row in stored["per_game"])
    check("per_game_rows_sum_to_total", per_game_sum == summary["in_zone_contact"], per_game_sum)

    for event in stored["events"]:
        if event["played_class"] == PROMO and event["promotions_available_from_square"] < 1:
            class_contradictions.append(event)
        if event["played_class"] == OTHER and event["square"] is None:
            class_contradictions.append(event)
    check("promotion_events_have_a_promotion_available", not class_contradictions, len(class_contradictions))

    if summary["in_zone_contact"] == 0:
        expected = "no_contacts_to_classify"
    elif summary[PROMO] == 0:
        expected = "contacts_are_available_but_unselected"
    elif summary[PROMO] >= 0.5 * summary["in_zone_contact"]:
        expected = "contact_promotion_is_usually_played"
    else:
        expected = "contact_choice_is_mixed"
    check("decision_rule_reproduces", expected == summary["decision"], expected)

    blob = (HERE / "results_stage12_contact_choice.json").read_text(encoding="utf-8").lower()
    check(
        "withdrawn_rate_contrast_absent",
        "outside_zone" not in blob and "in_zone_rate_outside" not in blob,
        [],
    )

    verdict = "all_checks_passed" if all(c["passed"] for c in checks) else "checks_failed"
    payload = dict(
        role="DEEPSEEK_AUX",
        verifier="verify_stage12_contact_choice.py",
        verdict=verdict,
        checks=checks,
        independent_recomputation=dict(recomputed),
        scope="board 4, classic_like, the six stored Stage-8 files; replay only",
    )
    (HERE / "verification_stage12_contact_choice.json").write_text(
        json.dumps(payload, indent=1) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=1))
    return 0 if verdict == "all_checks_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
