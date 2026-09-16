"""F90: measure the frozen F88 alpha=0.5 candidate across registered Arena8."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import (  # noqa: E402
    ArenaConfig,
    ArenaExecutionCaps,
    ArenaOpeningCorpus,
    run_arena_game_resumable,
)
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from scripts import f88_f87_update_damping_arena2 as f88  # noqa: E402


WORK_ORDER = "GENERICCHESS_F90_ALPHA05_ARENA8"
PARENT_ID = "c45623c0b905780ed1fd896a8f9364fd369bed1e641519f45fb40a3faf014d71"
RAW_F87_ID = "0c94b1d6b0a0b66939707d1e4184e23cc1391678c7bda67267d834a7565a5c42"
ALPHA05_ID = "0b318ea0a719971634abbc443e3334dfcef4a017d94d4dfd01c8a6ca69954316"
ALPHA05_MODEL_SHA256 = "f5e739b47e896a8d855869a4295d2b90d20a21228575440ffbd9bfd40444cd0b"
ARENA8_CORPUS_ID = "7446aa7fed2e7712941c914785a9db3dc51e9e07350fdbe4cfb7b0c629453755"
ARENA8_OPENING_INDICES = tuple(range(8))
DEFAULT_PROGRESS = ROOT / ".generic_chess_flow/f90-alpha05-arena8"
DEFAULT_RESULT = ROOT / "artifacts/f90_complete_alpha05_arena8/arena8_full_result.json"


def _load_context():
    allocation, compiled, native, parent, raw, _arena2 = f88._load_context()
    arena8_payload = allocation["selection_and_strength_corpora"]["Arena8"]
    if arena8_payload["corpus_id"] != ARENA8_CORPUS_ID:
        raise RuntimeError("F90 Arena8 corpus identity mismatch")
    corpus = ArenaOpeningCorpus.from_dict(arena8_payload["corpus"])
    corpus.validate(compiled)
    if tuple(opening.index for opening in corpus.openings) != ARENA8_OPENING_INDICES:
        raise RuntimeError("F90 requires registered Arena8 openings 0 through 7")
    candidate, metadata = f88.build_candidate(parent, raw, 0.5)
    if parent.checkpoint_id != PARENT_ID or raw.checkpoint_id != RAW_F87_ID:
        raise RuntimeError("F90 frozen parent or raw F87 identity mismatch")
    if candidate.checkpoint_id != ALPHA05_ID:
        raise RuntimeError("F90 alpha=0.5 candidate identity mismatch")
    if metadata["candidate_model_sha256"] != ALPHA05_MODEL_SHA256:
        raise RuntimeError("F90 alpha=0.5 model identity mismatch")
    candidate.validate_ruleset(compiled)
    return allocation, compiled, native, parent, candidate, corpus, metadata


def _game_payload(payload: dict, *, pair_index: int, child_owner: int) -> dict:
    game = payload["game"]
    return {
        "pair_index": pair_index,
        "opening_index": pair_index,
        "child_owner": child_owner,
        "winner": game["winner"],
        "result": game["result"],
        "plies": game["plies"],
        "completed": True,
        "truncated": False,
    }


def _progress_games(progress_dir: Path) -> list[dict]:
    games = []
    for pair_index in range(len(ARENA8_OPENING_INDICES)):
        for child_owner in (0, 1):
            path = progress_dir / f"game-{pair_index:06d}-owner-{child_owner}.json"
            if path.is_file():
                games.append(_game_payload(
                    json.loads(path.read_text(encoding="utf-8")),
                    pair_index=pair_index,
                    child_owner=child_owner,
                ))
    return games


def _partial_progress_games(progress_dir: Path) -> list[dict]:
    partial_games = []
    for path in sorted(progress_dir.glob("partial-game-*.json")):
        match = re.fullmatch(
            r"partial-game-(\d{6})-owner-([01])\.json", path.name
        )
        if match is None:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        partial_games.append({
            "pair_index": int(match.group(1)),
            "opening_index": int(match.group(1)),
            "child_owner": int(match.group(2)),
            "plies": int(payload["plies"]),
            "searched_nodes": int(payload["searched_nodes"]),
            "status": payload["status"],
            "resumable": True,
        })
    return partial_games


def run(progress_dir: Path = DEFAULT_PROGRESS, result_path: Path = DEFAULT_RESULT) -> dict:
    allocation, compiled, native, parent, candidate, corpus, metadata = _load_context()
    config = ArenaConfig(
        pairs=8,
        nodes_per_move=512,
        parent_nodes_per_move=512,
        child_nodes_per_move=512,
        max_depth=12,
        tt_megabytes=8,
        opening_seed=corpus.seed,
        opening_count=8,
        min_plies=corpus.min_plies,
        max_plies=corpus.max_plies,
        workers=2,
        tt_reset_each_move=True,
    )
    caps = ArenaExecutionCaps(
        per_game_wall_seconds=7200,
        per_game_nodes=262144,
        per_game_plies=512,
        max_stage_games=16,
        max_concurrent_games=2,
        stage_wall_seconds=57600,
        logical_cpu_count=4,
    )
    arena = run_arena_game_resumable(
        compiled,
        native,
        parent,
        candidate,
        config,
        progress_dir=progress_dir,
        openings=corpus,
        capture_search_metrics=True,
        execution_caps=caps,
        identity_caps=caps,
        stage_id="f90-complete-alpha05-arena8",
        max_pairs=8,
    )
    games = _progress_games(progress_dir)
    partial_games = _partial_progress_games(progress_dir)
    summary = None if arena.summary is None else {
        "pair_scores": list(arena.summary.pair_scores),
        "mean_pair_score": arena.summary.mean_pair_score,
        "game_wins": arena.summary.game_wins,
        "game_draws": arena.summary.game_draws,
        "game_losses": arena.summary.game_losses,
    }
    output = {
        "schema": "generic-chess-f90-complete-alpha05-arena8-v1",
        "status": arena.status,
        "reason": arena.reason,
        "work_order": WORK_ORDER,
        "parent_checkpoint_id": parent.checkpoint_id,
        "raw_f87_checkpoint_id": RAW_F87_ID,
        "alpha": 0.5,
        "candidate_checkpoint_id": candidate.checkpoint_id,
        "candidate_model_sha256": metadata["candidate_model_sha256"],
        "arena8_corpus_id": corpus.corpus_id,
        "arena8_seed": corpus.seed,
        "opening_indices": list(ARENA8_OPENING_INDICES),
        "config": asdict(config),
        "execution_caps": asdict(caps),
        "completed_games": arena.completed_games,
        "completed_pairs": arena.completed_pairs,
        "total_games": arena.total_games,
        "games": games,
        "resumable_partial_games": partial_games,
        "continuation": {
            "terminal_games_are_immutable": True,
            "resume_partial_games": True,
            "partial_game_count": len(partial_games),
        },
        "summary": summary,
        "historical_f89_arena4_context": {
            "artifact": "artifacts/f89_complete_alpha05_arena4/arena4_complete_evidence.json",
            "mean_pair_score": 0.8125,
            "pooled": False,
        },
        "prior_alpha05_arena2_context": {
            "artifact": "artifacts/f88_f87_update_damping_arena2/arena2_full_result.json",
            "mean_pair_score": 0.75,
            "pooled": False,
        },
        "historical_raw_f87_arena4_context": {
            "artifact": "artifacts/f87_two_trajectory_native_search_distillation/arena4_full_result.json",
            "mean_pair_score": 0.3125,
            "pooled": False,
        },
        "allocation_sha256": stable_sha256(allocation),
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--progress-dir", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--result-path", type=Path, default=DEFAULT_RESULT)
    args = parser.parse_args()
    print(json.dumps(run(args.progress_dir, args.result_path), sort_keys=True))
