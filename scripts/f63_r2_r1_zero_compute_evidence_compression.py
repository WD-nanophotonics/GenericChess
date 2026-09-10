"""Compress preserved F63 evidence and fingerprint frozen candidates.

This is intentionally an offline evidence pass: it never calls a search,
arena, engine, or new-game generator. Candidate models are reconstructed from
the already frozen F62 fit artifacts, then evaluated algebraically on the
already persisted F62 action rows.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from scripts import f63_champion_loop_causal_triage as f63  # noqa: E402
from scripts import f63_r2_strength_first_cheap_funnel as r2  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f62_learned_champion_repeatability as f62  # noqa: E402


SEEDS = (59011, 59012, 59013)
R10_ROOT = ROOT / ".generic_chess_flow" / "f63-champion-loop-causal-triage" / "progress"
STAGE0_PATH = ROOT / ".generic_chess_flow" / "f63-r2-strength-first-cheap-funnel" / "screen_results.json"
OUT = ROOT / ".generic_chess_flow" / "f63-r2-r1-zero-compute-evidence-compression"
RESULT_PATH = OUT / "evidence_compression.json"
REPORT_PATH = ROOT / "docs" / "architecture" / "GENERICCHESS_F63_R2_R1_ZERO_COMPUTE_CLOSEOUT.md"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _action_key(action: dict[str, Any]) -> str:
    return json.dumps(action, sort_keys=True, separators=(",", ":"))


def _r10_evidence() -> dict[str, Any]:
    by_seed: dict[str, dict[str, Any]] = {}
    for seed in SEEDS:
        directory = R10_ROOT / f"candidate-{seed}-common-4-calibrated-seed-630403"
        games: dict[int, dict[int, dict[str, Any]]] = {}
        for path in sorted(directory.glob("game-*.json")) if directory.is_dir() else ():
            match = re.fullmatch(r"game-(\d+)-owner-(\d+)\.json", path.name)
            if not match:
                continue
            pair_index, owner = map(int, match.groups())
            payload = _load(path)
            identity = payload["game_identity"]
            game = payload["game"]
            if int(identity["pair_index"]) != pair_index:
                raise RuntimeError(f"pair index mismatch: {path}")
            if int(identity["child_owner"]) != owner or int(game["child_owner"]) != owner:
                raise RuntimeError(f"owner mismatch: {path}")
            games.setdefault(pair_index, {})[owner] = {
                "file": path.name,
                "winner": game.get("winner"),
                "result": game.get("result"),
                "plies": game.get("plies"),
                "termination_mode": game.get("termination_mode") or game.get("result"),
                "opening_id": game.get("opening_id"),
                "opening_position_key": game.get("opening_position_key"),
                "final_position_key": game.get("final_position_key"),
            }
        complete = []
        pairs = []
        wins = draws = losses = 0
        for pair_index in sorted(games):
            pair = games[pair_index]
            if set(pair) != {0, 1}:
                continue
            game_scores = []
            for owner in (0, 1):
                result = pair[owner]["result"]
                winner = pair[owner]["winner"]
                if result == "repetition" or winner is None:
                    score = 0.5
                    draws += 1
                elif int(winner) == owner:
                    score = 1.0
                    wins += 1
                else:
                    score = 0.0
                    losses += 1
                pair[owner]["child_score"] = score
                game_scores.append(score)
            opening_ids = sorted({pair[owner]["opening_id"] for owner in (0, 1)})
            if len(opening_ids) != 1:
                raise RuntimeError(f"swapped-role opening mismatch: seed={seed} pair={pair_index}")
            complete.append(pair_index)
            pairs.append({
                "pair_index": pair_index,
                "opening_id": opening_ids[0],
                "games": [pair[owner] for owner in (0, 1)],
                "pair_score_child_points": sum(game_scores) / 2.0,
                "w_d_l_child_games": [
                    sum(score == 1.0 for score in game_scores),
                    sum(score == 0.5 for score in game_scores),
                    sum(score == 0.0 for score in game_scores),
                ],
            })
        by_seed[str(seed)] = {
            "game_indices": sorted(index for pair in games.values() for index in []),
            "persisted_game_files": sum(len(pair) for pair in games.values()),
            "complete_pair_indices": complete,
            "complete_pairs": pairs,
            "w_d_l_child_games": [wins, draws, losses],
            "selection_authority": "forbidden_unequal_r10_exposure",
        }
        by_seed[str(seed)]["game_indices"] = sorted(
            int(re.fullmatch(r"game-(\d+)-owner-\d+\.json", item["file"]).group(1))
            for pair in games.values() for item in pair.values()
        )
    overlap = sorted(
        set(by_seed["59011"]["complete_pair_indices"])
        & set(by_seed["59012"]["complete_pair_indices"])
    )
    return {"by_seed": by_seed, "overlapping_complete_pair_indices": overlap}


def _stage0_signatures() -> dict[str, dict[str, str]]:
    payload = _load(STAGE0_PATH)
    result: dict[str, dict[str, str]] = {str(seed): {} for seed in SEEDS}
    for distribution, per_seed in payload["screen"].items():
        for seed in SEEDS:
            rows = per_seed[str(seed)]["rows"]
            if len(rows) != 1:
                raise RuntimeError("Stage 0 expected exactly one named root per distribution")
            result[str(seed)][distribution] = _action_key(rows[0]["selected_action"])
    return result


def _fingerprint(compiled) -> dict[str, Any]:
    gen1, candidates = r2._candidate_population(compiled)
    by_seed = {str(row["seed"]): row["checkpoint"] for row in candidates}
    summary, _provenance, _persisted, _identity = f63._load_f62_training_summary(compiled, gen1)
    records, _ = f62._fresh_records(compiled, smoke=False)
    roots = summary["roots"]
    root_meta = summary["roots_metadata"]
    rows_by_seed: dict[str, list[dict[str, Any]]] = {str(seed): [] for seed in SEEDS}
    tolerance = 1e-9
    for index, rows in enumerate(roots):
        per_candidate = {}
        for seed in SEEDS:
            checkpoint = by_seed[str(seed)]
            model = CompactNonlinearResidual.from_dict(checkpoint.compact_nonlinear)
            predicted = f59._predict_total_q(rows, model.predict)
            order = sorted(
                range(len(rows)),
                key=lambda item: (-float(predicted[item]), rows[item].action_key),
            )
            top, second = order[0], order[1] if len(order) > 1 else order[0]
            per_candidate[str(seed)] = {
                "top_action": rows[top].action_key,
                "top_two_margin": float(predicted[top] - predicted[second]),
                "ordering": [rows[item].action_key for item in order],
                "scores": [float(value) for value in predicted],
            }
        rows_by_seed["59011"].append(per_candidate["59011"])
        rows_by_seed["59012"].append(per_candidate["59012"])
        rows_by_seed["59013"].append(per_candidate["59013"])

    pairwise = {}
    for left, right in (("59011", "59012"), ("59011", "59013"), ("59012", "59013")):
        top_agreement = []
        rank_disagreement = []
        differing_roots = []
        indistinguishable_roots = []
        for index in range(len(roots)):
            a, b = rows_by_seed[left][index], rows_by_seed[right][index]
            top_agreement.append(a["top_action"] == b["top_action"])
            rank_a = {key: rank for rank, key in enumerate(a["ordering"])}
            rank_b = {key: rank for rank, key in enumerate(b["ordering"])}
            common = set(rank_a) & set(rank_b)
            rank_disagreement.append(sum(rank_a[key] != rank_b[key] for key in common))
            if not top_agreement[-1] or rank_disagreement[-1]:
                differing_roots.append(index)
            if (
                a["ordering"] == b["ordering"]
                and all(abs(x - y) <= tolerance for x, y in zip(a["scores"], b["scores"]))
            ):
                indistinguishable_roots.append(index)
        pairwise[f"{left}_vs_{right}"] = {
            "root_count": len(roots),
            "top_action_agreement_count": sum(top_agreement),
            "top_action_agreement_rate": sum(top_agreement) / len(top_agreement),
            "rank_disagreement_total": sum(rank_disagreement),
            "roots_where_ordering_differs": differing_roots,
            "roots_effectively_indistinguishable": indistinguishable_roots,
        }

    focused = []
    for index in range(len(roots)):
        rank_difference = 0
        for other in ("59011", "59012"):
            left = {key: rank for rank, key in enumerate(rows_by_seed["59013"][index]["ordering"])}
            right = {key: rank for rank, key in enumerate(rows_by_seed[other][index]["ordering"])}
            rank_difference += sum(left[key] != right[key] for key in left.keys() & right.keys())
        top_differs_from_both = (
            rows_by_seed["59013"][index]["top_action"]
            != rows_by_seed["59011"][index]["top_action"]
            and rows_by_seed["59013"][index]["top_action"]
            != rows_by_seed["59012"][index]["top_action"]
        )
        focused.append({
            "index": index,
            "rank_difference": rank_difference,
            "top_differs_from_both": top_differs_from_both,
            "relevant_margin": rows_by_seed["59013"][index]["top_two_margin"],
        })
    preferred = [row for row in focused if row["top_differs_from_both"]]
    pool = preferred or focused
    selected = max(pool, key=lambda row: (row["rank_difference"], row["relevant_margin"], -row["index"]))
    primary_index = selected["index"]
    primary = {
        "root_index": primary_index,
        "position_key": root_meta[primary_index]["position_key"],
        "source_group": records[primary_index].get("source_group"),
        "source_split": records[primary_index].get("source_split"),
        "reason": "59013-focused cached rank disagreement; top-differs-from-both preferred, then margin and lower index",
        "selection_candidates_with_top_difference": [row["index"] for row in preferred],
        "selection_rank_difference": selected["rank_difference"],
        "candidate_fingerprints": {str(seed): rows_by_seed[str(seed)][primary_index] for seed in SEEDS},
    }
    observable_signatures = {str(seed): () for seed in SEEDS}
    stage0 = _stage0_signatures()
    for seed in SEEDS:
        observable_signatures[str(seed)] = tuple(stage0[str(seed)].values()) + tuple(
            row["top_action"] for row in rows_by_seed[str(seed)]
        )
    behavior_classes: dict[str, int] = {}
    representatives: list[str] = []
    for seed in SEEDS:
        existing = next(
            (class_id for class_id, representative in enumerate(representatives)
             if observable_signatures[representative] == observable_signatures[str(seed)]),
            None,
        )
        if existing is None:
            existing = len(representatives)
            representatives.append(str(seed))
        behavior_classes[str(seed)] = existing
    return {
        "cached_root_count": len(roots),
        "candidate_checkpoint_ids": {str(row["seed"]): row["checkpoint"].checkpoint_id for row in candidates},
        "pairwise": pairwise,
        "primary_witness": primary,
        "stage0_signatures": stage0,
        "behavior_classes": {
            "count": len(set(behavior_classes.values())),
            "by_seed": behavior_classes,
            "definition": "exact Stage-0 selected actions plus cached F62 top-action sequence",
        },
        "stage0_marker": "three_named_opening_smoke_roots_not_distribution_evidence",
    }


def run() -> dict[str, Any]:
    compiled, _native, _profile = f59._ruleset(f59.LABELS[1])
    payload = {
        "schema": "generic-chess-f63-r2-r1-zero-compute-evidence-v1",
        "work_order": "GENERICCHESS-F63-R2-R1-ZERO-COMPUTE-EVIDENCE-COMPRESSION",
        "parent_repository_sha": "6292c3ef63dd0295e668b8db55d23be30724b2c6",
        "new_game_or_search_compute": False,
        "r10": _r10_evidence(),
        "fingerprint": _fingerprint(compiled),
        "next_experiment": {
            "status": "DESIGNED_NOT_RUN",
            "decision_rule": "one frozen witness; one swapped-role pair per distinct behavior class",
            "nodes_per_move": 2000,
            "max_plies": 64,
            "ongoing_at_max_plies": "UNRESOLVED",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true")
    parser.parse_args()
    payload = run()
    fp = payload["fingerprint"]
    compact = {
        "r10_complete_pairs": {seed: row["complete_pair_indices"] for seed, row in payload["r10"]["by_seed"].items()},
        "r10_overlap": payload["r10"]["overlapping_complete_pair_indices"],
        "cached_roots": fp["cached_root_count"],
        "pairwise": {
            key: {
                "top_action_agreement_rate": value["top_action_agreement_rate"],
                "ordering_difference_roots": len(value["roots_where_ordering_differs"]),
                "indistinguishable_roots": len(value["roots_effectively_indistinguishable"]),
            }
            for key, value in fp["pairwise"].items()
        },
        "primary_witness": fp["primary_witness"],
        "result_sha256": stable_sha256(payload),
    }
    print(json.dumps(compact, sort_keys=True))


if __name__ == "__main__":
    main()
