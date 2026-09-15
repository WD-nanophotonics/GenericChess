"""F88R1: resume only the existing incomplete alpha=0.5 Arena2 game."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import f88_f87_update_damping_arena2 as f88  # noqa: E402


WORK_ORDER = "GENERICCHESS_F88R1_COMPLETE_ALPHA05_ARENA2"
F88_ALPHA = 0.5
EXPECTED_CANDIDATE_ID = "0b318ea0a719971634abbc443e3334dfcef4a017d94d4dfd01c8a6ca69954316"
EXPECTED_CORPUS_ID = "6eca12faa0981e1c71f637eae7f66ee4a053193a752fbe592d2b0edafbdffd2a"
EXPECTED_OPENING_ID = "bf02348560711e9fe727d670d421202bb5704f0a75015fbc1016e113b0d530ba"
EXPECTED_PARTIAL_NODES = 104448
EXPECTED_PARTIAL_PLIES = 204
PROGRESS_ROOT = ROOT / ".generic_chess_flow/f88-f87-update-damping-arena2"
ALPHA_PROGRESS = PROGRESS_ROOT / "alpha-0.5"
RESULT_PATH = ROOT / "artifacts/f88_f87_update_damping_arena2/arena2_full_result.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_initial_scope() -> None:
    partial_path = ALPHA_PROGRESS / "partial-game-000001-owner-0.json"
    if not partial_path.is_file():
        raise RuntimeError("F88R1 requires the existing alpha=0.5 partial game")
    partial = _read_json(partial_path)
    if (
        partial.get("status") != "partial"
        or partial.get("child_owner") != 0
        or partial.get("pair") != 1
        or partial.get("opening_id") != EXPECTED_OPENING_ID
        or partial.get("searched_nodes") != EXPECTED_PARTIAL_NODES
        or partial.get("plies") != EXPECTED_PARTIAL_PLIES
    ):
        raise RuntimeError("F88R1 partial evidence does not match the frozen continuation scope")
    if (PROGRESS_ROOT / "alpha-0.25").exists():
        alpha025_before = sorted(
            str(path.relative_to(PROGRESS_ROOT / "alpha-0.25"))
            for path in (PROGRESS_ROOT / "alpha-0.25").rglob("*")
            if path.is_file()
        )
        if not alpha025_before:
            raise RuntimeError("F88R1 alpha=0.25 evidence directory is unexpectedly empty")


def _merge_partial_evidence(previous: dict, resumed: dict) -> dict:
    merged = copy.deepcopy(resumed)
    if merged.get("status") == "COMPLETE":
        return merged
    prior_games = list(previous.get("games") or [])
    current_partial = ALPHA_PROGRESS / "partial-game-000001-owner-0.json"
    partial = _read_json(current_partial) if current_partial.is_file() else {}
    resumed_games = list(merged.get("games") or [])
    merged["games"] = prior_games + resumed_games
    if partial:
        merged["games"].append(
            {
                "child_owner": partial.get("child_owner"),
                "completed": False,
                "opening_id": partial.get("opening_id"),
                "pair": partial.get("pair"),
                "plies": partial.get("plies"),
                "result": None,
                "searched_nodes": partial.get("searched_nodes"),
                "status": partial.get("status"),
                "truncated": True,
                "truncation_reason": merged.get("reason"),
                "winner": None,
            }
        )
    return merged


def resume_existing(result_path: Path = RESULT_PATH) -> dict:
    _assert_initial_scope()
    allocation, compiled, native, parent, raw, corpus = f88._load_context()
    if corpus.corpus_id != EXPECTED_CORPUS_ID:
        raise RuntimeError("F88R1 Arena2 corpus identity changed")
    candidate, metadata = f88.build_candidate(parent, raw, F88_ALPHA)
    if candidate.checkpoint_id != EXPECTED_CANDIDATE_ID:
        raise RuntimeError("F88R1 alpha=0.5 candidate identity changed")
    previous = _read_json(result_path)
    alpha025 = copy.deepcopy(previous["candidates"][1])
    resumed = f88.run_candidate(compiled, native, parent, candidate, corpus, metadata, ALPHA_PROGRESS)
    resumed = _merge_partial_evidence(previous["candidates"][0], resumed)
    output = copy.deepcopy(previous)
    output["candidates"][0] = resumed
    output["candidates"][1] = alpha025
    output["continuation_work_order"] = WORK_ORDER
    output["status"] = "COMPLETE" if all(
        item.get("status") == "COMPLETE"
        and item.get("completed_games") == 4
        and item.get("completed_pairs") == 2
        for item in output["candidates"]
    ) else "INCOMPLETE"
    result_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-alpha05", action="store_true")
    parser.add_argument("--result-path", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    if not args.resume_alpha05:
        parser.error("F88R1 requires --resume-alpha05")
    print(json.dumps(resume_existing(args.result_path), sort_keys=True))
