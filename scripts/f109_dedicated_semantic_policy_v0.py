"""F109 dedicated Semantic Policy-v0 corpus, fit, parity, and Arena2 runner.

The evaluator checkpoints are inputs only.  The output policy is a distinct
artifact and is never represented as a value or compact-residual checkpoint.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import random
from typing import Any

import numpy as np

from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.learning.arena import ArenaConfig, run_arena
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.policy import (
    ACTION_FEATURE_WIDTH,
    SemanticPolicyExample,
    fit_semantic_policy_v0,
    policy_target_from_q,
    semantic_action_features,
    semantic_policy_hand_type_indices,
    semantic_state_feature_vector,
)
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.native.semantic import dynamic_features as native_dynamic_features
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


WORK_ORDER_ID = "GENERICCHESS_F109_DEDICATED_SEMANTIC_POLICY_V0_CHESS_SHOGI_ARENA2"
CHECKPOINT_IDS = {
    "western_chess": "55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e",
    "standard_shogi": "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4",
}
CORPUS_PLIES = (4, 8, 12, 16, 20, 24)
ROOT_TRAINING_NODES = 1000
POLICY_TRAINING_SEEDS = {"western_chess": 1090101, "standard_shogi": 1090201}
POLICY_FIT_SEEDS = {"western_chess": 1090111, "standard_shogi": 1090211}
ARENA_SEEDS = {"western_chess": 1090701, "standard_shogi": 1090801}


def _load_checkpoint(path: Path, expected_id: str) -> LearnableMaterialCheckpoint:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload.get("checkpoint"), dict):
        payload = payload["checkpoint"]
    elif isinstance(payload.get("parent"), dict) and payload["parent"].get("checkpoint_id") == expected_id:
        payload = payload["parent"]
    checkpoint = LearnableMaterialCheckpoint.from_dict(payload)
    if checkpoint.checkpoint_id != expected_id:
        raise ValueError(
            f"frozen checkpoint identity mismatch: expected {expected_id}, got {checkpoint.checkpoint_id}"
        )
    return checkpoint


def _replay(compiled, actions) -> GameSession:
    session = GameSession(compiled)
    for action in actions:
        session.submit(action)
    return session


def _collect_parent_games(compiled, native_rules, checkpoint, *, ruleset_name: str) -> list[dict[str, Any]]:
    """Collect exactly eight deterministic parent self-play games."""
    games = []
    for game_index in range(8):
        rng = random.Random(POLICY_TRAINING_SEEDS[ruleset_name] * 1000 + game_index)
        session = GameSession(compiled)
        actions = []
        snapshots: dict[int, tuple] = {}
        engine = SemanticSearchEngine(compiled, native_rules, checkpoint=checkpoint, tt_megabytes=8)
        for ply in range(24):
            if session.result.status.value != "ongoing":
                break
            result = engine.search(
                session,
                SearchLimits(max_depth=12, max_nodes=2000, quiescence_max_depth=0),
            )
            legal = session.legal_actions()
            if not legal:
                break
            action = rng.choice(list(legal)) if rng.random() < 0.10 else result.action
            if action is None or action not in legal:
                action = legal[0]
            session.submit(action)
            actions.append(action)
            if len(actions) in CORPUS_PLIES:
                snapshots[len(actions)] = tuple(actions)
        games.append({"game_index": game_index, "snapshots": snapshots})
    return games


def _root_example(compiled, native_rules, checkpoint, history) -> tuple[SemanticPolicyExample, dict[str, Any]]:
    root = _replay(compiled, history)
    legal = root.legal_actions()
    if not legal:
        raise RuntimeError("eligible policy root has no legal actions")
    packed = pack_semantic_search_position(compiled, native_rules, root)
    legal = tuple(sorted(
        legal,
        key=lambda action: int(pack_semantic_action(native_rules, root.state.position, action)),
    ))
    dynamic = native_dynamic_features(native_rules, packed)
    state = semantic_state_feature_vector(root.state.position, compiled, dynamic)
    action_matrix = [semantic_action_features(compiled, root.state.position, action) for action in legal]
    q_values = []
    for action in legal:
        child = _replay(compiled, history)
        actor = child.state.position.side_to_move
        child.submit(action)
        if child.result.status.value != "ongoing":
            if child.result.winner is None:
                q_values.append(0.0)
            else:
                q_values.append(100000000.0 if child.result.winner == actor else -100000000.0)
            continue
        child_engine = SemanticSearchEngine(compiled, native_rules, checkpoint=checkpoint, tt_megabytes=8)
        result = child_engine.search(
            child,
            SearchLimits(max_depth=12, max_nodes=ROOT_TRAINING_NODES, quiescence_max_depth=0),
        )
        q_values.append(float(-result.score))
    target = policy_target_from_q(q_values)
    example = SemanticPolicyExample(
        state=tuple(float(value) for value in state),
        actions=tuple(tuple(float(value) for value in row) for row in action_matrix),
        target=tuple(float(value) for value in target),
        root_identity=position_identity_key(root.state.position, compiled),
    )
    return example, {
        "root_identity": example.root_identity,
        "ply": len(history),
        "action_count": len(legal),
        "q_values": q_values,
        "target": list(example.target),
        "complete_action_vector": True,
        "action_features": [list(row) for row in example.actions],
        "state_features": list(example.state),
    }


def _split_examples(compiled, native_rules, checkpoint, games):
    rows = []
    seen = set()
    for game in games:
        split = "train" if game["game_index"] < 5 else ("dev" if game["game_index"] == 5 else "holdout")
        for _ply, history in sorted(game["snapshots"].items()):
            key = position_identity_key(_replay(compiled, history).state.position, compiled)
            if key in seen:
                continue
            seen.add(key)
            example, row = _root_example(compiled, native_rules, checkpoint, history)
            row["game_index"] = game["game_index"]
            row["split"] = split
            row["history"] = [action_to_dict(action) for action in history]
            rows.append((split, example, row))
    counts = {name: sum(split == name for split, _, _ in rows) for name in ("train", "dev", "holdout")}
    minimums = {"train": 20, "dev": 4, "holdout": 8}
    if any(counts[name] < minimums[name] for name in minimums):
        raise RuntimeError(f"POLICY_V0_INSUFFICIENT_ON_POLICY_STATES: {counts}")
    return rows, counts


def _performance_rows(compiled, native_rules, checkpoint, model, rows):
    result_rows = []
    for _split, example, row in rows[:24]:
        # The model is intentionally attached only to ordering.  A fresh
        # engine and the frozen evaluator are used for every performance root.
        session = _replay(compiled, tuple(action_from_dict(item) for item in row["history"]))
        engine = SemanticSearchEngine(compiled, native_rules, checkpoint=checkpoint, policy=model, tt_megabytes=8)
        result = engine.search(
            session,
            SearchLimits(max_depth=12, max_nodes=2000, quiescence_max_depth=0),
        )
        result_rows.append({
            "root_identity": row["root_identity"],
            "nodes": result.nodes,
            "policy_nodes": result.policy_nodes,
            "policy_state_inferences": result.policy_state_inferences,
            "policy_actions_scored": result.policy_actions_scored,
            "state_inferences_equal_nodes": result.policy_state_inferences == result.policy_nodes,
        })
    return result_rows


def _diagnostics(model, rows):
    diagnostics = {}
    for split in ("train", "dev", "holdout"):
        selected = [item for item in rows if item[0] == split]
        cross_entropy = []
        kl = []
        top_agreement = []
        pairwise = []
        regrets = []
        target_entropy = []
        policy_entropy = []
        for _split, example, row in selected:
            logits = model.logits(example.state, example.actions)
            shifted = logits - np.max(logits)
            probs = np.exp(shifted)
            probs /= np.sum(probs)
            target = np.asarray(example.target, dtype=np.float64)
            q = np.asarray(row["q_values"], dtype=np.float64)
            cross_entropy.append(float(-np.sum(target * np.log(np.maximum(probs, 1e-300)))))
            kl.append(float(np.sum(target * np.log(np.maximum(target, 1e-300) / np.maximum(probs, 1e-300)))))
            top_agreement.append(float(int(np.argmax(probs) == np.argmax(q))))
            pair_total = pair_correct = 0
            for left in range(len(q)):
                for right in range(left + 1, len(q)):
                    if q[left] == q[right]:
                        continue
                    pair_total += 1
                    pair_correct += int((q[left] - q[right]) * (logits[left] - logits[right]) > 0)
            pairwise.append(pair_correct / pair_total if pair_total else 1.0)
            regrets.append(float(np.max(q) - q[int(np.argmax(probs))]))
            target_entropy.append(float(-np.sum(target * np.log(np.maximum(target, 1e-300)))))
            policy_entropy.append(float(-np.sum(probs * np.log(np.maximum(probs, 1e-300)))))
        diagnostics[split] = {
            "roots": len(selected),
            "cross_entropy": float(np.mean(cross_entropy)) if cross_entropy else None,
            "kl_target_policy": float(np.mean(kl)) if kl else None,
            "top1_q1k_agreement": float(np.mean(top_agreement)) if top_agreement else None,
            "complete_pairwise_ranking_accuracy": float(np.mean(pairwise)) if pairwise else None,
            "q1k_regret_policy_top": float(np.mean(regrets)) if regrets else None,
            "target_entropy": float(np.mean(target_entropy)) if target_entropy else None,
            "policy_entropy": float(np.mean(policy_entropy)) if policy_entropy else None,
        }
    return diagnostics


def run_ruleset(name: str, builder, checkpoint_path: Path, output_dir: Path) -> dict[str, Any]:
    compiled = compile_semantic_ruleset(builder())
    native_rules = compile_native_semantic_rules(compiled)
    checkpoint = _load_checkpoint(checkpoint_path, CHECKPOINT_IDS[name])
    games = _collect_parent_games(compiled, native_rules, checkpoint, ruleset_name=name)
    rows, counts = _split_examples(compiled, native_rules, checkpoint, games)
    train = tuple(example for split, example, _row in rows if split == "train")
    model = fit_semantic_policy_v0(
        train,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        corpus_config={
            "games": 8, "nodes_per_move": 2000, "max_depth": 12,
            "tt_megabytes": 8, "epsilon": 0.10, "max_plies": 24,
            "retained_plies": list(CORPUS_PLIES), "split_by_whole_games": {"train": [0, 1, 2, 3, 4], "dev": [5], "holdout": [6, 7]},
        },
        seed=POLICY_FIT_SEEDS[name],
        hand_type_indices=semantic_policy_hand_type_indices(compiled, native_rules),
    )
    persisted = model.to_dict()
    restored = type(model).from_dict(persisted)
    reload_identity = all(
        np.array_equal(model.logits(example.state, example.actions), restored.logits(example.state, example.actions))
        for _split, example, _row in rows[:24]
    )
    performance = _performance_rows(compiled, native_rules, checkpoint, model, rows)
    diagnostics = _diagnostics(model, rows)
    arena_config = ArenaConfig(
        pairs=2, nodes_per_move=1_000_000, max_depth=12, tt_megabytes=8,
        opening_seed=ARENA_SEEDS[name], opening_count=2, min_plies=2, max_plies=6,
        workers=1, move_time_seconds=1.0, root_window_pruning=True,
    )
    arena = run_arena(compiled, native_rules, checkpoint, checkpoint, arena_config, policy=model)
    classification = (
        "SEMANTIC_POLICY_V0_SURVIVES" if arena.mean_pair_score > 0.5
        else "SEMANTIC_POLICY_V0_EQUAL" if arena.mean_pair_score == 0.5
        else "SEMANTIC_POLICY_V0_REJECTED"
    )
    output = {
        "work_order_id": WORK_ORDER_ID,
        "ruleset": name,
        "frozen_checkpoint_id": checkpoint.checkpoint_id,
        "policy_artifact": persisted,
        "corpus_counts": counts,
        "rows": [row for _split, _example, row in rows],
        "reload_identity": reload_identity,
        "diagnostics": diagnostics,
        "performance": performance,
        "arena_config": asdict(arena_config),
        "arena": {
            "pair_scores": list(arena.pair_scores),
            "mean_pair_score": arena.mean_pair_score,
            "child_better_pairs": arena.child_better_pairs,
            "tied_pairs": arena.tied_pairs,
            "child_worse_pairs": arena.child_worse_pairs,
            "game_wins": arena.game_wins,
            "game_draws": arena.game_draws,
            "game_losses": arena.game_losses,
        },
        "classification": classification,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{name}.json").write_text(json.dumps(output, sort_keys=True), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chess-checkpoint", type=Path, required=True)
    parser.add_argument("--shogi-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ruleset", choices=("western_chess", "standard_shogi"), default=None)
    args = parser.parse_args()
    builders = {
        "western_chess": (build_western_chess_ruleset, args.chess_checkpoint),
        "standard_shogi": (build_standard_shogi_ruleset, args.shogi_checkpoint),
    }
    names = (args.ruleset,) if args.ruleset else tuple(builders)
    results = {
        name: run_ruleset(name, builders[name][0], builders[name][1], args.output_dir)
        for name in names
    }
    overall = "SEMANTIC_POLICY_V0_SURVIVES" if results and all(
        result["classification"] == "SEMANTIC_POLICY_V0_SURVIVES" for result in results.values()
    ) else "SEMANTIC_POLICY_V0_NOT_UNIFORMLY_SURVIVING"
    (args.output_dir / "summary.json").write_text(
        json.dumps({"work_order_id": WORK_ORDER_ID, "rulesets": results, "overall_classification": overall}, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps({"work_order_id": WORK_ORDER_ID, "overall_classification": overall}, sort_keys=True))


if __name__ == "__main__":
    main()
