"""Recheck saved static_v2/Unit choices at matched completed depth; no games."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_from_dict
from generic_chess.session.session import GameSession
from scripts.research_record import record_value


HERE = Path(__file__).resolve().parent
GAMES = HERE / "games.jsonl"
OUT = HERE / "equal_depth_choice_summary.json"
SEEDS = tuple(range(522001, 522009))


def digest(value) -> str:
    raw = json.dumps(record_value(value), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_action(value):
    """Normalize saved-record and public action serializers to one move shape."""
    def square(raw):
        if raw is None:
            return None
        if isinstance(raw, dict):
            return [int(raw["file"]), int(raw["rank"])]
        return [int(raw[0]), int(raw[1])]

    return {
        "actor_type_id": value.get("actor_type_id"),
        "base_type_id": value.get("base_type_id"),
        "from": square(value.get("from_square", value.get("from"))),
        "to": square(value.get("to_square", value.get("to"))),
        "promotion_target_id": value.get("promotion_target_id"),
        "hand_type_id": value.get("hand_type_id"),
        "pattern_id": value.get("pattern_id"),
        "geometry_id": value.get("geometry_id"),
    }


def action_key(action):
    return tuple(json.dumps(canonical_action(record_value(action_to_dict(action))).get(key),
                            sort_keys=True, separators=(",", ":")) for key in (
        "actor_type_id", "base_type_id", "from", "to",
        "promotion_target_id", "hand_type_id",
    ))


def submit_saved_action(session: GameSession, value):
    matches = [
        action for action in session.legal_actions()
        if canonical_action(record_value(action_to_dict(action))) == canonical_action(value)
    ]
    if len(matches) != 1:
        raise AssertionError(f"saved action not uniquely legal: matches={len(matches)} value={value}")
    session.submit(matches[0])


def checkpoint(compiled, profile_data, kind: str):
    ids = [piece_type.type_id for piece_type in compiled.piece_types]
    anchors = {piece_type.type_id for piece_type in compiled.piece_types if piece_type.is_anchor}
    if kind == "unit":
        board = {type_id: (0.0 if type_id in anchors else 1.0) for type_id in ids}
        hand = dict(board)
    else:
        board = {type_id: float(profile_data["board"][type_id]) / 1000.0 for type_id in ids}
        hand = {type_id: float(profile_data["hand"][type_id]) / 1000.0 for type_id in ids}
    return LearnableMaterialCheckpoint(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        evaluation_profile_version=f"primary-static-5x5-{kind}",
        board_weights=board,
        hand_weights=hand,
        material_scale=256,
        value_scale=10.0,
        reference_median=1.0,
    )


def search(compiled, native, cp, session):
    engine = SemanticSearchEngine(compiled, native, checkpoint=cp, tt_megabytes=0)
    limits = SearchLimits(
        max_depth=3,
        max_nodes=None,
        max_time_seconds=None,
        quiescence_max_depth=0,
    )
    result = engine.search(session, limits, root_window_pruning=False)
    if result.completed_depth != 3 or result.termination_reason not in ("completed", "completed_depth"):
        raise AssertionError(
            f"D3 did not complete: depth={result.completed_depth} reason={result.termination_reason}"
        )
    return {
        "action": record_value(action_to_dict(result.action)) if result.action is not None else None,
        "action_key": action_key(result.action) if result.action is not None else None,
        "score": int(result.score),
        "depth": int(result.completed_depth),
        "nodes": int(result.nodes),
        "qnodes": int(result.qnodes),
        "elapsed_seconds": float(result.elapsed_seconds),
        "termination_reason": result.termination_reason,
        "pv": [record_value(action_to_dict(action)) for action in result.principal_variation],
    }


def main():
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite frozen audit output: {OUT}")
    started = time.monotonic()
    rows = [json.loads(line) for line in GAMES.read_text(encoding="utf-8").splitlines() if line]
    arms = defaultdict(dict)
    for row in rows:
        if row.get("candidate") not in ("unit", "static_v2"):
            continue
        root = row["game_id"].split("|", 1)[0]
        key = (root, row["foe"], int(row["candidate_owner"]))
        arm = row["candidate"]
        if arm in arms[key]:
            raise AssertionError(f"duplicate saved arm {key}/{arm}")
        arms[key][arm] = row

    unique_contexts = {}
    paired_queries = 0
    terminal_pairs = 0
    prior_unique_flips = 0
    duplicate_foe_contexts = defaultdict(list)
    for key, pair in sorted(arms.items()):
        if set(pair) != {"unit", "static_v2"}:
            raise AssertionError(f"unpaired frozen game slot: {key}")
        unit_row, static_row = pair["unit"], pair["static_v2"]
        unit_move = next((move for move in unit_row["moves"] if move.get("role") == "candidate"), None)
        static_move = next((move for move in static_row["moves"] if move.get("role") == "candidate"), None)
        if unit_move is None and static_move is None:
            terminal_pairs += 1
            continue
        if unit_move is None or static_move is None:
            raise AssertionError(f"one candidate move missing in frozen pair: {key}")
        if unit_move["state_before"] != static_move["state_before"]:
            raise AssertionError(f"frozen state hashes differ: {key}")
        if int(unit_move["nodes"]) != 8192 or int(static_move["nodes"]) != 8192:
            raise AssertionError(f"recorded node cap differs: {key}")
        paired_queries += 1
        root, foe, owner = key
        context_key = (root, owner, unit_move["state_before"])
        duplicate_foe_contexts[context_key].append((foe, unit_row, static_row, unit_move, static_move))

    if paired_queries != 56 or terminal_pairs != 8:
        raise AssertionError(f"unexpected frozen denominator: paired={paired_queries}, terminal={terminal_pairs}")

    for context_key, variants in sorted(duplicate_foe_contexts.items()):
        variants.sort(key=lambda item: item[0])
        action_pairs = {
            (json.dumps(unit_move["action"], sort_keys=True), json.dumps(static_move["action"], sort_keys=True))
            for _, _, _, unit_move, static_move in variants
        }
        if len(action_pairs) != 1:
            raise AssertionError(f"duplicate foe rows disagree at context {context_key}")
        foe, unit_row, static_row, unit_move, static_move = variants[0]
        if json.dumps(unit_move["action"], sort_keys=True) != json.dumps(static_move["action"], sort_keys=True):
            prior_unique_flips += 1
        unique_contexts[context_key] = {
            "foe": foe,
            "unit_row": unit_row,
            "static_row": static_row,
            "state_before": unit_move["state_before"],
            "prior_unit_action": unit_move["action"],
            "prior_static_v2_action": static_move["action"],
        }
    if len(unique_contexts) != 37 or prior_unique_flips != 14:
        raise AssertionError(f"unexpected unique denominator/flips: {len(unique_contexts)}/{prior_unique_flips}")

    compiled_by_seed = {}
    profiles_by_seed = {}
    results = []
    for (root, owner, state_hash), item in sorted(unique_contexts.items()):
        seed = int(root.split("-", 1)[0])
        if seed not in SEEDS:
            raise AssertionError(f"unexpected seed: {seed}")
        if seed not in compiled_by_seed:
            rules_path = HERE / f"rule-{seed}.json"
            profile_path = HERE / f"profile-{seed}.json"
            ruleset = ruleset_from_dict(json.loads(rules_path.read_text(encoding="utf-8")))
            compiled = compile_legacy_ruleset_for_semantic_execution(ruleset)
            profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
            if profile_data["fingerprint"] != compiled.ruleset_fingerprint:
                raise AssertionError(f"saved profile fingerprint mismatch for {seed}")
            generated_profile = build_ruleset_profile(compiled, EvaluationConfig())
            for type_id in profile_data["board"]:
                if profile_data["board"][type_id] != generated_profile.board_value_by_type[type_id]:
                    raise AssertionError(f"board profile differs from saved source for {seed}/{type_id}")
                if profile_data["hand"][type_id] != generated_profile.hand_value_by_base_type[type_id]:
                    raise AssertionError(f"hand profile differs from saved source for {seed}/{type_id}")
            compiled_by_seed[seed] = (compiled, compile_native_semantic_rules(compiled))
            profiles_by_seed[seed] = profile_data

        compiled, native = compiled_by_seed[seed]
        profile_data = profiles_by_seed[seed]
        session = GameSession(compiled)
        static_row = item["static_row"]
        for action in static_row["opening_actions"]:
            submit_saved_action(session, action)
        target_move = next(move for move in static_row["moves"] if move.get("role") == "candidate")
        for move in static_row["moves"]:
            if move is target_move:
                break
            if move.get("action") is None:
                raise AssertionError("candidate context preceded by a terminal/no-action reply")
            submit_saved_action(session, move["action"])
        reconstructed_hash = digest(session.state)
        if reconstructed_hash != state_hash or target_move["state_before"] != state_hash:
            raise AssertionError(f"saved prefix does not reproduce context {root}/{owner}")
        if session.result.status.value != "ongoing":
            raise AssertionError(f"saved candidate context is terminal {root}/{owner}")

        unit_cp = checkpoint(compiled, profile_data, "unit")
        static_cp = checkpoint(compiled, profile_data, "static_v2")
        unit_result = search(compiled, native, unit_cp, session)
        static_result = search(compiled, native, static_cp, session)
        results.append({
            "root": root,
            "owner": int(owner),
            "state_before_sha256": state_hash,
            "canonical_foe_for_replay": item["foe"],
            "reconstructed_history_length": len(session._search_witnesses),
            "prior_node_capped_choice_changed": item["prior_unit_action"] != item["prior_static_v2_action"],
            "prior": {"unit_action": item["prior_unit_action"], "static_v2_action": item["prior_static_v2_action"]},
            "equal_depth": {"unit": unit_result, "static_v2": static_result,
                            "action_changed": unit_result["action_key"] != static_result["action_key"],
                            "score_changed": unit_result["score"] != static_result["score"]},
        })

    prior_flips = sum(result["prior_node_capped_choice_changed"] for result in results)
    depth_flips = sum(result["equal_depth"]["action_changed"] for result in results)
    prior_scores = sum(result["prior"]["unit_action"] != result["prior"]["static_v2_action"] for result in results)
    summary = {
        "schema": "primary-static-v2-equal-depth-choice-audit-v1",
        "question": "Do prior static_v2-vs-Unit first-action changes survive equal completed depth on the same saved candidate96 contexts?",
        "protocol": {"contexts": len(results), "paired_queries": paired_queries,
                     "terminal_pairs_excluded": terminal_pairs, "distinct_prior_node_capped_action_flips": prior_unique_flips,
                     "depth": 3, "qdepth": 0, "tt_megabytes": 0,
                     "root_window_pruning": False, "node_limit": None, "time_limit_seconds": None,
                     "ruleset_seeds": list(SEEDS), "new_games": False, "training": False},
        "counts": {"matched_depth_action_flips": depth_flips,
                   "matched_depth_action_flip_rate": depth_flips / len(results),
                   "matched_depth_score_changes": sum(r["equal_depth"]["score_changed"] for r in results),
                   "prior_node_capped_action_flips": prior_flips},
        "scope": "Finite paired decision sensitivity on 37 state-clustered frozen generated-5x5 contexts; not utility, causal reward benefit, population transfer, or a universal price claim.",
        "inputs": {str(path.relative_to(HERE)): file_sha(path) for path in [GAMES] +
                   [HERE / f"rule-{seed}.json" for seed in SEEDS] +
                   [HERE / f"profile-{seed}.json" for seed in SEEDS]},
        "elapsed_wall_seconds": time.monotonic() - started,
        "contexts": results,
    }
    OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(OUT.relative_to(HERE)), "counts": summary["counts"],
                      "elapsed_wall_seconds": summary["elapsed_wall_seconds"],
                      "sha256": file_sha(OUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
