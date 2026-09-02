"""H48C: resolve F48 corpus seeds using position identity only.

This script intentionally has no evaluator/search/learning imports.  It is a
pre-learning corpus resolver and does not assign an F48 scientific result.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.learning.openings import ArenaOpeningCorpus, generate_arena_openings
from generic_chess.learning.serialization import canonical_json, stable_sha256
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset

try:
    from .f48_protocol import (
        H48B_SELECTED_FINGERPRINT,
        ROOT,
        RULESET_FINGERPRINTS,
        atomic_write_json,
        guard_corpus_identities,
        verify_authority,
    )
except ImportError:
    from f48_protocol import (
        H48B_SELECTED_FINGERPRINT,
        ROOT,
        RULESET_FINGERPRINTS,
        atomic_write_json,
        guard_corpus_identities,
        verify_authority,
    )


OUT = ROOT / "tests" / "fixtures" / "h48c_corpus_disjointness_resolution.json"
COLLISION_OUT = ROOT / "tests" / "fixtures" / "h48c_corpus_disjointness_collision_keys.json"
PARENT_SHA = "d829f14e4c7c939bb1c2e06bc8b7d2b6f4b9e510"
TRAINING_SEED = 480700
HOLDOUT_START, HOLDOUT_END = 480701, 490700
ARENA_START, ARENA_END = 480702, 490701
IDENTITY_AUTHORITY = "generic_chess.core.identity.position_identity_key"


def _rulesets():
    western = compile_ruleset_for_execution(build_western_chess_ruleset())._legacy_compiled
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())._legacy_compiled
    generated = generate_game(GeneratorConfig(seed=20260807009, board_size=6, setup_preset="free_random")).compiled_ruleset
    values = [("A_CANONICAL_WESTERN_CHESS", western), ("B_CANONICAL_STANDARD_SHOGI", shogi), ("C_H48B_SELECTED_GENERATED", generated)]
    for name, compiled in values:
        if compiled.ruleset_fingerprint != RULESET_FINGERPRINTS[name]:
            raise RuntimeError(f"{name} fingerprint drift")
    return values


def _identity_hash(values):
    return stable_sha256(sorted(str(value) for value in values))


def _intersection_hash(values):
    return stable_sha256(sorted(values))


def _canonical_action_key(action):
    return canonical_json(action_to_dict(action))


def _diagnostic_corpus(compiled, openings, *, count, seed, min_plies=2, max_plies=6):
    """Generate the fixed corpus using Core legal actions and identity only."""
    openings.validate(compiled)
    base_rng = random.Random(seed)
    candidates = list(openings.openings)
    positions = []
    index = 0
    while len(positions) < count:
        opening = candidates[index % len(candidates)]
        attempt = 0
        generated = None
        while attempt < 50:
            target = base_rng.randint(min_plies, max_plies)
            pos_seed = seed * 10_000 + index * 100 + attempt
            rng = random.Random(pos_seed)
            session = GameSession(compiled)
            for action in opening.actions:
                session.submit(action)
            history = list(opening.actions)
            ok = True
            while len(history) < target:
                legal = session.legal_actions()
                if not legal or session.result.status.value != "ongoing":
                    ok = False
                    break
                ordered = sorted(legal, key=_canonical_action_key)
                action = ordered[rng.randrange(len(ordered))]
                session.submit(action)
                history.append(action)
            if ok and session.result.status.value == "ongoing":
                key = str(position_identity_key(session.state.position, compiled))
                generated = {
                    "index": index,
                    "action_history": [action_to_dict(action) for action in history],
                    "position_key": key,
                    "side_to_move": session.state.position.side_to_move,
                    "ply": session.state.ply_count,
                }
                break
            attempt += 1
        if generated is None:
            raise RuntimeError(f"could not generate H48C position {index}")
        positions.append(generated)
        index += 1
    corpus = {
        "schema_version": 1,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "source_opening_corpus_id": openings.corpus_id,
        "seed": seed,
        "positions": positions,
    }
    return {"corpus": corpus, "corpus_id": stable_sha256(corpus), "identities": {p["position_key"] for p in positions}}


def _opening_identity_set(compiled, openings):
    openings.validate(compiled)
    identities = set()
    for opening in openings.openings:
        session = GameSession(compiled)
        for action in opening.actions:
            session.submit(action)
        identities.add(str(position_identity_key(session.state.position, compiled)))
    return identities


def _training(compiled):
    openings = generate_arena_openings(compiled, count=16, seed=TRAINING_SEED, min_plies=2, max_plies=6)
    corpus = _diagnostic_corpus(compiled, openings, count=64, seed=TRAINING_SEED, min_plies=2, max_plies=6)
    return {"opening": openings, "corpus": corpus, "identities": corpus["identities"]}


def _holdout(compiled, seed):
    openings = generate_arena_openings(compiled, count=16, seed=seed, min_plies=2, max_plies=6)
    corpus = _diagnostic_corpus(compiled, openings, count=64, seed=seed, min_plies=2, max_plies=6)
    return {"opening": openings, "corpus": corpus, "identities": corpus["identities"]}


def _arena(compiled, seed):
    openings = generate_arena_openings(compiled, count=16, seed=seed, min_plies=2, max_plies=6)
    return {"opening": openings, "identities": _opening_identity_set(compiled, openings)}


def _attempt_row(seed, rulesets, kind, fixed):
    rows = []
    all_pass = True
    for ruleset_id, compiled in rulesets:
        if kind == "holdout":
            candidate = _holdout(compiled, seed)
            left_name, right_name = "training", "holdout"
            left, right = fixed[ruleset_id]["training"]["identities"], candidate["identities"]
        else:
            candidate = _arena(compiled, seed)
            left_name, right_name = "training", "arena"
            left, right = fixed[ruleset_id]["training"]["identities"], candidate["identities"]
            holdout = fixed[ruleset_id]["holdout"]["identities"]
        shared = sorted(left & right)
        collisions = {f"{left_name}_{right_name}": shared}
        if kind == "arena":
            shared_holdout = sorted(holdout & right)
            collisions["holdout_arena"] = shared_holdout
        passed = all(not values for values in collisions.values())
        all_pass = all_pass and passed
        rows.append({"ruleset_id": ruleset_id, "seed": seed, "corpus_id": candidate["corpus"]["corpus_id"] if kind == "holdout" else candidate["opening"].corpus_id, "identity_set_count": len(candidate["identities"]), "identity_set_hash": _identity_hash(candidate["identities"]), "intersection_counts": {name: len(values) for name, values in collisions.items()}, "intersection_key_hashes": {name: _intersection_hash(values) for name, values in collisions.items()}, "intersection_keys": collisions, "pass": passed})
    return {"seed": seed, "kind": kind, "rulesets": rows, "pass": all_pass}


def _direct_first(rows):
    passing = [row["seed"] for row in rows if row["pass"]]
    return min(passing) if passing else None


def _reconstruct_final(rulesets, holdout_seed, arena_seed):
    final = {}
    for ruleset_id, compiled in rulesets:
        training = _training(compiled)
        holdout = _holdout(compiled, holdout_seed)
        arena = _arena(compiled, arena_seed)
        final[ruleset_id] = {"training": {"corpus_id": training["corpus"]["corpus_id"], "identity_set_hash": _identity_hash(training["identities"]), "identity_set_count": len(training["identities"])}, "holdout": {"corpus_id": holdout["corpus"]["corpus_id"], "identity_set_hash": _identity_hash(holdout["identities"]), "identity_set_count": len(holdout["identities"])}, "arena": {"corpus_id": arena["opening"].corpus_id, "identity_set_hash": _identity_hash(arena["identities"]), "identity_set_count": len(arena["identities"])} , "pairwise_intersections": {"training_holdout": [], "training_arena": [], "holdout_arena": []}}
    return final


def resolve():
    verify_authority()
    rulesets = _rulesets()
    fixed = {ruleset_id: {"training": _training(compiled)} for ruleset_id, compiled in rulesets}
    holdout_attempts = []
    for seed in range(HOLDOUT_START, HOLDOUT_END + 1):
        for ruleset_id, compiled in rulesets:
            fixed[ruleset_id]["holdout"] = _holdout(compiled, seed)
        row = _attempt_row(seed, rulesets, "holdout", fixed)
        holdout_attempts.append(row)
        if row["pass"]:
            break
    else:
        return {"kind": "H48C_CORPUS_DISJOINTNESS_RESOLUTION", "status": "F48_CORPUS_DISJOINTNESS_UNRESOLVED", "parent_h48r3a_sha": PARENT_SHA}
    selected_holdout = holdout_attempts[-1]["seed"]
    arena_attempts = []
    for seed in range(ARENA_START, ARENA_END + 1):
        if seed == selected_holdout:
            continue
        row = _attempt_row(seed, rulesets, "arena", fixed)
        arena_attempts.append(row)
        if row["pass"]:
            break
    else:
        return {"kind": "H48C_CORPUS_DISJOINTNESS_RESOLUTION", "status": "F48_CORPUS_DISJOINTNESS_UNRESOLVED", "parent_h48r3a_sha": PARENT_SHA}
    selected_arena = arena_attempts[-1]["seed"]
    direct_holdout = _direct_first(holdout_attempts)
    direct_arena = _direct_first(arena_attempts)
    if (direct_holdout, direct_arena) != (selected_holdout, selected_arena):
        raise RuntimeError("sequential/direct H48C minimality disagreement")
    final_a = _reconstruct_final(rulesets, selected_holdout, selected_arena)
    final_b = _reconstruct_final(rulesets, selected_holdout, selected_arena)
    if final_a != final_b:
        raise RuntimeError("H48C selected-corpus reconstruction is not deterministic")
    guard_results = {}
    for ruleset_id, compiled in rulesets:
        final_training = _training(compiled)
        final_holdout = _holdout(compiled, selected_holdout)
        final_arena = _arena(compiled, selected_arena)
        guard_results[ruleset_id] = guard_corpus_identities(ruleset_id=ruleset_id, ruleset_fingerprint=compiled.ruleset_fingerprint, identities={"training": final_training["identities"], "holdout": final_holdout["identities"], "arena": final_arena["identities"]}, authority_hash=stable_sha256(RULESET_FINGERPRINTS), config_hash=stable_sha256({"training": TRAINING_SEED, "holdout": selected_holdout, "arena": selected_arena}), input_hash=stable_sha256({"parent": PARENT_SHA, "ruleset": ruleset_id}), proceed=lambda value: value)
    collision_keys = {"holdout": [{"seed": row["seed"], "rulesets": [{"ruleset_id": item["ruleset_id"], "intersection_keys": item["intersection_keys"], "intersection_key_hashes": item["intersection_key_hashes"]} for item in row["rulesets"]]} for row in holdout_attempts if not row["pass"]], "arena": [{"seed": row["seed"], "rulesets": [{"ruleset_id": item["ruleset_id"], "intersection_keys": item["intersection_keys"], "intersection_key_hashes": item["intersection_key_hashes"]} for item in row["rulesets"]]} for row in arena_attempts if not row["pass"]]}
    public_holdout_attempts = [{key: value for key, value in row.items() if key != "_internal"} | {"rulesets": [{key: value for key, value in item.items() if key != "intersection_keys"} for item in row["rulesets"]]} for row in holdout_attempts]
    public_arena_attempts = [{key: value for key, value in row.items() if key != "_internal"} | {"rulesets": [{key: value for key, value in item.items() if key != "intersection_keys"} for item in row["rulesets"]]} for row in arena_attempts]
    payload = {"kind": "H48C_CORPUS_DISJOINTNESS_RESOLUTION", "status": "PASS", "parent_h48r3a_sha": PARENT_SHA, "ruleset_fingerprints": RULESET_FINGERPRINTS, "identity_authority": IDENTITY_AUTHORITY, "original_failed_seed_triple": {"training": TRAINING_SEED, "holdout": 480701, "arena": 480702}, "selected_holdout_seed": selected_holdout, "selected_arena_seed": selected_arena, "resolved_seed_triple": {"training": TRAINING_SEED, "holdout": selected_holdout, "arena": selected_arena}, "holdout_attempts": public_holdout_attempts, "arena_attempts": public_arena_attempts, "final_corpora": final_a, "reconstruction_repeat_equal": True, "minimality": {"sequential_holdout": selected_holdout, "direct_holdout": direct_holdout, "sequential_arena": selected_arena, "direct_arena": direct_arena, "lexicographically_minimal": True}, "runtime_guard": {"pairwise_disjoint": all(value["pairwise_disjoint"] for value in guard_results.values()), "per_ruleset": guard_results}, "collision_auxiliary_path": str(COLLISION_OUT.relative_to(ROOT)), "evaluator_invoked": False, "search_invoked": False, "learner_invoked": False, "selfplay_invoked": False, "arena_games_invoked": False}
    atomic_write_json(COLLISION_OUT, collision_keys)
    payload["collision_auxiliary_sha256"] = stable_sha256(collision_keys)
    atomic_write_json(OUT, payload)
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.parse_args()
    payload = resolve()
    print(canonical_json({"status": payload["status"], "selected_holdout_seed": payload.get("selected_holdout_seed"), "selected_arena_seed": payload.get("selected_arena_seed")}))


if __name__ == "__main__":
    main()
