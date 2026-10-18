"""DEEPSEEK_AUX bounded follow-up: can the four profitable blind threats be realised?

For each profitable excluded drop, enumerate every legal opponent reply, flag
captures of the dropped piece and moves of the threatened piece, and re-search
the parent at depth 3 with a larger node cap. Descriptive; no utility claim.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from generic_chess.core.actions import (
    action_is_board,
    action_source_square,
    action_target_square,
)
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.transition import legal_successors

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("probe_stage2", HERE / "probe_stage2.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
stage1 = probe.stage1


def review_case(record: dict) -> dict:
    seed = record["seed"]
    compiled = stage1.generated_compiled(seed)
    state, offset = probe.sample_start2(compiled, seed)
    evaluator, profile = stage1.make_searcher(compiled)
    categories = stage1.drop_categories(state, compiled)
    side = state.position.side_to_move
    match = [
        (a, c)
        for a, c in categories["successors"]
        if str(a) == record["action"]
    ]
    assert len(match) == 1, (seed, record["action"], len(match))
    action, child = match[0]
    dropped_square = action_target_square(action)
    target_file, target_rank = record["target_square"]
    target_square = type(dropped_square)(target_file, target_rank)
    replies = []
    for reply, grandchild in legal_successors(child, compiled):
        replies.append(
            {
                "reply": str(reply),
                "captures_dropped": action_is_board(reply)
                and action_target_square(reply) == dropped_square,
                "moves_threatened_piece": action_source_square(reply)
                == target_square,
                "terminal": grandchild.terminal_status.is_terminal,
                "static_mover_after_reply": evaluator.evaluate(grandchild)
                if not grandchild.terminal_status.is_terminal
                else None,
            }
        )
    static_values = [
        r["static_mover_after_reply"]
        for r in replies
        if r["static_mover_after_reply"] is not None
    ]
    depth1 = stage1.search(child, compiled, evaluator, 1)
    replay_mover_score = -depth1["score"]
    stored_payload = json.loads(
        (HERE / "results_stage2_fresh_seeds.json").read_text(encoding="utf-8")
    )
    stored_position = next(p for p in stored_payload["positions"] if p["seed"] == seed)
    stored_confirmation = next(
        rec["confirmation"]
        for rec in stored_position["excluded_drop_records"]
        if rec["action_key"] == str(action)
    )
    large_stats = stage1.SearchStatistics()
    large_action, large_score, _pv, large_reason = stage1.run_root_search(
        state,
        compiled,
        evaluator,
        stage1.TranspositionTable(max_entries=200_000),
        SearchLimits(
            max_depth=3,
            max_nodes=200_000,
            quiescence_max_depth=4,
            quiescence_hard_max_depth=8,
        ),
        None,
        large_stats,
        use_tt=False,
        use_ordering=True,
    )
    return {
        "seed": seed,
        "offset": offset,
        "ply": state.ply_count,
        "action": record["action"],
        "action_key": str(action),
        "parent_static": evaluator.evaluate(state),
        "dropped_base_type": record["base_type"],
        "drop_value": record["drop_value"],
        "target_square": record["target_square"],
        "target_type": record["target_type"],
        "target_value": record["target_value"],
        "legal_replies": len(replies),
        "replies_capturing_dropped": sum(1 for r in replies if r["captures_dropped"]),
        "replies_moving_threatened_piece": sum(
            1 for r in replies if r["moves_threatened_piece"]
        ),
        "terminal_replies": sum(1 for r in replies if r["terminal"]),
        "best_static_mover_after_reply": max(static_values) if static_values else None,
        "worst_static_mover_after_reply": min(static_values) if static_values else None,
        "depth1_child_score_side_to_move": depth1["score"],
        "depth1_mover_score_replay": replay_mover_score,
        "stored_depth1_mover_score": stored_confirmation[
            "child_score_mover_perspective"
        ],
        "stored_depth1_reason": stored_confirmation["reason"],
        "depth1_replay_matches_stored": replay_mover_score
        == stored_confirmation["child_score_mover_perspective"],
        "large_cap": {
            "max_nodes": 200_000,
            "score": large_score,
            "action": None if large_action is None else str(large_action),
            "reason": large_reason,
            "nodes": large_stats.nodes,
            "qnodes": large_stats.qnodes,
            "chosen_this_drop": large_action is not None
            and str(large_action) == str(action),
        },
        "replies": replies,
    }


def main() -> int:
    results = json.loads(
        (HERE / "results_stage2_fresh_seeds.json").read_text(encoding="utf-8")
    )
    profitable = [
        {"seed": p["seed"], **rec}
        for p in results["positions"]
        for r in p["excluded_drop_records"]
        for rec in r["profitable_records"]
    ]
    cases = []
    for record in profitable:
        case = review_case(record)
        cases.append(case)
        print(
            case["seed"],
            case["action_key"],
            "replies",
            case["legal_replies"],
            "capture_dropped",
            case["replies_capturing_dropped"],
            "save_target",
            case["replies_moving_threatened_piece"],
            "best_static",
            case["best_static_mover_after_reply"],
            "parent",
            case["parent_static"],
            "large_chosen",
            case["large_cap"]["chosen_this_drop"],
            flush=True,
        )
    payload = {
        "role": "DEEPSEEK_AUX",
        "session_id": probe.stage1.SESSION_ID,
        "source_result": str(HERE / "results_stage2_fresh_seeds.json"),
        "cases": cases,
        "summary": {
            "cases": len(cases),
            "cases_with_opponent_capture_of_dropped": sum(
                1 for c in cases if c["replies_capturing_dropped"]
            ),
            "cases_with_target_escaping_move": sum(
                1 for c in cases if c["replies_moving_threatened_piece"]
            ),
            "cases_with_terminal_reply": sum(
                1 for c in cases if c["terminal_replies"]
            ),
            "cases_best_static_above_parent": sum(
                1
                for c in cases
                if c["best_static_mover_after_reply"] is not None
                and c["best_static_mover_after_reply"] > c["parent_static"]
            ),
            "cases_chosen_at_larger_cap": sum(
                1 for c in cases if c["large_cap"]["chosen_this_drop"]
            ),
            "depth1_replay_mismatches": [
                c["seed"] for c in cases if not c["depth1_replay_matches_stored"]
            ],
        },
        "nonclaims": [
            "geometry ignores pins; a legal reply list is not a proof of best play",
            "larger node cap is not a solve; reason field states truncation",
            "no strength or utility claim",
        ],
    }
    (HERE / "bound_profitable_cases.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
