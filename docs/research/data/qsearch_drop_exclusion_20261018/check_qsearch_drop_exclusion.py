"""Are ordinary quiet drops a measurable blind spot of served qsearch?

DEEPSEEK_AUX private probe (2026-10-18), segment
``4615243a-f2b9-40ce-a634-266bb0b2e3b7``.  Plan:
``plan.json`` in this directory, written before the run.

The served quiescence policy (:func:`classify_noisy`) includes captures,
promotions, material-inventory changes, terminals and checks, but excludes an
ordinary quiet drop.  A drop can nevertheless create a new attack on an
enemy piece.  This probe counts such positions on fresh generated 4x4 rules
and asks whether they show a larger served depth-2 vs depth-3 score change
than positions without an excluded drop.

This is a scoped search-horizon measurement, not a strength/utility claim:
no games are played, "undefended" uses pseudo-attack geometry (pins ignored)
and the panel is 12 fixed rules with one position each.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import random  # noqa: E402

from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402
from generic_chess.ai.alphabeta.quiescence import classify_noisy  # noqa: E402
from generic_chess.ai.alphabeta.search import run_root_search  # noqa: E402
from generic_chess.ai.alphabeta.statistics import SearchStatistics  # noqa: E402
from generic_chess.ai.alphabeta.transposition import TranspositionTable  # noqa: E402
from generic_chess.ai.evaluation.config import (  # noqa: E402
    MATE_THRESHOLD,
    EvaluationConfig,
)
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.core.actions import (  # noqa: E402
    action_drop_base_type_id,
    action_is_drop,
    action_to_dict,
)
from generic_chess.core.attacks import (  # noqa: E402
    is_in_check,
    is_square_attacked,
    pseudo_attacks,
)
from generic_chess.core.movegen import legal_actions  # noqa: E402
from generic_chess.core.semantic_executor import semantic_engine_for  # noqa: E402
from generic_chess.core.transition import initial_state, legal_successors  # noqa: E402

HERE = Path(__file__).resolve().parent
SESSION_ID = "4615243a-f2b9-40ce-a634-266bb0b2e3b7"

SEEDS = tuple(range(101, 113))
BOARD_SIZE = 4
HAND_WEIGHT = 0.9
DEPTHS = (2, 3)
SECONDARY_DEPTH = 4
NODE_CAP = 20_000
QMAX_DEPTH = 4
QHARD_DEPTH = 8
START_PLY = 10
MIN_START_ACTIONS = 6
MAX_OFFSETS = 4

OUT = HERE / "results_qsearch_drop_exclusion.json"
LOG = HERE / "plan-log.json"
SOURCE_FILES = (
    "generic_chess/ai/alphabeta/quiescence.py",
    "generic_chess/ai/alphabeta/search.py",
    "generic_chess/ai/alphabeta/statistics.py",
    "generic_chess/core/attacks.py",
    "generic_chess/core/movegen.py",
    "generic_chess/core/transition.py",
    "generic_chess/generation/generator.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def generated_compiled(seed: int):
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=BOARD_SIZE, setup_preset="classic_like")
    )
    return game.compiled_ruleset


def make_searcher(compiled) -> tuple[Evaluator, object]:
    config = EvaluationConfig(hand_weight=HAND_WEIGHT)
    profile = build_ruleset_profile(compiled, config)
    return Evaluator(compiled, profile, config), profile


def sample_start(compiled, seed: int):
    """First deterministic non-terminal state at ply>=10 without a terminal child."""
    for offset in range(MAX_OFFSETS):
        rng = random.Random(seed * 1009 + offset)
        state = initial_state(compiled)
        while state.ply_count < 60:
            if state.terminal_status.is_terminal:
                break
            if state.ply_count >= START_PLY:
                actions = legal_actions(state, compiled)
                children = legal_successors(state, compiled)
                if (
                    len(actions) >= MIN_START_ACTIONS
                    and not any(child.terminal_status.is_terminal for _, child in children)
                ):
                    return state, offset
            children = legal_successors(state, compiled)
            if not children:
                break
            _, state = rng.choice(children)
    return None, None


def search(state, compiled, evaluator, depth: int) -> dict:
    stats = SearchStatistics()
    started = time.monotonic()
    action, score, _pv, reason = run_root_search(
        state,
        compiled,
        evaluator,
        TranspositionTable(max_entries=NODE_CAP),
        SearchLimits(
            max_depth=depth,
            max_nodes=NODE_CAP,
            quiescence_max_depth=QMAX_DEPTH,
            quiescence_hard_max_depth=QHARD_DEPTH,
        ),
        None,
        stats,
        use_tt=False,
        use_ordering=True,
    )
    return {
        "action": None if action is None else action_to_dict(action),
        "action_key": None if action is None else str(action),
        "score": score,
        "reason": reason,
        "nodes": stats.nodes,
        "qnodes": stats.qnodes,
        "completed_depth": stats.completed_depth,
        "nonchecking_drop_excluded": stats.nonchecking_drop_excluded,
        "checking_drop_qactions": stats.checking_drop_qactions,
        "seconds": round(time.monotonic() - started, 4),
    }


def drop_categories(state, compiled) -> dict:
    """Cross-check the engine's own noisy-action classification for one position."""
    successors = legal_successors(state, compiled)
    classify_stats = SearchStatistics()
    noisy = classify_noisy(state, successors, compiled, classify_stats)
    noisy_set = set(noisy)
    engine = semantic_engine_for(compiled)
    side = state.position.side_to_move
    excluded, checking, terminal = [], [], []
    for action, child in successors:
        if not action_is_drop(action):
            continue
        gives_check = (
            engine.in_check(child.position, 1 - side)
            if engine is not None
            else is_in_check(child.position, 1 - side, compiled)
        )
        record = {
            "action": action_to_dict(action),
            "action_key": str(action),
            "base_type": action_drop_base_type_id(action),
            "child_terminal": child.terminal_status.is_terminal,
            "gives_check": gives_check,
            "in_noisy_set": action in noisy_set,
        }
        if child.terminal_status.is_terminal:
            terminal.append(record)
        elif gives_check:
            checking.append(record)
        elif action not in noisy_set:
            excluded.append(record)
    return {
        "successors": successors,
        "noisy_count": len(noisy),
        "classify_nonchecking_drop_excluded": classify_stats.nonchecking_drop_excluded,
        "drops_total": sum(1 for a, _c in successors if action_is_drop(a)),
        "excluded": excluded,
        "checking": checking,
        "terminal": terminal,
    }


