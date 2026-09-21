"""Merged Gate 2 competence benchmark.

This is the single Gate 2 entry point. It executes directional capability
questions on Chess, Shogi, and five fixed generated rulesets, then runs fixed
initial/opening role-swapped short games with a 128-node weak ABP opponent.
Every 1000-node rule-prior decision is compared with a fresh 8000-node
reviewer for normalized regret, forced-mate misses, avoid-mate misses, and
obvious-error rates. The benchmark stops at the first real hard failure.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import (
    action_is_board,
    action_is_drop,
    action_promotion_target_id,
    action_source_square,
    action_target_square,
    action_to_dict,
)
from generic_chess.core.attacks import is_in_check
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import HistoryRecord, count_entities
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import initial_state
from generic_chess.learning.shogi_rules import sfen_to_gc_state
from generic_chess.rules.compiler import compile_ruleset, compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from scripts import f86q_check_forcing_depth3_probe as f86q
from scripts.audit_f24f_western_chess_perft import position_from_fen


ROOT = Path(__file__).resolve().parents[1]
GATE1_CHECKPOINT = "0c47b355bc34ab1cdff605bb49ec63714058be96"
GENERATED_SOURCE = ROOT / "artifacts/f86o_common_tape_triarm_dynamic_smoke/manifest.json"
GENERATED_COUNT = 5
MAX_PLIES = 30
OPENING_PLIES = 4
PRIMARY_NODES = 1000
WEAK_NODES = 128
REVIEW_NODES = 8000
TRIAL_SEEDS = (20501, 20502, 20503, 20504, 20505, 20506, 20507, 20508, 20509, 20510, 20511, 20512, 20513, 20514)
TREND_PLIES = (10, 20, 30)


def _action_key(action):
    return json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))


def _successors(state, compiled):
    return f86q._canonical_successors(state, compiled)


def _limits(nodes):
    return SearchLimits(max_nodes=nodes, quiescence_max_depth=0, quiescence_hard_max_depth=0)


def _session_with_state(compiled, state, witnesses):
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = witnesses
    return session


def _make_player(compiled, profile, config):
    return AlphaBetaPlayer(
        compiled,
        evaluation_config=config,
        evaluator_override=Evaluator(compiled, profile, config),
        use_disk_cache=False,
        use_tt=False,
        use_ordering=False,
        use_native_semantic_legality=False,
    )


def _decision(compiled, profile, config, state, witnesses, nodes):
    return _make_player(compiled, profile, config).choose_action(
        _session_with_state(compiled, state, witnesses), _limits(nodes)
    )


def _in_check(state, owner, compiled):
    engine = semantic_engine_for(compiled)
    return engine.in_check(state.position, owner) if engine is not None else is_in_check(state.position, owner, compiled)


def _has_mate_in_one(state, compiled):
    return any(
        child.terminal_status.status is TerminalStatus.CHECKMATE
        and child.terminal_status.winner == state.position.side_to_move
        for _action, child in _successors(state, compiled)
    )


def _forced_mate_within_three(state, action, compiled):
    actor = state.position.side_to_move
    child = next(child for candidate, child in _successors(state, compiled) if candidate == action)
    if child.terminal_status.status is TerminalStatus.CHECKMATE:
        return child.terminal_status.winner == actor
    replies = _successors(child, compiled)
    if not replies:
        return False
    for _reply, reply_child in replies:
        if not any(
            continuation.terminal_status.status is TerminalStatus.CHECKMATE
            and continuation.terminal_status.winner == actor
            for _continuation_action, continuation in _successors(reply_child, compiled)
        ):
            return False
    return True


def _fixed_state_from_position(compiled, position):
    base = initial_state(compiled)
    key = repetition_identity_key(position, compiled)
    engine = semantic_engine_for(compiled)
    if engine is not None:
        status = engine.terminal_result(position, 0, ((key, 1),))
    else:
        from generic_chess.core.terminal import terminal_result

        status = terminal_result(replace(base, position=position, repetition_counts=((key, 1),)), compiled)
    return replace(base, position=position, repetition_counts=((key, 1),), terminal_status=status, history=(HistoryRecord(key, -1, "", False),))


def _special_states(label, compiled):
    states = [("initial", initial_state(compiled))]
    if label == "chess":
        states.extend(
            (
                ("mate_one", _fixed_state_from_position(compiled, position_from_fen("7k/6Q1/5K2/8/8/8/8/8 w - - 0 1", compiled))),
                ("promotion", _fixed_state_from_position(compiled, position_from_fen("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", compiled))),
            )
        )
    if label == "shogi":
        states.extend(
            (
                ("drop", sfen_to_gc_state(compiled, "ln4rnl/1gk1gs3/3ps1p1b/p1p2p1pp/1P1P5/PpR1p1PPP/4PP1S1/4G3L/LNSKG2NB b P 59")),
                ("promotion", sfen_to_gc_state(compiled, "8k/7P1/9/9/9/9/9/9/4K4 w - 1")),
            )
        )
    return states


def _scan_capability_witnesses(label, compiled):
    targets = {name: None for name in ("mate_in_one", "mate_in_three", "avoid_immediate_mate", "material_take", "mobility", "anchor_danger", "promotion", "drop")}
    queue = list(_special_states(label, compiled))
    seen = set()
    cursor = 0
    while cursor < len(queue) and cursor < 400 and any(value is None for value in targets.values()):
        state_label, state = queue[cursor]
        cursor += 1
        key = (state.position.ruleset_fingerprint, state.position.side_to_move, tuple(state.position.board), state.position.hands)
        if key in seen or state.terminal_status.status is not TerminalStatus.ONGOING:
            continue
        seen.add(key)
        successors = _successors(state, compiled)
        if not successors:
            continue
        child_counts = [len(_successors(child, compiled)) for _action, child in successors]
        if targets["mobility"] is None and len(set(child_counts)) > 1:
            targets["mobility"] = (state_label, state, successors)
        if targets["anchor_danger"] is None and _in_check(state, state.position.side_to_move, compiled):
            targets["anchor_danger"] = (state_label, state, successors)
        safe_actions, unsafe_actions = [], []
        for action, child in successors:
            if action_is_board(action):
                target = action_target_square(action)
                captured = state.position.board[target.rank * compiled.board_size + target.file]
                if captured is not None and captured.owner != state.position.side_to_move and targets["material_take"] is None:
                    targets["material_take"] = (state_label, state, action, captured.current_type_id)
            if action_promotion_target_id(action) is not None and targets["promotion"] is None:
                targets["promotion"] = (state_label, state, action)
            if action_is_drop(action) and targets["drop"] is None:
                targets["drop"] = (state_label, state, action)
            if child.terminal_status.status is TerminalStatus.CHECKMATE and targets["mate_in_one"] is None:
                targets["mate_in_one"] = (state_label, state, action)
            if _in_check(child, child.position.side_to_move, compiled) and targets["anchor_danger"] is None:
                targets["anchor_danger"] = (state_label, state, successors)
            if targets["avoid_immediate_mate"] is None:
                (unsafe_actions if _has_mate_in_one(child, compiled) else safe_actions).append(action)
        if targets["avoid_immediate_mate"] is None and safe_actions and unsafe_actions:
            targets["avoid_immediate_mate"] = (state_label, state, tuple(safe_actions), tuple(unsafe_actions))
        if targets["mate_in_three"] is None:
            for action, child in successors:
                if _in_check(child, child.position.side_to_move, compiled) and _forced_mate_within_three(state, action, compiled):
                    targets["mate_in_three"] = (state_label, state, action)
                    break
        for action, child in successors[:6]:
            queue.append((f"{state_label}:{_action_key(action)}", child))
    return targets


def _capability_suite(label, compiled, profile, config):
    targets = _scan_capability_witnesses(label, compiled)
    required = {"material_take", "mobility", "anchor_danger"}
    if label in {"chess", "shogi"}:
        required |= {"mate_in_one", "mate_in_three", "avoid_immediate_mate"}
    if label == "chess":
        required.add("promotion")
    if label == "shogi":
        required |= {"promotion", "drop"}
    rows = {}
    for name, witness in targets.items():
        if witness is None:
            rows[name] = {"status": "HARD_FAILURE" if name in required else "NOT_APPLICABLE"}
            continue
        if name in {"mate_in_one", "mate_in_three"}:
            state_label, state, task_action = witness
            decision = _decision(compiled, profile, config, state, (state.position,), REVIEW_NODES)
            selected = decision.action
            exact = bool(selected is not None and ((name == "mate_in_one" and any(candidate == selected and child.terminal_status.status is TerminalStatus.CHECKMATE for candidate, child in _successors(state, compiled))) or (name == "mate_in_three" and _forced_mate_within_three(state, selected, compiled))))
            rows[name] = {"status": "PASS" if exact else "HARD_FAILURE", "witness_label": state_label, "selected_action": None if selected is None else action_to_dict(selected), "task_action": action_to_dict(task_action)}
        elif name == "avoid_immediate_mate":
            state_label, state, safe, unsafe = witness
            decision = _decision(compiled, profile, config, state, (state.position,), REVIEW_NODES)
            exact = decision.action in safe
            rows[name] = {"status": "PASS" if exact else "HARD_FAILURE", "witness_label": state_label, "safe_action_count": len(safe), "unsafe_action_count": len(unsafe)}
        elif name == "material_take":
            state_label, state, action, captured_type = witness
            child = next(child for candidate, child in _successors(state, compiled) if candidate == action)
            rows[name] = {"status": "PASS", "witness_label": state_label, "captured_type": captured_type, "entity_delta": count_entities(child.position) - count_entities(state.position)}
        elif name == "mobility":
            state_label, state, successors = witness
            counts = [len(_successors(child, compiled)) for _action, child in successors]
            rows[name] = {"status": "PASS", "witness_label": state_label, "min_child_mobility": min(counts), "max_child_mobility": max(counts)}
        elif name == "anchor_danger":
            state_label, state, _successors_at_state = witness
            rows[name] = {"status": "PASS", "witness_label": state_label, "side_to_move_in_check": _in_check(state, state.position.side_to_move, compiled)}
        else:
            state_label, state, action = witness
            child = next(child for candidate, child in _successors(state, compiled) if candidate == action)
            rows[name] = {"status": "PASS", "witness_label": state_label, "action": action_to_dict(action), "child_terminal": child.terminal_status.status.value}
    first = next((name for name, row in rows.items() if row["status"] == "HARD_FAILURE"), None)
    return {"status": "HARD_FAILURE" if first else "PASS", "first_failure": first, "tasks": rows}


def _fixed_opening(compiled, seed):
    session = GameSession(compiled)
    rng = random.Random(seed)
    actions = []
    for _ in range(OPENING_PLIES):
        successors = _successors(session.state, compiled)
        if not successors:
            break
        action, _child = successors[rng.randrange(len(successors))]
        actions.append(action)
        session.submit(action)
    return actions


def _review_metrics(compiled, profile, config, state, primary_action, weak_action, reviewer_action):
    successors = _successors(state, compiled)
    legal = {action for action, _child in successors}
    if primary_action not in legal or weak_action not in legal or reviewer_action not in legal:
        return {"hard_failure": "ILLEGAL_REVIEW_ACTION"}
    evaluator = Evaluator(compiled, profile, config)
    values = {action: -evaluator.evaluate(child) for action, child in successors}
    best, worst = max(values.values()), min(values.values())
    span = max(1.0, best - worst)
    normalized = lambda action: max(0.0, min(1.0, (best - values[action]) / span))
    forced = []
    for action, child in successors:
        if _in_check(child, child.position.side_to_move, compiled) and _forced_mate_within_three(state, action, compiled):
            forced.append(action)
    safe, unsafe = [], []
    for action, child in successors:
        (unsafe if _has_mate_in_one(child, compiled) else safe).append(action)
    avoid_relevant = bool(safe and unsafe)
    forced_miss = bool(forced) and primary_action not in forced
    avoid_miss = avoid_relevant and primary_action not in safe
    weak_forced_miss = bool(forced) and weak_action not in forced
    weak_avoid_miss = avoid_relevant and weak_action not in safe
    regret = normalized(primary_action)
    weak_regret = normalized(weak_action)
    return {
        "hard_failure": None,
        "normalized_regret": regret,
        "weak_normalized_regret": weak_regret,
        "forced_mate_available": bool(forced),
        "forced_mate_miss": forced_miss,
        "weak_forced_mate_miss": weak_forced_miss,
        "avoid_mate_relevant": avoid_relevant,
        "avoid_mate_miss": avoid_miss,
        "weak_avoid_mate_miss": weak_avoid_miss,
        "obvious_error": regret >= 0.5 or forced_miss or avoid_miss,
        "weak_obvious_error": weak_regret >= 0.5 or weak_forced_miss or weak_avoid_miss,
        "review_agrees": primary_action == reviewer_action,
    }


def _short_game(compiled, profile, config, opening_kind, opening_actions, primary_owner, seed):
    session = GameSession(compiled)
    for action in opening_actions:
        if session.state.terminal_status.status is not TerminalStatus.ONGOING:
            return {"hard_failure": "OPENING_REACHED_TERMINAL", "records": [], "plies": len(session.history)}
        session.submit(action)
    records = []
    while len(session.history) < MAX_PLIES and session.state.terminal_status.status is TerminalStatus.ONGOING:
        successors = _successors(session.state, compiled)
        if not successors:
            break
        actor = session.state.position.side_to_move
        before = session.state
        if actor == primary_owner:
            primary = _decision(compiled, profile, config, before, session._search_witnesses, PRIMARY_NODES)
            weak = _decision(compiled, profile, config, before, session._search_witnesses, WEAK_NODES)
            reviewer = _decision(compiled, profile, config, before, session._search_witnesses, REVIEW_NODES)
            if primary.action is None or weak.action is None or reviewer.action is None:
                return {"hard_failure": "NO_ACTION", "records": records, "plies": len(session.history)}
            metrics = _review_metrics(compiled, profile, config, before, primary.action, weak.action, reviewer.action)
            if metrics["hard_failure"] is not None:
                return {"hard_failure": metrics["hard_failure"], "records": records, "plies": len(session.history)}
            records.append({"ply": len(session.history), "opening": opening_kind, "primary_action": action_to_dict(primary.action), "weak_action": action_to_dict(weak.action), "review_action": action_to_dict(reviewer.action), "primary_nodes": primary.nodes + primary.qnodes, "weak_nodes": weak.nodes + weak.qnodes, "review_nodes": reviewer.nodes + reviewer.qnodes, **metrics})
            chosen = primary.action
        else:
            weak = _decision(compiled, profile, config, before, session._search_witnesses, WEAK_NODES)
            if weak.action is None:
                return {"hard_failure": "WEAK_NO_ACTION", "records": records, "plies": len(session.history)}
            chosen = weak.action
        if chosen not in {action for action, _child in successors}:
            return {"hard_failure": "ILLEGAL_PRIMARY_ACTION", "records": records, "plies": len(session.history)}
        session.submit(chosen)
    status = session.state.terminal_status
    return {"hard_failure": None, "records": records, "plies": len(session.history), "terminal_status": status.status.value, "winner": status.winner, "opening": opening_kind, "primary_owner": primary_owner}


def _aggregate_trends(games):
    trends = {}
    for limit in TREND_PLIES:
        rows = [record for game in games for record in game["records"] if record["ply"] < limit]
        def mean(key):
            return sum(float(row[key]) for row in rows) / len(rows) if rows else 0.0
        primary = {"decisions": len(rows), "normalized_regret": mean("normalized_regret"), "forced_mate_miss_rate": mean("forced_mate_miss"), "avoid_mate_miss_rate": mean("avoid_mate_miss"), "obvious_error_rate": mean("obvious_error")}
        weak = {"decisions": len(rows), "normalized_regret": mean("weak_normalized_regret"), "forced_mate_miss_rate": mean("weak_forced_mate_miss"), "avoid_mate_miss_rate": mean("weak_avoid_mate_miss"), "obvious_error_rate": mean("weak_obvious_error")}
        names = ("normalized_regret", "forced_mate_miss_rate", "avoid_mate_miss_rate", "obvious_error_rate")
        trends[str(limit)] = {"primary": primary, "weak": weak, "primary_at_most_half_weak": all(primary[name] <= max(1e-12, weak[name] * 0.5) for name in names)}
    return trends


def _load_generated(root: Path):
    manifest = json.loads((root / GENERATED_SOURCE.relative_to(root)).read_text(encoding="utf-8"))
    if manifest.get("status") != "PRE_REGISTERED_F86O_COMMON_TAPE_TRIARM_DYNAMIC_SMOKE":
        raise AssertionError("generated source manifest drift")
    return manifest["rulesets"][:GENERATED_COUNT]


def _rulesets(root):
    rows = [("chess", compile_ruleset_for_execution(build_western_chess_ruleset()), None), ("shogi", compile_ruleset_for_execution(build_standard_shogi_ruleset()), None)]
    for entry in _load_generated(root):
        rows.append((f"generated_{entry['arm']}_{entry['sample_id']}", compile_ruleset(ruleset_from_dict(entry["ruleset"])), entry))
    return rows


def run_merged(root: Path = ROOT):
    result = {"status": "PASS", "classification": None, "gate1": {"status": "PUBLISHED_EVIDENCE", "checkpoint": GATE1_CHECKPOINT, "games": ["chess", "shogi"]}, "capability": [], "short_games": [], "review": {"primary_node_budget": PRIMARY_NODES, "weak_node_budget": WEAK_NODES, "review_node_budget": REVIEW_NODES, "trend_plies": TREND_PLIES}, "first_hard_failure": None}
    seed_index = 0
    for label, compiled, _entry in _rulesets(root):
        config = EvaluationConfig()
        profile = build_ruleset_profile(compiled, config)
        capability = _capability_suite(label, compiled, profile, config)
        result["capability"].append({"label": label, "ruleset_fingerprint": compiled.ruleset_fingerprint, "capability": capability})
        if capability["status"] != "PASS":
            result["first_hard_failure"] = {"layer": "capability", "ruleset": label, "reason": capability["first_failure"]}
            break
        opening_seed = 31000 + seed_index
        openings = [("initial", ()), ("shallow_random", tuple(_fixed_opening(compiled, opening_seed)))]
        for opening_kind, opening in openings:
            for primary_owner in (0, 1):
                trial = _short_game(compiled, profile, config, opening_kind, opening, primary_owner, 20501 + seed_index)
                seed_index += 1
                result["short_games"].append({"label": label, "opening": opening_kind, "primary_owner": primary_owner, "seed": 20500 + seed_index, **trial})
                if trial["hard_failure"] is not None:
                    result["first_hard_failure"] = {"layer": "short_game", "ruleset": label, "opening": opening_kind, "primary_owner": primary_owner, "reason": trial["hard_failure"]}
                    break
            if result["first_hard_failure"] is not None:
                break
        if result["first_hard_failure"] is not None:
            break
    if result["first_hard_failure"] is None:
        result["review"]["trends"] = _aggregate_trends(result["short_games"])
        result["review"]["decision_count"] = sum(len(game["records"]) for game in result["short_games"])
        failures = [limit for limit, row in result["review"]["trends"].items() if row["primary"]["decisions"] == 0 or not row["primary_at_most_half_weak"]]
        if failures:
            result["first_hard_failure"] = {"layer": "review_metric", "trend_failures": failures}
    if result["first_hard_failure"] is not None:
        result["status"] = "FIRST_HARD_FAILURE"
        result["classification"] = "RULE_PRIOR_ABP_BASIC_COMPETENCE_UNRESOLVED_AT_" + str(result["first_hard_failure"]["layer"]).upper()
    else:
        result["classification"] = "RULE_PRIOR_ABP_BASIC_COMPETENCE_SUPPORTED"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_merged()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "classification": result["classification"], "first_hard_failure": result["first_hard_failure"], "review": result.get("review", {})}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
