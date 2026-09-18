"""Frozen-data F111 Action Encoder-v1 offline gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from generic_chess.core.actions import action_from_dict
from generic_chess.learning.policy import SemanticPolicyV0, policy_target_from_q
from generic_chess.learning.policy_v1 import action_v1_components, fit_semantic_policy_v1
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


WORK_ORDER_ID = "GENERICCHESS_F111_SEMANTIC_POLICY_V1_ACTION_ENCODER_ARENA2"
SEEDS = {"western_chess": 1090111, "standard_shogi": 1090211}
CHECKPOINT_IDS = {"western_chess": "55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e", "standard_shogi": "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"}


def _prob(logits):
    value = np.exp(logits - np.max(logits)); return value / np.sum(value)


def _metrics(policy, roots, version):
    rows = []
    for split, root in roots:
        if version == "v0":
            logits = policy.logits(root["state"], root["v0_actions"])
        else:
            logits = policy.logits(root["state"], root["base_actions"], root["categories"])
        probs = _prob(logits); target = root["target"]; q = root["q"]
        pair_total = pair_correct = 0
        for left in range(len(q)):
            for right in range(left + 1, len(q)):
                if q[left] == q[right]: continue
                pair_total += 1; pair_correct += int((q[left] - q[right]) * (logits[left] - logits[right]) > 0)
        rows.append({"split": split, "cross_entropy": float(-np.sum(target * np.log(np.maximum(probs, 1e-300)))), "kl": float(np.sum(target * np.log(np.maximum(target, 1e-300) / np.maximum(probs, 1e-300)))), "top1": float(np.argmax(probs) == np.argmax(q)), "pairwise": pair_correct / pair_total if pair_total else 1.0, "regret": float(np.max(q) - q[int(np.argmax(probs))]), "entropy": float(-np.sum(probs * np.log(np.maximum(probs, 1e-300)))), "max_probability": float(np.max(probs)), "logit_std": float(np.std(logits))})
    result = {}
    for split in ("train", "dev", "holdout"):
        selected = [row for row in rows if row["split"] == split]
        result[split] = {key: float(np.mean([row[key] for row in selected])) for key in rows[0] if key != "split"} if selected else None
    return result


def _load(name, path):
    bundle = json.loads(path.read_text(encoding="utf-8"))
    v0 = SemanticPolicyV0.from_dict(bundle["policy_artifact"])
    if bundle["frozen_checkpoint_id"] != CHECKPOINT_IDS[name]: raise AssertionError("checkpoint identity mismatch")
    builder = build_western_chess_ruleset if name == "western_chess" else build_standard_shogi_ruleset
    compiled = compile_semantic_ruleset(builder()); native_rules = compile_native_semantic_rules(compiled)
    type_count = len(tuple(sorted(getattr(compiled.support, "type_metadata", {}))))
    roots = []
    for row in bundle["rows"]:
        q = np.asarray(row["q_values"], dtype=np.float64)
        corrected = policy_target_from_q(q, epsilon=1.0)
        if not np.allclose(corrected, np.asarray(row["target"], dtype=np.float64), atol=1e-12, rtol=0):
            raise RuntimeError("POLICY_V1_FROZEN_TARGET_IDENTITY_MISMATCH")
        session = GameSession(compiled)
        for item in row["history"]: session.submit(action_from_dict(item))
        actions = tuple(sorted(session.legal_actions(), key=lambda action: int(pack_semantic_action(native_rules, session.state.position, action))))
        v0_actions = np.asarray(row["action_features"], dtype=np.float64)
        reconstructed = np.asarray([__import__("generic_chess.learning.policy", fromlist=["semantic_action_features"]).semantic_action_features(compiled, session.state.position, action) for action in actions])
        if reconstructed.shape != v0_actions.shape or not np.array_equal(reconstructed, v0_actions): raise RuntimeError("F111_ACTION_RECONSTRUCTION_MISMATCH")
        components = [action_v1_components(compiled, session.state.position, action) for action in actions]
        base = np.asarray([item[0] for item in components], dtype=np.float64)
        cats = tuple(np.asarray([item[1][axis] for item in components], dtype=np.int64) for axis in range(4))
        roots.append((row["split"], {"root_identity": row["root_identity"], "state": np.asarray(row["state_features"], dtype=np.float64), "v0_actions": v0_actions, "base_actions": base, "categories": cats, "target": np.asarray(row["target"], dtype=np.float64), "q": q}))
    train = [root for split, root in roots if split == "train"]
    examples = [(root["state"], root["base_actions"], root["categories"], root["target"]) for root in train]
    v1 = fit_semantic_policy_v1(examples, ruleset_fingerprint=compiled.ruleset_fingerprint, corpus_config=v0.corpus_config, seed=SEEDS[name], type_count=type_count)
    restored = type(v1).from_dict(v1.to_dict())
    identity = restored.computed_model_sha256 == v1.to_dict()["model_sha256"]
    metrics_v0 = _metrics(v0, roots, "v0"); metrics_v1 = _metrics(restored, roots, "v1")
    oracle = {"top1": {"western_chess": 0.5357142857142857, "standard_shogi": 0.13333333333333333}[name], "pairwise": {"western_chess": 0.6985522686051251, "standard_shogi": 0.7247439352698473}[name]}
    gate = all(metrics_v1["train"][key] < metrics_v0["train"][key] for key in ("cross_entropy", "kl", "regret")) and metrics_v1["train"]["top1"] > oracle["top1"] and metrics_v1["train"]["pairwise"] > oracle["pairwise"] and all(np.isfinite(value) for split in metrics_v1.values() if split for value in split.values())
    return {"ruleset": name, "frozen_checkpoint_id": bundle["frozen_checkpoint_id"], "policy_v0_model_sha256": v0.model_sha256, "policy_v1_model_sha256": v1.to_dict()["model_sha256"], "policy_v1_reload_identity": identity, "target_identity_corrected_scale": True, "root_counts": {split: sum(item[0] == split for item in roots) for split in ("train", "dev", "holdout")}, "policy_v0": metrics_v0, "policy_v1": metrics_v1, "f110_linear_oracle": oracle, "offline_gate_pass": gate, "roots": [{"split": split, "root_identity": root["root_identity"]} for split, root in roots], "policy_v1_artifact": v1.to_dict()}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--chess-bundle", type=Path, required=True); parser.add_argument("--shogi-bundle", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    results = {"western_chess": _load("western_chess", args.chess_bundle), "standard_shogi": _load("standard_shogi", args.shogi_bundle)}
    overall = all(result["offline_gate_pass"] for result in results.values())
    report = {"work_order_id": WORK_ORDER_ID, "new_search_performed": False, "new_arena_performed": False, "new_policy_states_performed": False, "rulesets": results, "offline_gate_all_rulesets": overall, "arena_authorized_rulesets": [name for name, result in results.items() if result["offline_gate_pass"]], "status": "CONTINUE", "candidate_sha": "NONE", "promotion": "HOLD"}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
    print(json.dumps({"work_order_id": WORK_ORDER_ID, "offline_gate_all_rulesets": overall, "arena_authorized_rulesets": report["arena_authorized_rulesets"]}, sort_keys=True))


if __name__ == "__main__": main()