def blind_threats(child, parent, side: int, compiled, profile) -> list[dict]:
    """New mover attacks on enemy pieces that no enemy piece defends after the drop."""
    n = compiled.board_size
    before = pseudo_attacks(parent.position, side, compiled)
    after = pseudo_attacks(child.position, side, compiled)
    findings = []
    for square in sorted(after - before, key=lambda s: (s.rank, s.file)):
        occupant = child.position.board[square.rank * n + square.file]
        if occupant is None or occupant.owner == side:
            continue
        defended = is_square_attacked(child.position, square, 1 - side, compiled)
        target_value = int(profile.board_value_by_type.get(occupant.current_type_id, 0))
        findings.append(
            {
                "square": [square.file, square.rank],
                "target_type": occupant.current_type_id,
                "target_value": target_value,
                "defended": defended,
            }
        )
    return findings


def analyze_position(seed: int, compiled, profile, evaluator, state, offset: int) -> dict:
    categories = drop_categories(state, compiled)
    side = state.position.side_to_move
    parent_static = evaluator.evaluate(state)
    excluded_records = []
    for record in categories["excluded"]:
        action = next(
            a
            for a, _c in categories["successors"]
            if str(a) == record["action_key"]
        )
        child = next(
            c for a, c in categories["successors"] if str(a) == record["action_key"]
        )
        threats = blind_threats(child, state, side, compiled, profile)
        undefended = [t for t in threats if not t["defended"]]
        drop_value = int(profile.board_value_by_type.get(record["base_type"], 0))
        max_gap = (
            max(t["target_value"] - drop_value for t in undefended) if undefended else None
        )
        confirmation = None
        if undefended:
            child_search = search(child, compiled, evaluator, 1)
            mover_score = -child_search["score"]
            confirmation = {
                "child_score_side_to_move": child_search["score"],
                "child_score_mover_perspective": mover_score,
                "parent_static": parent_static,
                "exceeds_parent_static": mover_score > parent_static,
                "reason": child_search["reason"],
                "nodes": child_search["nodes"],
                "qnodes": child_search["qnodes"],
                "seconds": child_search["seconds"],
            }
        excluded_records.append(
            {
                **record,
                "drop_value": drop_value,
                "new_enemy_attacks": len(threats),
                "blind_threats": len(undefended),
                "threats": threats,
                "max_blind_threat_value_gap": max_gap,
                "confirmation": confirmation,
                "_action": action,
            }
        )
    searches = {depth: search(state, compiled, evaluator, depth) for depth in DEPTHS}
    secondary = search(state, compiled, evaluator, SECONDARY_DEPTH)
    d2, d3 = searches[2], searches[3]
    blind_drops = sum(1 for r in excluded_records if r["blind_threats"] > 0)
    return {
        "seed": seed,
        "offset": offset,
        "ply": state.ply_count,
        "side_to_move": side,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "legal_actions": len(legal_actions(state, compiled)),
        "drops_total": categories["drops_total"],
        "excluded_drops": len(excluded_records),
        "checking_drops": len(categories["checking"]),
        "terminal_drops": len(categories["terminal"]),
        "classify_noisy_count": categories["noisy_count"],
        "classify_nonchecking_drop_excluded": categories[
            "classify_nonchecking_drop_excluded"
        ],
        "blind_threat_drops": blind_drops,
        "attacked_only_drops": sum(
            1 for r in excluded_records if r["new_enemy_attacks"] > 0
        ),
        "max_blind_threat_value_gap": max(
            (
                r["max_blind_threat_value_gap"]
                for r in excluded_records
                if r["max_blind_threat_value_gap"] is not None
            ),
            default=None,
        ),
        "excluded_drop_records": [
            {k: v for k, v in r.items() if k != "_action"} for r in excluded_records
        ],
        "checking_drop_records": categories["checking"],
        "terminal_drop_records": categories["terminal"],
        "searches": {str(d): s for d, s in searches.items()},
        "depth4_secondary": secondary,
        "d2_score": d2["score"],
        "d3_score": d3["score"],
        "d4_score": secondary["score"],
        "d2_action": d2["action"],
        "d3_action": d3["action"],
        "action_equal_2_3": d2["action_key"] == d3["action_key"],
        "abs_score_delta_2_3": abs(d3["score"] - d2["score"]),
        "search_reason_d2": d2["reason"],
        "search_reason_d3": d3["reason"],
    }


