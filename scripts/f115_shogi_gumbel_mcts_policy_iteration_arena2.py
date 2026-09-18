"""F115 bounded generic Gumbel-MCTS policy iteration and Shogi Arena2."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
import re
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.learning.gumbel_mcts import (
    SemanticGumbelMCTSV0,
    UnsupportedNeutralDeclaration,
)
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.policy import semantic_state_feature_vector
from generic_chess.learning.policy_v1 import SemanticPolicyV1, action_v1_components
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.native.semantic import (
    dynamic_features,
    policy_logits,
    public_action,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


FROZEN_CHECKPOINT_ID = "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
PARENT_POLICY_SHA = "2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955"


def _load_inputs(checkpoint_path: Path, policy_report: Path):
    checkpoint_payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint = LearnableMaterialCheckpoint.from_dict(
        checkpoint_payload.get("checkpoint", checkpoint_payload)
    )
    if checkpoint.checkpoint_id != FROZEN_CHECKPOINT_ID:
        raise RuntimeError("FROZEN_CHECKPOINT_IDENTITY_MISMATCH")
    report = json.loads(policy_report.read_text(encoding="utf-8"))
    parent = SemanticPolicyV1.from_dict(
        report["rulesets"]["standard_shogi"]["policy_v1_artifact"]
    )
    if parent.computed_model_sha256 != PARENT_POLICY_SHA:
        raise RuntimeError("PARENT_POLICY_IDENTITY_MISMATCH")
    return checkpoint, parent


def _context(ruleset):
    compiled = compile_semantic_ruleset(ruleset)
    return compiled, compile_native_semantic_rules(compiled)


def _sorted_legal(session):
    return sorted(
        session.legal_actions(),
        key=lambda action: json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":")),
    )


def _policy_python_logits(compiled, native_rules, policy, session, raw_actions):
    position = session.state.position
    packed = pack_semantic_search_position(compiled, native_rules, session)
    state = semantic_state_feature_vector(
        position, compiled, dynamic_features(native_rules, packed)
    )
    actions = [public_action(native_rules, raw) for raw in raw_actions]
    bases = []
    categories = []
    for action in actions:
        base, category = action_v1_components(compiled, position, action)
        bases.append(base)
        categories.append(category)
    category_arrays = tuple(
        np.asarray([category[index] for category in categories], dtype=np.int64)
        for index in range(4)
    )
    return policy.logits(state, np.asarray(bases), category_arrays), position


def _policy_parity(compiled, native_rules, policy, count=100):
    session = GameSession(compiled)
    rows = []
    for _ in range(count):
        packed = pack_semantic_search_position(compiled, native_rules, session)
        native = policy_logits(native_rules, packed, policy)
        raw_actions = tuple(native["actions"])
        python_logits, position = _policy_python_logits(
            compiled, native_rules, policy, session, raw_actions
        )
        if raw_actions != tuple(
            pack_semantic_action(native_rules, position, public_action(native_rules, raw))
            for raw in raw_actions
        ):
            raise RuntimeError("GUMBEL_MCTS_POLICY_ORDER_PARITY_FAILED")
        max_error = max(
            (abs(float(a) - float(b)) for a, b in zip(native["logits"], python_logits)),
            default=0.0,
        )
        if max_error > 1e-9:
            raise RuntimeError("GUMBEL_MCTS_POLICY_LOGIT_PARITY_FAILED")
        rows.append({
            "position_identity": position_identity_key(position, compiled),
            "action_count": len(raw_actions),
            "max_abs_logit_error": max_error,
        })
        legal = _sorted_legal(session)
        if not legal:
            session = GameSession(compiled)
        else:
            session.submit(legal[0])
            if session.result.status.value != "ongoing":
                session = GameSession(compiled)
    return {"positions": len(rows), "max_abs_logit_error": max(r["max_abs_logit_error"] for r in rows), "rows": rows}


def _genericity_smokes():
    # These are deliberately uniform-prior searches: the backend must work
    # without a game-name branch or a Policy-v1 artifact.
    contexts = [
        ("standard_shogi", build_standard_shogi_ruleset()),
        ("western_chess", build_western_chess_ruleset()),
    ]
    # The lowered semantic Shogi builder is an existing generated semantic
    # ruleset and exercises the generic DSL path independently of the catalog.
    from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset
    contexts.append(("generated_semantic_shogi", build_semantic_shogi_ruleset()))
    result = []
    for name, ruleset in contexts:
        compiled, native_rules = _context(ruleset)
        smoke = SemanticGumbelMCTSV0(
            compiled, native_rules, simulations=16, policy=None
        ).search(GameSession(compiled), search_seed=1150000 + len(result))
        if smoke.action not in smoke.root_actions or sum(smoke.root_visits) != 16:
            raise RuntimeError("GUMBEL_MCTS_GENERICITY_SMOKE_FAILED")
        result.append({"ruleset": name, "actions": len(smoke.root_actions), "simulations": smoke.simulations, "expanded_nodes": smoke.expanded_nodes})
    return result


def _root_record(compiled, session, result, game, ply, split):
    return {
        "split": split,
        "game": game,
        "ply": ply,
        "position_identity": result.root_position_key,
        "side_to_move": int(session.state.position.side_to_move),
        "history": [action_to_dict(item.action) for item in session.history],
        "actions": list(result.root_actions),
        "logits": list(result.root_logits),
        "priors": list(result.root_priors),
        "gumbels": list(result.root_gumbels),
        "visits": list(result.root_visits),
        "q_values": list(result.root_q_values),
        "target_policy": list(result.target_policy),
        "selected_action": result.action,
        "simulations": result.simulations,
        "expanded_nodes": result.expanded_nodes,
        "leaf_evaluations": result.leaf_evaluations,
        "maximum_tree_depth": result.maximum_tree_depth,
        "declaration_encounters": result.declaration_encounters,
        "wall_seconds": result.wall_seconds,
        "legal_action_count": len(session.legal_actions()),
    }


def _selfplay(compiled, native_rules, checkpoint, parent):
    rows = []
    games = []
    for game in range(5):
        session = GameSession(compiled)
        game_rows = []
        for ply in range(64):
            if session.result.status.value != "ongoing":
                break
            result = SemanticGumbelMCTSV0(
                compiled, native_rules, checkpoint=checkpoint, policy=parent
            ).search(session, search_seed=1150101 + 10000 * game + ply)
            split = "train" if game < 3 else ("dev" if game == 3 else "holdout")
            game_rows.append(_root_record(compiled, session, result, game, ply, split))
            if result.declaration_id is not None:
                session.declare(result.declaration_id)
                break
            if result.action is None or result.action not in result.root_actions:
                raise RuntimeError("GUMBEL_MCTS_SELFPLAY_INVALID_ACTION")
            action = public_action(native_rules, result.action)
            session.submit(action)
        rows.extend(game_rows)
        games.append({"game": game, "plies": len(game_rows), "status": session.result.status.value, "winner": session.result.winner})
    informative = [row for row in rows if len(row["actions"]) > 1]
    counts = {split: sum(row["split"] == split for row in informative) for split in ("train", "dev", "holdout")}
    if counts["train"] < 80 or counts["dev"] < 20 or counts["holdout"] < 20:
        raise RuntimeError("GUMBEL_MCTS_POLICY_CORPUS_INSUFFICIENT")
    return rows, games, counts


def _examples(rows, compiled, native_rules):
    # Root tensors are rebuilt from the persisted identities; this also proves
    # the artifact contains enough information for an offline update.
    examples = {"train": [], "dev": [], "holdout": []}
    for row in rows:
        if len(row["actions"]) <= 1:
            continue
        session = GameSession(compiled)
        from generic_chess.core.actions import action_from_dict
        for payload in row["history"]:
            session.submit(action_from_dict(payload))
        packed = pack_semantic_search_position(compiled, native_rules, session)
        state = semantic_state_feature_vector(session.state.position, compiled, dynamic_features(native_rules, packed))
        public = [public_action(native_rules, raw) for raw in row["actions"]]
        parts = [action_v1_components(compiled, session.state.position, action) for action in public]
        bases = np.asarray([item[0] for item in parts], dtype=np.float64)
        cats = tuple(np.asarray([item[1][index] for item in parts], dtype=np.int64) for index in range(4))
        examples[row["split"]].append((state, bases, cats, np.asarray(row["target_policy"], dtype=np.float64)))
    return examples


def _forward(params, state, bases, cats):
    h = np.tanh(params[0] @ state + params[1])
    actor, promo, drop, geometry = cats
    z = bases @ params[2].T + params[3] + params[4][actor] + params[5][promo] + params[6][drop] + params[7][actor, geometry]
    z += bases[:, 18:19] * params[8][actor] + bases[:, 17:18] * params[9][actor] + bases[:, 1:2] * params[10][actor]
    embedding = np.tanh(z)
    logits = embedding @ h + bases @ params[11] + params[12][actor] + params[13][promo] + params[14][drop] + params[15][actor, geometry] + bases[:, 18] * params[16][actor] + bases[:, 17] * params[17][actor] + bases[:, 1] * params[18][actor]
    return h, embedding, logits


def _loss(params, examples):
    total = 0.0
    count = 0
    for state, bases, cats, target in examples:
        _, _, logits = _forward(params, state, bases, cats)
        shifted = logits - np.max(logits)
        probs = np.exp(shifted); probs /= np.sum(probs)
        total += float(-np.sum(target * np.log(np.maximum(probs, 1e-300))))
        count += 1
    return total / max(count, 1)


def _train(parent, examples, *, steps=100, learning_rate=0.001, proximal=0.001, seed=1150111):
    params = [value.copy() for value in parent._arrays()]
    anchor = [value.copy() for value in params]
    moments = [(np.zeros_like(value), np.zeros_like(value)) for value in params]
    count = len(examples)
    for step in range(1, steps + 1):
        gradients = [np.zeros_like(value) for value in params]
        for state, bases, cats, target in examples:
            h, embedding, logits = _forward(params, state, bases, cats)
            shifted = logits - np.max(logits); probs = np.exp(shifted); probs /= np.sum(probs)
            dlogits = (probs - target) / count
            actor, promo, drop, geometry = cats
            gradients[11] += bases.T @ dlogits
            gradients[12] += np.bincount(actor, dlogits, minlength=params[12].shape[0])
            gradients[13] += np.bincount(promo, dlogits, minlength=params[13].shape[0])
            gradients[14] += np.bincount(drop, dlogits, minlength=params[14].shape[0])
            for index, value in enumerate(dlogits):
                gradients[15][actor[index], geometry[index]] += value
                gradients[16][actor[index]] += value * bases[index, 18]
                gradients[17][actor[index]] += value * bases[index, 17]
                gradients[18][actor[index]] += value * bases[index, 1]
            d_embedding = dlogits[:, None] * h[None, :]
            d_z = d_embedding * (1.0 - embedding * embedding)
            gradients[2] += d_z.T @ bases; gradients[3] += np.sum(d_z, axis=0)
            gradients[4][actor] += d_z; gradients[5][promo] += d_z; gradients[6][drop] += d_z
            for index in range(len(dlogits)):
                gradients[7][actor[index], geometry[index]] += d_z[index]
                gradients[8][actor[index]] += d_z[index] * bases[index, 18]
                gradients[9][actor[index]] += d_z[index] * bases[index, 17]
                gradients[10][actor[index]] += d_z[index] * bases[index, 1]
            d_h = np.sum(dlogits[:, None] * embedding, axis=0); d_state = d_h * (1.0 - h * h)
            gradients[0] += np.outer(d_state, state); gradients[1] += d_state
        for index, (param, gradient) in enumerate(zip(params, gradients)):
            gradient += proximal * (param - anchor[index])
            first, second = moments[index]
            first[...] = 0.9 * first + 0.1 * gradient; second[...] = 0.999 * second + 0.001 * gradient * gradient
            param[...] -= learning_rate * (first / (1 - 0.9 ** step)) / (np.sqrt(second / (1 - 0.999 ** step)) + 1e-8)
    return params


def _policy_from_params(parent, params):
    names = ("state_weights", "state_bias", "base_weights", "action_bias", "actor_embedding", "promotion_embedding", "drop_embedding", "actor_geometry_embedding", "actor_capture_embedding", "actor_promotion_embedding", "actor_drop_embedding", "beta_base", "beta_actor", "beta_promotion", "beta_drop", "beta_actor_geometry", "beta_actor_capture", "beta_actor_promotion", "beta_actor_drop")
    values = {}
    def tree(value):
        return tuple(tree(item) for item in value) if getattr(value, "ndim", 0) > 1 else tuple(float(item) for item in value)
    for name, value in zip(names, params):
        values[name] = tree(value)
    return replace(parent, **values, model_sha256="")


def _metrics(policy, examples):
    losses = []; kls = []; top = 0; target_entropy = []; policy_entropy = []
    for state, bases, cats, target in examples:
        _, _, logits = _forward(policy._arrays(), state, bases, cats)
        shifted = logits - np.max(logits); probs = np.exp(shifted); probs /= np.sum(probs)
        entropy = -float(np.sum(target * np.log(np.maximum(target, 1e-300))))
        ce = -float(np.sum(target * np.log(np.maximum(probs, 1e-300))))
        losses.append(ce); kls.append(ce - entropy); target_entropy.append(entropy); policy_entropy.append(-float(np.sum(probs * np.log(np.maximum(probs, 1e-300)))))
        top += int(int(np.argmax(logits)) == int(np.argmax(target)))
    return {"cross_entropy": float(np.mean(losses)), "kl_target_policy": float(np.mean(kls)), "top1_target_agreement": top / len(examples), "target_entropy": float(np.mean(target_entropy)), "policy_entropy": float(np.mean(policy_entropy))}


def _interpolate(parent, trained, alpha):
    return _policy_from_params(parent, [a + alpha * (b - a) for a, b in zip(parent._arrays(), trained._arrays())])


def _consistency(compiled, native_rules, checkpoint, parent, child, rows):
    selected = [row for row in rows if row["split"] == "holdout"][:24]
    out = []
    for index, row in enumerate(selected):
        from generic_chess.core.actions import action_from_dict
        session = GameSession(compiled)
        for payload in row["history"]: session.submit(action_from_dict(payload))
        a = SemanticGumbelMCTSV0(compiled, native_rules, checkpoint=checkpoint, policy=parent).search(session, search_seed=1150201 + index)
        b = SemanticGumbelMCTSV0(compiled, native_rules, checkpoint=checkpoint, policy=child).search(session, search_seed=1150201 + index)
        pa = np.asarray(a.target_policy); pb = np.asarray(b.target_policy)
        kl = float(np.sum(pa * np.log(np.maximum(pa, 1e-300) / np.maximum(pb, 1e-300))))
        out.append({"position_identity": row["position_identity"], "action_agreement": a.action == b.action, "target_kl": kl, "mean_abs_q_difference": float(np.mean(np.abs(np.asarray(a.root_q_values) - np.asarray(b.root_q_values)))), "parent_wall_seconds": a.wall_seconds, "child_wall_seconds": b.wall_seconds, "parent_expanded_nodes": a.expanded_nodes, "child_expanded_nodes": b.expanded_nodes, "parent_max_depth": a.maximum_tree_depth, "child_max_depth": b.maximum_tree_depth})
    return {"count": len(out), "action_agreement_rate": float(np.mean([row["action_agreement"] for row in out])), "mean_target_kl": float(np.mean([row["target_kl"] for row in out])), "rows": out}


def _arena(compiled, native_rules, checkpoint, parent, child, excluded):
    corpus = generate_arena_openings(compiled, count=2, seed=1150801, min_plies=2, max_plies=6)
    corpus.validate(compiled)
    if any(opening.final_position_key in excluded for opening in corpus.openings):
        raise RuntimeError("GUMBEL_MCTS_ARENA_OPENING_OVERLAP")
    games = []
    for game in range(4):
        opening = corpus.openings[game // 2]
        child_owner = game % 2
        session = GameSession(compiled)
        for action in opening.actions: session.submit(action)
        metrics = []; declarations = 0
        for ply in range(256):
            if session.result.status.value != "ongoing": break
            side = int(session.state.position.side_to_move)
            policy = child if side == child_owner else parent
            started = time.perf_counter()
            result = SemanticGumbelMCTSV0(compiled, native_rules, checkpoint=checkpoint, policy=policy).search(session, search_seed=1150901 + 10000 * game + ply)
            metrics.append({"simulations": result.simulations, "expanded_nodes": result.expanded_nodes, "leaf_evaluations": result.leaf_evaluations, "maximum_tree_depth": result.maximum_tree_depth, "wall_seconds": time.perf_counter() - started, "declaration_encounters": result.declaration_encounters})
            if result.declaration_id is not None:
                session.declare(result.declaration_id); declarations += 1; break
            if result.action is None: raise RuntimeError("GUMBEL_MCTS_ARENA_NO_ACTION")
            session.submit(public_action(native_rules, result.action))
        valid = session.result.status.value != "ongoing" and all(row["simulations"] == 64 for row in metrics)
        games.append({"game": game, "opening": opening.index, "child_owner": child_owner, "valid": valid, "status": session.result.status.value, "winner": session.result.winner, "plies": len(metrics), "declarations": declarations, "metrics": metrics})
    valid_games = [row for row in games if row["valid"]]
    if len(valid_games) != 4:
        return {"corpus": corpus.to_dict(), "games": games, "valid_game_count": len(valid_games), "pair_scores": [], "mean_pair_score": None, "child_better_pairs": 0, "child_worse_pairs": 0, "classification": "SHOGI_GUMBEL_MCTS_POLICY_ITERATION_ARENA2_REJECTED"}
    pair_scores = []
    for pair in range(2):
        scores = []
        for row in games[2 * pair:2 * pair + 2]:
            scores.append(0.5 if row["winner"] is None else float(row["winner"] == row["child_owner"]))
        pair_scores.append(float(np.mean(scores)))
    mean = float(np.mean(pair_scores))
    better = sum(score > 0.5 for score in pair_scores); worse = sum(score < 0.5 for score in pair_scores)
    return {"corpus": corpus.to_dict(), "games": games, "pair_scores": pair_scores, "mean_pair_score": mean, "child_better_pairs": better, "child_worse_pairs": worse, "classification": "SHOGI_GUMBEL_MCTS_POLICY_ITERATION_ARENA2_SURVIVES" if mean > 0.5 and better > worse else "SHOGI_GUMBEL_MCTS_POLICY_ITERATION_ARENA2_REJECTED"}


def _known_identities():
    pattern = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
    names = ("f62", "f75", "f77", "f78", "f79", "f80", "f81", "f107", "f108", "f112", "f113", "f114")
    found = set()
    for path in ROOT.rglob("*"):
        if not path.is_file() or not any(part.lower().startswith(name) for part in path.parts for name in names):
            continue
        try:
            found.update(pattern.findall(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            pass
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--policy-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-policy", type=Path, required=True)
    parser.add_argument("--arena-only", action="store_true")
    parser.add_argument("--skip-arena", action="store_true")
    args = parser.parse_args()
    checkpoint, parent = _load_inputs(args.checkpoint, args.policy_report)
    compiled, native_rules = _context(build_standard_shogi_ruleset())
    if args.arena_only:
        child = SemanticPolicyV1.from_dict(json.loads(args.candidate_policy.read_text(encoding="utf-8")))
        arena = _arena(compiled, native_rules, checkpoint, parent, child, _known_identities())
        report = {"work_order_id": "GENERICCHESS_F115_SHOGI_GUMBEL_MCTS_POLICY_ITERATION_ARENA2", "classification": arena["classification"], "frozen_checkpoint_id": checkpoint.checkpoint_id, "parent_policy_sha256": parent.computed_model_sha256, "candidate_policy_sha256": child.computed_model_sha256, "arena": arena}
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"classification": report["classification"], "valid_game_count": arena["valid_game_count"]}, sort_keys=True))
        return
    genericity = _genericity_smokes()
    parity = _policy_parity(compiled, native_rules, parent)
    rows, games, counts = _selfplay(compiled, native_rules, checkpoint, parent)
    examples = _examples(rows, compiled, native_rules)
    parent_metrics = {split: _metrics(parent, examples[split]) for split in examples}
    trained = _policy_from_params(parent, _train(parent, examples["train"]))
    candidate = None
    backtracking = []
    for alpha in (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625, 0.0078125):
        trial = _interpolate(parent, trained, alpha)
        metrics = {split: _metrics(trial, examples[split]) for split in examples}
        finite = all(math.isfinite(value) for row in metrics.values() for value in row.values())
        safe = finite and metrics["train"]["cross_entropy"] < parent_metrics["train"]["cross_entropy"] and metrics["dev"]["cross_entropy"] <= parent_metrics["dev"]["cross_entropy"] and metrics["dev"]["kl_target_policy"] <= parent_metrics["dev"]["kl_target_policy"]
        backtracking.append({"alpha": alpha, "finite": finite, "safe": safe, "metrics": metrics})
        if safe:
            candidate = trial; candidate_metrics = metrics; chosen_alpha = alpha; break
    if candidate is None:
        report = {"work_order_id": "GENERICCHESS_F115_SHOGI_GUMBEL_MCTS_POLICY_ITERATION_ARENA2", "classification": "GUMBEL_MCTS_POLICY_UPDATE_REJECTED_OFFLINE", "frozen_checkpoint_id": checkpoint.checkpoint_id, "parent_policy_sha256": parent.computed_model_sha256, "genericity": genericity, "policy_order_parity": parity, "corpus_counts": counts, "parent_metrics": parent_metrics, "backtracking": backtracking}
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        raise SystemExit(0)
    args.candidate_policy.parent.mkdir(parents=True, exist_ok=True); args.candidate_policy.write_text(json.dumps(candidate.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    reloaded = SemanticPolicyV1.from_dict(json.loads(args.candidate_policy.read_text(encoding="utf-8")))
    if reloaded.computed_model_sha256 != candidate.computed_model_sha256: raise RuntimeError("GUMBEL_MCTS_CANDIDATE_RELOAD_FAILED")
    consistency = _consistency(compiled, native_rules, checkpoint, parent, reloaded, rows)
    if args.skip_arena:
        report = {"work_order_id": "GENERICCHESS_F115_SHOGI_GUMBEL_MCTS_POLICY_ITERATION_ARENA2", "classification": "GUMBEL_MCTS_OFFLINE_POLICY_UPDATE_ACCEPTED_ARENA_PENDING", "frozen_checkpoint_id": checkpoint.checkpoint_id, "parent_policy_sha256": parent.computed_model_sha256, "candidate_policy_sha256": reloaded.computed_model_sha256, "policy_training": {"optimizer": "Adam", "steps": 100, "learning_rate": 0.001, "proximal": 0.001, "seed": 1150111, "chosen_alpha": chosen_alpha, "parent_metrics": parent_metrics, "candidate_metrics": candidate_metrics, "backtracking": backtracking}, "genericity": genericity, "policy_order_parity": parity, "selfplay_games": games, "selfplay_roots": rows, "corpus_counts": counts, "consistency_probe": consistency}
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"classification": report["classification"], "candidate_policy_sha256": reloaded.computed_model_sha256}, sort_keys=True))
        return
    excluded = {row["position_identity"] for row in rows} | _known_identities()
    arena = _arena(compiled, native_rules, checkpoint, parent, reloaded, excluded)
    report = {"work_order_id": "GENERICCHESS_F115_SHOGI_GUMBEL_MCTS_POLICY_ITERATION_ARENA2", "classification": arena["classification"], "frozen_checkpoint_id": checkpoint.checkpoint_id, "parent_policy_sha256": parent.computed_model_sha256, "candidate_policy_sha256": reloaded.computed_model_sha256, "policy_training": {"optimizer": "Adam", "steps": 100, "learning_rate": 0.001, "proximal": 0.001, "seed": 1150111, "chosen_alpha": chosen_alpha, "parent_metrics": parent_metrics, "candidate_metrics": candidate_metrics, "backtracking": backtracking}, "genericity": genericity, "policy_order_parity": parity, "selfplay_games": games, "selfplay_roots": rows, "corpus_counts": counts, "consistency_probe": consistency, "arena": arena}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": report["classification"], "candidate_policy_sha256": reloaded.computed_model_sha256}, sort_keys=True))


if __name__ == "__main__": main()
