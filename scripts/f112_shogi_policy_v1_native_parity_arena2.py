"""F112 Shogi Native V1 parity smoke, performance, and Arena2."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

import numpy as np

from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_from_dict
from generic_chess.learning.arena import ArenaConfig, run_arena
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.policy_v1 import SemanticPolicyV1, action_v1_components
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession


CHECKPOINT_ID = "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
POLICY_SHA = "2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--bundle", type=Path, required=True); ap.add_argument("--policy-report", type=Path, required=True); ap.add_argument("--checkpoint", type=Path, required=True); ap.add_argument("--output", type=Path, required=True); args = ap.parse_args()
    report = json.loads(args.policy_report.read_text(encoding="utf-8")); policy = SemanticPolicyV1.from_dict(report["rulesets"]["standard_shogi"]["policy_v1_artifact"])
    if policy.computed_model_sha256 != POLICY_SHA: raise RuntimeError("POLICY_V1_IDENTITY_MISMATCH")
    checkpoint_payload = json.loads(args.checkpoint.read_text(encoding="utf-8")); checkpoint = LearnableMaterialCheckpoint.from_dict(checkpoint_payload.get("checkpoint", checkpoint_payload))
    if checkpoint.checkpoint_id != CHECKPOINT_ID: raise RuntimeError("FROZEN_CHECKPOINT_IDENTITY_MISMATCH")
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset()); native_rules = compile_native_semantic_rules(compiled)
    # Existing F109 positions only: reconstruct histories and measure 24 fresh engines.
    bundle = json.loads(args.bundle.read_text(encoding="utf-8")); rows = bundle["rows"][:24]
    performance = []
    for row in rows:
        session = GameSession(compiled)
        for item in row["history"]: session.submit(action_from_dict(item))
        engine = SemanticSearchEngine(compiled, native_rules, checkpoint=checkpoint, policy=policy, tt_megabytes=8)
        result = engine.search(session, SearchLimits(max_depth=12, max_nodes=2000, quiescence_max_depth=0))
        performance.append({"root_identity": row["root_identity"], "nodes": result.nodes, "completed_depth": result.completed_depth, "policy_nodes": result.policy_nodes, "policy_state_inferences": result.policy_state_inferences, "policy_action_embeddings": result.policy_action_embeddings, "policy_actions_scored": result.policy_actions_scored, "policy_elapsed_seconds": result.policy_elapsed_seconds, "legal_action": result.action is not None})
    probe = performance[0]
    if any(not row["legal_action"] or row["policy_state_inferences"] != row["policy_nodes"] or row["policy_action_embeddings"] != row["policy_actions_scored"] for row in performance): raise RuntimeError("SEMANTIC_POLICY_V1_NATIVE_TELEMETRY_FAILED")
    arena_config = ArenaConfig(pairs=2, nodes_per_move=1_000_000, max_depth=12, tt_megabytes=8, opening_seed=1110801, opening_count=2, min_plies=2, max_plies=6, workers=1, move_time_seconds=1.0, root_window_pruning=True)
    arena = run_arena(compiled, native_rules, checkpoint, checkpoint, arena_config, policy=policy)
    output = {"work_order_id": "GENERICCHESS_F112_SHOGI_POLICY_V1_NATIVE_PARITY_EQUAL_WALLCLOCK_ARENA2", "frozen_checkpoint_id": checkpoint.checkpoint_id, "policy_model_sha256": policy.model_sha256, "probe": probe, "performance": performance, "arena_config": asdict(arena_config), "arena": {"pair_scores": list(arena.pair_scores), "mean_pair_score": arena.mean_pair_score, "child_better_pairs": arena.child_better_pairs, "tied_pairs": arena.tied_pairs, "child_worse_pairs": arena.child_worse_pairs, "game_wins": arena.game_wins, "game_draws": arena.game_draws, "game_losses": arena.game_losses}, "classification": "SHOGI_POLICY_V1_ACTION_ENCODER_ARENA2_SURVIVES" if arena.mean_pair_score > 0.5 and arena.child_better_pairs > arena.child_worse_pairs else "SHOGI_POLICY_V1_ACTION_ENCODER_ARENA2_REJECTED"}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(output, sort_keys=True), encoding="utf-8"); print(json.dumps({"classification": output["classification"], "mean_pair_score": arena.mean_pair_score}, sort_keys=True))


if __name__ == "__main__": main()