def median_or_none(values):
    return statistics.median(values) if values else None


def evaluate_decision(positions: list[dict]) -> dict:
    group = [p for p in positions if p["blind_threat_drops"] > 0]
    rest = [p for p in positions if p["blind_threat_drops"] == 0]
    group_delta = [p["abs_score_delta_2_3"] for p in group]
    rest_delta = [p["abs_score_delta_2_3"] for p in rest]
    group_median = median_or_none(group_delta)
    rest_median = median_or_none(rest_delta)
    group_flips = sum(1 for p in group if not p["action_equal_2_3"])
    rest_flips = sum(1 for p in rest if not p["action_equal_2_3"])
    group_rate = group_flips / len(group) if group else None
    rest_rate = rest_flips / len(rest) if rest else None
    delta_ok = (
        group_median is not None
        and rest_median is not None
        and rest_median > 0
        and group_median >= 2 * rest_median
    )
    delta_ok_zero_rest = (
        group_median is not None
        and rest_median == 0
        and group_median > 0
    )
    flip_ok = (
        group_rate is not None
        and rest_rate is not None
        and group_flips >= 3
        and group_rate >= 2 * rest_rate
    )
    supported = len(group) >= 3 and (delta_ok or delta_ok_zero_rest or flip_ok)
    return {
        "blind_group_positions": len(group),
        "rest_positions": len(rest),
        "blind_group_median_abs_delta": group_median,
        "rest_median_abs_delta": rest_median,
        "delta_ratio": (
            (group_median / rest_median)
            if group_median is not None and rest_median not in (None, 0)
            else None
        ),
        "blind_group_flips": group_flips,
        "rest_flips": rest_flips,
        "blind_group_flip_rate": group_rate,
        "rest_flip_rate": rest_rate,
        "delta_criterion": bool(delta_ok or delta_ok_zero_rest),
        "flip_criterion": bool(flip_ok),
        "supported": bool(supported),
        "outcome": "support" if supported else "no_support",
        "criterion_source": "plan.json decision_rule_written_before_run",
    }


