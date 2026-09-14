"""R19 trusted-target POINTWISE_Q screen.

This is the R18 state-distribution experiment with the existing F59 target
trust gate restored.  Roots are retained only when q10/q20 agree on the
selected action and ``_ordinary_usable`` accepts the full F59 root metadata.
The learner, target semantics, and playing-strength screen remain fixed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f60_disjoint_policy_objective_validation as f60  # noqa: E402
from scripts import f61_gen0_gen1_strength_triage as gen  # noqa: E402
from scripts import f61_strength_first_triage as f61  # noqa: E402


RULESET = "B_CANONICAL_STANDARD_SHOGI"
TRAINING_SEED = 59013
ARENA_SEED = 620709
FROZEN_OPENING_SEED = 620700
ROOTS_PER_DISTRIBUTION = 12
NODES = 2_000
DEPTH = 12
TT_MB = 8
R18_D1_SEED = 620802
R18_D2_SEED = 620803
D1_SEED = 620812
D2_SEED = 620813
MAX_POOL_ROUNDS = 4
OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "pointwise_trusted_target_screen.json"


def _key(record: dict) -> str:
    return str(record["position_key"])


def _opening_keys(compiled) -> set[str]:
    keys: set[str] = set()
    for seed in range(620700, 620709):
        openings = generate_arena_openings(compiled, count=4, seed=seed, min_plies=2, max_plies=6)
        for opening in openings.openings:
            history = []
            for action in opening.actions:
                history.append(action)
                record = f59._record_from_actions(compiled, history)
                if record is not None:
                    keys.add(_key(record))
    return keys


def _d2_pv_root(compiled, native, parent, base: dict, forbidden: set[str], *, prefix: str):
    root = f59._root_search(compiled, native, parent, base, f60.F60_PV_NODES)
    history = [f59.action_from_dict(item) for item in base["action_history"]]
    for payload in root["pv"]:
        candidate = f59._record_from_actions(compiled, history + [f59.action_from_dict(payload)])
        if candidate is not None and _key(candidate) not in forbidden:
            row = dict(candidate)
            row["source_group"] = f"{prefix}_{base.get('source_group', '')}"
            return row
    return None


def _r18_keys(compiled, native, parent, forbidden: set[str]) -> set[str]:
    """Reconstruct the exact R18 root identity for the disjointness gate."""
    d1_pool, _ = f60._fresh_selfplay(compiled, native, parent, R18_D1_SEED, ROOTS_PER_DISTRIBUTION, smoke=False)
    d1: list[dict] = []
    groups: dict[str, list[dict]] = {}
    for row in d1_pool:
        groups.setdefault(str(row.get("source_group", "")), []).append(row)
    used = set(forbidden)
    for group in sorted(groups):
        row = next((candidate for candidate in groups[group] if _key(candidate) not in used), None)
        if row is not None:
            d1.append(row)
            used.add(_key(row))
        if len(d1) == ROOTS_PER_DISTRIBUTION:
            break
    if len(d1) != ROOTS_PER_DISTRIBUTION:
        raise RuntimeError("unable to reconstruct R18 D1 roots")
    d2_pool, _ = f60._fresh_selfplay(compiled, native, parent, R18_D2_SEED, ROOTS_PER_DISTRIBUTION, smoke=False)
    d2: list[dict] = []
    groups = {}
    for row in d2_pool:
        groups.setdefault(str(row.get("source_group", "")), []).append(row)
    for group in sorted(groups):
        base = next((candidate for candidate in groups[group] if _key(candidate) not in used), None)
        if base is None:
            continue
        candidate = _d2_pv_root(compiled, native, parent, base, used, prefix="R18_D2_PV")
        if candidate is not None:
            d2.append(candidate)
            used.add(_key(candidate))
        if len(d2) == ROOTS_PER_DISTRIBUTION:
            break
    if len(d2) != ROOTS_PER_DISTRIBUTION:
        raise RuntimeError("unable to reconstruct R18 D2 roots")
    return {_key(row) for row in d1 + d2}


def _groups(records: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for row in records:
        result.setdefault(str(row.get("source_group", "")), []).append(row)
    return result


def _stats(values: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(values)), "max": float(np.max(values)),
        "mean": float(np.mean(values)), "std": float(np.std(values)),
        "rms": float(np.sqrt(np.mean(np.square(values)))),
    }


def _screen_pool(compiled, native, parent, *, label: str, seed: int, forbidden: set[str], pv_corridor: bool = False):
    retained: list[dict] = []
    examined = 0
    eligible = 0
    errors = 0
    source_ids: list[str] = []
    used_groups: set[str] = set()
    for round_index in range(MAX_POOL_ROUNDS):
        pool_seed = seed + 2 * round_index
        pool, source_id = f60._fresh_selfplay(compiled, native, parent, pool_seed, ROOTS_PER_DISTRIBUTION, smoke=False)
        source_ids.append(source_id)
        grouped = _groups(pool)
        for group in sorted(grouped):
            group_id = f"{label}_seed{pool_seed}_{group}"
            if group_id in used_groups:
                continue
            used_groups.add(group_id)
            for candidate in grouped[group]:
                if _key(candidate) in forbidden:
                    continue
                screened_candidate = candidate
                if pv_corridor:
                    screened_candidate = _d2_pv_root(
                        compiled, native, parent, candidate, forbidden,
                        prefix=f"{label}_PV_seed{pool_seed}",
                    )
                    if screened_candidate is None:
                        continue
                examined += 1
                try:
                    rows, metadata = f59._spectrum_for_root(compiled, native, parent, screened_candidate, smoke=False)
                    stable = metadata["spectrum_top_10k_action_key"] == metadata["spectrum_top_20k_action_key"]
                    ordinary = f59._ordinary_usable(metadata)
                except Exception:
                    errors += 1
                    continue
                if stable and ordinary:
                    retained.append(dict(screened_candidate, source_group=group_id))
                    forbidden.add(_key(screened_candidate))
                    eligible += 1
                    break
            if len(retained) == ROOTS_PER_DISTRIBUTION:
                break
        if len(retained) == ROOTS_PER_DISTRIBUTION:
            break
    if len(retained) != ROOTS_PER_DISTRIBUTION:
        raise RuntimeError(f"{label} trusted-target pool retained {len(retained)} roots, expected {ROOTS_PER_DISTRIBUTION}")
    return retained, {
        "candidate_roots_examined": examined,
        "eligible_roots": eligible,
        "eligibility_pass_rate": eligible / examined if examined else 0.0,
        "screen_errors": errors,
        "source_ids": source_ids,
    }


def _fit(records, compiled, native, parent):
    roots = []
    for index, record in enumerate(records):
        rows, metadata = f59._spectrum_for_root(compiled, native, parent, record, smoke=False)
        if metadata["spectrum_top_10k_action_key"] != metadata["spectrum_top_20k_action_key"] or not f59._ordinary_usable(metadata):
            raise RuntimeError(f"retained root {index} failed trust gate on replay")
        usable = [row for row in rows if row.q_20k is not None]
        if len(usable) < 2:
            raise RuntimeError(f"root {index} has fewer than two usable q20 actions")
        roots.append(usable)
    features = np.vstack([row.features for root in roots for row in root])
    base = np.asarray([row.base_q for root in roots for row in root], dtype=float)
    target = np.asarray([row.q_20k for root in roots for row in root], dtype=float)
    groups = []
    cursor = 0
    for root in roots:
        groups.append(np.arange(cursor, cursor + len(root)))
        cursor += len(root)
    model = f61._fit_serializable(features, base, target, groups, "POINTWISE_Q", TRAINING_SEED)
    spec = {"candidate_id": "F61_D12_POINTWISE_Q_SEED_59013_TRUSTED_TARGET", "training_distribution": "D12_D1_D2_TRUSTED", "objective": "POINTWISE_Q", "seed": TRAINING_SEED}
    child, payload = f61._candidate_checkpoint(parent, compiled, model, spec)
    residual = target - base
    prediction = model.predict(features)
    return child, payload, {
        "training_roots": len(roots), "training_actions": int(len(features)),
        "target_residual": _stats(residual), "learned_residual": _stats(prediction),
        "prediction_to_target_rms_ratio": float(np.sqrt(np.mean(prediction ** 2)) / np.sqrt(np.mean(residual ** 2))),
        "model_sha256": f61.stable_sha256(payload),
    }


def _frozen_search(compiled, native, parent, child):
    rows = []
    openings = generate_arena_openings(compiled, count=4, seed=FROZEN_OPENING_SEED, min_plies=2, max_plies=6)
    for opening in openings.openings:
        record = {"action_history": [f59.action_to_dict(action) for action in opening.actions]}
        session = f59._session(compiled, record)
        results = []
        for checkpoint in (parent, child):
            result = SemanticSearchEngine(compiled, native, checkpoint=checkpoint, tt_megabytes=TT_MB).search(session, SearchLimits(max_depth=DEPTH, max_nodes=NODES, quiescence_max_depth=0))
            results.append({"action": None if result.action is None else f59.action_to_dict(result.action), "score": int(result.score)})
        rows.append({"opening_id": opening.final_position_key, "parent": results[0], "child": results[1], "changed": results[0]["action"] != results[1]["action"]})
    return rows


def _arena_payload(summary) -> dict:
    return {"pair_count": summary.pair_count, "pair_scores": list(summary.pair_scores), "mean_pair_score": summary.mean_pair_score, "child_better_pairs": summary.child_better_pairs, "tied_pairs": summary.tied_pairs, "child_worse_pairs": summary.child_worse_pairs, "game_wins": summary.game_wins, "game_draws": summary.game_draws, "game_losses": summary.game_losses, "bootstrap_low": summary.bootstrap_low, "bootstrap_high": summary.bootstrap_high}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-arena", action="store_true")
    args = parser.parse_args()
    compiled, native, parent, _ = gen._context(RULESET)
    forbidden = {_key(row) for row in gen._d0_records(compiled, 620000, count=24, smoke=False)}
    forbidden |= _opening_keys(compiled)
    r18 = _r18_keys(compiled, native, parent, set(forbidden))
    forbidden |= r18
    d1, d1_stats = _screen_pool(compiled, native, parent, label="D1", seed=D1_SEED, forbidden=forbidden)
    # D2 is independently self-play generated and each candidate is advanced
    # through the existing F60 PV corridor before applying the trust gate.
    d2, d2_stats = _screen_pool(compiled, native, parent, label="D2", seed=D2_SEED, forbidden=forbidden, pv_corridor=True)
    records = d1 + d2
    if len(records) != 24 or len({_key(row) for row in records}) != 24:
        raise RuntimeError("trusted D1/D2 root identity is not exactly 24 unique positions")
    child, model_payload, fit_metrics = _fit(records, compiled, native, parent)
    frozen = _frozen_search(compiled, native, parent, child)
    if not any(row["changed"] for row in frozen):
        raise RuntimeError("trusted-target candidate is behaviorally identical to parent on all frozen openings")
    payload = {"schema": "generic-chess-f61-pointwise-trusted-target-screen-v1", "ruleset": RULESET, "training_distribution": "D12_D1_D2_TRUSTED", "d1_seed": D1_SEED, "d2_seed": D2_SEED, "arena_seed": ARENA_SEED, "parent_checkpoint_id": parent.checkpoint_id, "child_checkpoint_id": child.checkpoint_id, "model_sha256": fit_metrics["model_sha256"], "training": fit_metrics, "root_counts": {"D1_V2_SELFPLAY": len(d1), "D2_V2_PV_CORRIDOR": len(d2), "total": len(records)}, "eligibility": {"D1": d1_stats, "D2": d2_stats}, "r18_disjoint_root_count": len(r18), "frozen_opening_search": {"opening_seed": FROZEN_OPENING_SEED, "nodes": NODES, "max_depth": DEPTH, "tt_megabytes": TT_MB, "rows": frozen}}
    if args.run_arena:
        openings = generate_arena_openings(compiled, count=1, seed=ARENA_SEED, min_plies=2, max_plies=6)
        result = run_arena_game_resumable(compiled, native, parent, child, ArenaConfig(pairs=1, nodes_per_move=NODES, max_depth=DEPTH, tt_megabytes=TT_MB, opening_seed=ARENA_SEED, opening_count=1, min_plies=2, max_plies=6, workers=1), progress_dir=OUT.parent / "arena-progress-trusted-target" / str(compiled.ruleset_fingerprint) / f"seed-{ARENA_SEED}", openings=openings, stop_on_decision=False)
        if result.status != "COMPLETE" or result.summary is None:
            raise RuntimeError(f"Arena incomplete: {result.status} {result.reason}")
        payload["fresh_arena"] = {"opening_seed": ARENA_SEED, "nodes": NODES, "max_depth": DEPTH, "tt_megabytes": TT_MB, **_arena_payload(result.summary)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
