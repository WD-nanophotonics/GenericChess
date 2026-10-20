"""Outcome-blind full-history Chess root-pool feasibility for task2618.

Reads only initial-root records from prior Chess traces and reconstructs the
registered complete task2616 training-family root pool. It does not use any
outcome, post-root move, model weight, or new game/search result.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from results.dev_aux.task2492.adapters import ChessEnv  # noqa: E402
from results.dev_aux.task2565.train import prefix  # noqa: E402

TRAIN_SEED = 0
TRAIN_FAMILY_RANGE = range(810001, 820001)
EVAL_SEED = 0
EVAL_FAMILY_RANGE = range(910001, 920001)
TRAIN_ROOTS_REQUIRED = 512
EVAL_ROOTS_REQUIRED = 32
OUT = ROOT / "results/dev_aux/task2619"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(record: dict) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def is_chess(plan: dict) -> bool:
    rules = plan.get("rules", [])
    return plan.get("domain") == "chess" or (isinstance(rules, list) and 0 in rules)


def source_pin(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(data)}


def read_initial_records(path: Path) -> tuple[set[str], int]:
    roots: set[str] = set()
    rows = 0
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            row = json.loads(line)
            record = row.get("initial_record")
            if isinstance(record, dict):
                roots.add(canonical(record))
                rows += 1
    return roots, rows


def generated_root(generator_seed: int, family: int) -> dict | None:
    env = ChessEnv()
    prefix(env, generator_seed, family, 8)
    record = env.record()
    return record if len(record.get("moves", [])) == 8 else None


def main() -> None:
    prior_eval: set[str] = set()
    prior_train: set[str] = set()
    source_rows: list[dict] = []
    seen_eval_paths: set[Path] = set()
    seen_train_paths: set[Path] = set()
    possible_training_roots: set[str] = set()

    for plan_path in sorted(ROOT.joinpath("results/dev_aux").rglob("eval-plan.json")):
        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        if not is_chess(plan):
            continue
        games_path = plan_path.parent / "eval-games.jsonl"
        if not games_path.is_file():
            continue
        roots, rows = read_initial_records(games_path)
        prior_eval.update(roots)
        seen_eval_paths.add(games_path)
        source_rows.append({"kind": "registered_eval_roots", **source_pin(games_path), "rows": rows, "unique_roots": len(roots)})

    for plan_path in sorted(ROOT.joinpath("results/dev_aux").rglob("plan.json")):
        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        if not is_chess(plan):
            continue
        for relative in ("games.jsonl", "train/games.jsonl", "tree-games.jsonl"):
            games_path = plan_path.parent / relative
            if not games_path.is_file() or games_path in seen_train_paths:
                continue
            roots, rows = read_initial_records(games_path)
            prior_train.update(roots)
            seen_train_paths.add(games_path)
            source_rows.append({"kind": "observed_training_starts", **source_pin(games_path), "rows": rows, "unique_roots": len(roots)})

        # This exact full-pool recipe was independently established by task2617
        # for the task2616 Chess training plan; do not generalize its family
        # allocation convention to unrelated historical runners.
        if plan_path.relative_to(ROOT).as_posix() == "results/dev_aux/task2568/plan.json":
            offset = plan.get("training_family_offset")
            max_games = plan.get("max_games")
            plies = plan.get("prefix_plies")
        else:
            offset = max_games = plies = None
        if isinstance(offset, int) and isinstance(max_games, int) and isinstance(plies, int) and plies == 8:
            # The pinned task2565 training source assigns one family per pair
            # of games; reconstruct every possible start in this registered pool.
            stop = offset + (max_games + 1) // 2
            roots = set()
            for family in range(offset, stop):
                record = generated_root(0, family)
                if record is not None:
                    roots.add(canonical(record))
            possible_training_roots.update(roots)
            source_rows.append({
                "kind": "reconstructed_possible_training_starts",
                "plan": plan_path.relative_to(ROOT).as_posix(),
                "plan_sha256": source_pin(plan_path)["sha256"],
                "generator_seed": 0,
                "family_range": [offset, stop],
                "plies": plies,
                "unique_roots": len(roots),
            })

    excluded = prior_eval | prior_train | possible_training_roots
    selected_train: list[dict] = []
    selected_keys: set[str] = set()
    train_examined = train_invalid = train_overlap = 0
    for family in TRAIN_FAMILY_RANGE:
        record = generated_root(TRAIN_SEED, family)
        if record is None:
            train_invalid += 1
            continue
        train_examined += 1
        key = canonical(record)
        if key in excluded or key in selected_keys:
            train_overlap += 1
            continue
        selected_keys.add(key)
        selected_train.append({"generator_seed": TRAIN_SEED, "family": family, "record": record, "record_sha256": sha(key.encode())})
        if len(selected_train) == TRAIN_ROOTS_REQUIRED:
            break
    if len(selected_train) != TRAIN_ROOTS_REQUIRED:
        raise SystemExit(f"only {len(selected_train)}/{TRAIN_ROOTS_REQUIRED} training roots available")

    selected_eval: list[dict] = []
    selected_eval_keys: set[str] = set()
    eval_examined = eval_invalid = eval_overlap = 0
    for family in EVAL_FAMILY_RANGE:
        record = generated_root(EVAL_SEED, family)
        if record is None:
            eval_invalid += 1
            continue
        eval_examined += 1
        key = canonical(record)
        if key in excluded or key in selected_keys or key in selected_eval_keys:
            eval_overlap += 1
            continue
        selected_eval_keys.add(key)
        selected_eval.append({"generator_seed": EVAL_SEED, "family": family, "record": record, "record_sha256": sha(key.encode())})
        if len(selected_eval) == EVAL_ROOTS_REQUIRED:
            break
    if len(selected_eval) != EVAL_ROOTS_REQUIRED:
        raise SystemExit(f"only {len(selected_eval)}/{EVAL_ROOTS_REQUIRED} evaluation roots available")

    overlap = selected_keys & selected_eval_keys
    assert not overlap
    pins = [source_pin(ROOT / "results/dev_aux/task2492/adapters.py"), source_pin(ROOT / "results/dev_aux/task2565/train.py")]
    result = {
        "status": "OUTCOME_BLIND_ROOT_FEASIBILITY_ONLY",
        "root_identity": "canonical complete standard-Chess GameSession record: initial FEN, ordered eight-ply UCI history, and resulting FEN",
        "python_chess_version": chess.__version__,
        "source_pins": pins,
        "prior_source_rows": source_rows,
        "prior_root_counts": {
            "registered_eval_rows": sum(row["rows"] for row in source_rows if row["kind"] == "registered_eval_roots"),
            "registered_eval_unique": len(prior_eval),
            "observed_training_rows": sum(row["rows"] for row in source_rows if row["kind"] == "observed_training_starts"),
            "observed_training_unique": len(prior_train),
            "reconstructed_possible_training_unique": len(possible_training_roots),
            "union_excluded_unique": len(excluded),
        },
        "prospective_training": {
            "generator_seed": TRAIN_SEED,
            "candidate_family_range": [TRAIN_FAMILY_RANGE.start, TRAIN_FAMILY_RANGE.stop],
            "selected": len(selected_train),
            "families": [row["family"] for row in selected_train],
            "valid_examined_until_selection": train_examined,
            "invalid_short_or_terminal": train_invalid,
            "rejected_exact_overlap_or_duplicate": train_overlap,
            "overlap_with_all_prior_roots": len(selected_keys & excluded),
        },
        "prospective_evaluation": {
            "generator_seed": EVAL_SEED,
            "candidate_family_range": [EVAL_FAMILY_RANGE.start, EVAL_FAMILY_RANGE.stop],
            "selected": len(selected_eval),
            "families": [row["family"] for row in selected_eval],
            "valid_examined_until_selection": eval_examined,
            "invalid_short_or_terminal": eval_invalid,
            "rejected_exact_overlap_or_duplicate": eval_overlap,
            "overlap_with_prior_roots_or_training": len(selected_eval_keys & (excluded | selected_keys)),
            "overlap_with_prospective_training": len(selected_eval_keys & selected_keys),
        },
        "claim_limit": "Exact full-history start disjointness from all scanned prior registered Chess evaluation starts, observed Chess training starts, and the reconstructed task2616 possible training-root pool only; not descendant-state, semantic/transposition, unobserved historical potential roots, or distributional independence. Roots remain prospective and must be rebound after any generator, seed, family-range, or recipe change. No learner was run; outcome fields are not accessed or used by audit logic.",
    }
    (OUT / "root-feasibility.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "prospective-training-roots.json").write_text(json.dumps({"task": "DEV_AUX2619", "roots": selected_train}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "prospective-evaluation-roots.json").write_text(json.dumps({"task": "DEV_AUX2619", "roots": selected_eval}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "prior": result["prior_root_counts"],
        "training_selected": result["prospective_training"]["selected"],
        "training_examined": train_examined,
        "training_rejected": train_overlap,
        "evaluation_selected": result["prospective_evaluation"]["selected"],
        "evaluation_examined": eval_examined,
        "evaluation_rejected": eval_overlap,
        "train_eval_overlap": len(overlap),
        "outputs": ["root-feasibility.json", "prospective-training-roots.json", "prospective-evaluation-roots.json"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