def write_plan_log(started_at: str, elapsed: float, head: str) -> None:
    payload = {
        "role": "DEEPSEEK_AUX",
        "session_id": SESSION_ID,
        "generated_at": started_at,
        "elapsed_seconds": round(elapsed, 2),
        "git_head": head,
        "hashes": {
            str(path): sha256_file(ROOT / path) for path in SOURCE_FILES
        }
        | {
            "plan.json": sha256_file(HERE / "plan.json"),
            "check_qsearch_drop_exclusion.py": sha256_file(Path(__file__)),
        },
        "design": {
            "seeds": list(SEEDS),
            "depths": list(DEPTHS),
            "secondary_depth": SECONDARY_DEPTH,
            "node_cap": NODE_CAP,
            "hand_weight": HAND_WEIGHT,
            "start_recipe": {
                "min_ply": START_PLY,
                "min_actions": MIN_START_ACTIONS,
                "max_offsets": MAX_OFFSETS,
            },
            "quiescence": {
                "max_depth": QMAX_DEPTH,
                "hard_max_depth": QHARD_DEPTH,
            },
            "use_tt": False,
            "use_ordering": True,
        },
    }
    LOG.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    if OUT.exists() and "--allow-overwrite" not in sys.argv[1:]:
        print(f"refusing to overwrite {OUT.name}", file=sys.stderr)
        return 2
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    started = time.monotonic()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    positions: list[dict] = []
    problems: list[str] = []
    for seed in SEEDS:
        try:
            compiled = generated_compiled(seed)
            state, offset = sample_start(compiled, seed)
            if state is None:
                problems.append(f"seed {seed}: no eligible start position")
                continue
            evaluator, profile = make_searcher(compiled)
            record = analyze_position(seed, compiled, profile, evaluator, state, offset)
            positions.append(record)
            print(
                seed,
                "ply",
                record["ply"],
                "drops",
                record["drops_total"],
                "excluded",
                record["excluded_drops"],
                "blind",
                record["blind_threat_drops"],
                "d2",
                record["d2_score"],
                "d3",
                record["d3_score"],
                "delta",
                record["abs_score_delta_2_3"],
                flush=True,
            )
        except Exception as exc:  # keep partial evidence, report failure
            problems.append(f"seed {seed}: {type(exc).__name__}: {exc}")
            print(f"seed {seed} FAILED {type(exc).__name__}: {exc}", flush=True)
    aggregate = {
        "positions": len(positions),
        "positions_with_blind_threat_drop": sum(
            1 for p in positions if p["blind_threat_drops"] > 0
        ),
        "total_excluded_drops": sum(p["excluded_drops"] for p in positions),
        "total_blind_threat_drops": sum(p["blind_threat_drops"] for p in positions),
        "total_attacked_only_drops": sum(p["attacked_only_drops"] for p in positions),
        "total_checking_drops": sum(p["checking_drops"] for p in positions),
        "total_terminal_drops": sum(p["terminal_drops"] for p in positions),
        "classification_crosscheck_mismatches": [
            p["seed"]
            for p in positions
            if p["classify_nonchecking_drop_excluded"] != p["excluded_drops"]
        ],
        "action_flips_2_3": sum(1 for p in positions if not p["action_equal_2_3"]),
        "median_abs_score_delta_2_3": median_or_none(
            [p["abs_score_delta_2_3"] for p in positions]
        ),
        # Descriptive only: rows whose served score is in the mate band measure
        # mate distance, not an evaluation horizon; the pre-written decision
        # rule still runs over every planned position.
        "mate_bound_positions": [
            p["seed"]
            for p in positions
            if abs(p["d2_score"]) >= MATE_THRESHOLD
            or abs(p["d3_score"]) >= MATE_THRESHOLD
        ],
        "search_seconds_total": round(
            sum(
                s["seconds"]
                for p in positions
                for s in list(p["searches"].values()) + [p["depth4_secondary"]]
            )
            + sum(
                r["confirmation"]["seconds"]
                for p in positions
                for r in p["excluded_drop_records"]
                if r["confirmation"]
            ),
            2,
        ),
    }
    decision = evaluate_decision(positions)
    payload = {
        "role": "DEEPSEEK_AUX",
        "session_id": SESSION_ID,
        "question": (
            "In drop-enabled generated rules, how many positions contain a quiet "
            "(non-checking) drop that the served quiescence policy excludes but "
            "that creates a new attack on an undefended enemy piece, and do those "
            "positions show a larger depth-2 vs depth-3 served score change?"
        ),
        "design": {
            "seeds": list(SEEDS),
            "board_size": BOARD_SIZE,
            "setup_preset": "classic_like",
            "hand_weight": HAND_WEIGHT,
            "depths": list(DEPTHS),
            "secondary_depth": SECONDARY_DEPTH,
            "node_cap": NODE_CAP,
            "quiescence_max_depth": QMAX_DEPTH,
            "quiescence_hard_max_depth": QHARD_DEPTH,
            "use_tt": False,
            "use_ordering": True,
        },
        "positions": positions,
        "aggregate": aggregate,
        "decision": decision,
        "problems": problems,
        "nonclaims": [
            "search-horizon measurement only; no games and no strength/utility claim",
            "pseudo-attack geometry ignores pins, so undefended is approximate",
            "12 fixed generated rules with one position each: not a population statement",
            "no change to product code, defaults, caps or frozen panels",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elapsed = time.monotonic() - started
    write_plan_log(started_at, elapsed, head)
    print(json.dumps({"aggregate": aggregate, "decision": decision}, indent=1))
    print("problems", problems)
    print("wrote", OUT.name, "elapsed_s", round(elapsed, 1))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
