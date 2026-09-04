"""F58 Native parity, policy smoke, and paired arena verification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from f50_generic_learnable_evaluator import _ruleset
from f54_direct_capacity_and_gradient_geometry_diagnosis import _parent, _session
from f58_compact_nonlinear_capacity import _corpus, _features
from generic_chess.ai.limits import SearchLimits
from generic_chess.learning.arena import ArenaConfig, run_arena
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.nonlinear import CompactNonlinearResidual
from generic_chess.learning.serialization import stable_sha256
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.semantic import dynamic_features, evaluate as native_evaluate
from generic_chess.native.semantic_engine import SemanticSearchEngine


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".generic_chess_flow" / "f58-compact-nonlinear-native"


def _load_model(path: Path, label: str) -> tuple[dict, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = next(item for item in payload["results"] if item["label"] == label)
    model = next(item for item in result["compact_models"] if item["seed"] == 58011)
    return result, model


def _child(parent, model: dict):
    return parent.child_checkpoint(
        board_weights=parent.board_weights,
        hand_weights=parent.hand_weights,
        dynamic_weights=parent.dynamic_weights,
        compact_nonlinear=model,
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=stable_sha256({"stage": "F58-native", "seed": model["seed"]}),
        training_seed=model["seed"],
    )


def _search_rows(compiled, native, checkpoint, records, nodes: int) -> list[dict]:
    rows = []
    for record in records:
        session = _session(compiled, record)
        result = SemanticSearchEngine(
            compiled, native, checkpoint=checkpoint, tt_megabytes=0
        ).search(
            session,
            SearchLimits(max_depth=4, max_nodes=nodes, quiescence_max_depth=0),
        )
        rows.append({
            "action": None if result.action is None else str(result.action),
            "score": int(result.score),
            "nodes": int(result.nodes),
        })
    return rows


def run(path: Path, label: str, validation_count: int, search_nodes: int, arena_pairs: int) -> dict:
    result, model = _load_model(path, label)
    compiled, native, _profile = _ruleset(label)
    parent = _parent(label)
    child = _child(parent, model)
    compact_model = CompactNonlinearResidual.from_dict(model)
    _payload, corpus = _corpus(label, compiled)
    records = corpus["records"][-validation_count:]

    deltas = []
    for record in records:
        session = _session(compiled, record)
        packed = pack_semantic_search_position(compiled, native, session)
        dynamic = dynamic_features(native, packed)
        features = _features(compiled, native, record)
        residual = float(compact_model.predict([features])[0])
        type_ids = tuple(native.type_ids)
        parent_score = native_evaluate(
            native,
            packed,
            board_values=parent.semantic_quantized_board(type_ids),
            hand_values=parent.semantic_quantized_hand(type_ids),
            dynamic_values=parent.semantic_quantized_dynamic(),
            evaluator_scale=parent.semantic_native_scale,
        )
        child_score = native_evaluate(
            native,
            packed,
            board_values=child.semantic_quantized_board(type_ids),
            hand_values=child.semantic_quantized_hand(type_ids),
            dynamic_values=child.semantic_quantized_dynamic(),
            compact_values=model,
            evaluator_scale=child.semantic_native_scale,
        )
        expected_delta = int(round(residual * child.semantic_native_scale))
        if session.state.position.side_to_move == 1:
            expected_delta = -expected_delta
        deltas.append({
            "actual": int(child_score - parent_score),
            "expected": expected_delta,
            "residual_human": residual,
            "dynamic_dimension": len(dynamic),
        })

    parent_rows = _search_rows(compiled, native, parent, records, search_nodes)
    child_rows = _search_rows(compiled, native, child, records, search_nodes)
    policy = {
        "positions": len(records),
        "move_flip_rate_vs_parent": sum(
            a["action"] != b["action"] for a, b in zip(child_rows, parent_rows)
        ) / len(records),
    }
    openings = None
    if arena_pairs:
        arena = run_arena(
            compiled,
            native,
            parent,
            child,
            ArenaConfig(
                pairs=arena_pairs,
                nodes_per_move=search_nodes,
                max_depth=4,
                tt_megabytes=0,
                opening_seed=580201,
                opening_count=arena_pairs,
                min_plies=2,
                max_plies=4,
                workers=1,
            ),
        )
        openings = {
            "pairs": arena.pair_count,
            "mean_pair_score": arena.mean_pair_score,
            "game_wins": arena.game_wins,
            "game_draws": arena.game_draws,
            "game_losses": arena.game_losses,
        }
    return {
        "label": label,
        "parent_checkpoint_id": parent.checkpoint_id,
        "child_checkpoint_id": child.checkpoint_id,
        "model_seed": model["seed"],
        "model_sha256": stable_sha256(model),
        "offline_selected_width": result["model_selection"]["selected_width"],
        "offline_selected_regularization": result["model_selection"]["selected_regularization"],
        "native_parity": {
            "positions": len(deltas),
            "max_abs_delta_error": max(abs(item["actual"] - item["expected"]) for item in deltas),
            "all_exact": all(item["actual"] == item["expected"] for item in deltas),
        },
        "policy_smoke": policy,
        "arena_smoke": openings,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-json", type=Path, required=True)
    parser.add_argument("--label", default="B_CANONICAL_STANDARD_SHOGI")
    parser.add_argument("--validation-count", type=int, default=8)
    parser.add_argument("--search-nodes", type=int, default=128)
    parser.add_argument("--arena-pairs", type=int, default=2)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    output = run(args.model_json, args.label, args.validation_count, args.search_nodes, args.arena_pairs)
    (OUT / "f58_native_results.json").write_text(json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
