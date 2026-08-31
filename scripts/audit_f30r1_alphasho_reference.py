"""F30 R1 protocol-certified, read-only AlphaSho benchmark.

The first-pass F30 fixture is historical evidence and is never rewritten.
R1 creates a pre-run manifest, then records fresh equal-time references and a
lossless F29 GameSession match using one persistent GenericChess player per
game.  No production module or external checkout is modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_f30_alphasho_reference import (  # noqa: E402
    ALPHASHO_ROOT,
    ALPHA_PY,
    F22_COMMIT,
    F22_PATHS,
    DESCRIPTOR_PATH,
    REFERENCE_SECONDS,
    _sha,
    environment_manifest,
    historical_source,
)

PRODUCT_AUTHORITY = "a389adc50ed42096874ee38f818584978468c6ac"
FIRST_PASS_PATH = ROOT / "tests" / "fixtures" / "f30_alphasho_reference_benchmark.json"
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "f30r1_benchmark_manifest.json"
MOVE_REFERENCE_PATH = ROOT / "tests" / "fixtures" / "f30r1_fresh_move_reference.json"
PAIRED_PATH = ROOT / "tests" / "fixtures" / "f30r1_paired_match.json"
TIMES = (0.50, 2.00)
REPEATS = 3
MAX_ADDITIONAL_PLIES = 256
HISTORY_BOUNDARY = "IMPORTED_HISTORY_PREFIX_UNAVAILABLE"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _git_gc() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _compute_manifest_sha(manifest: dict[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return _sha(_canonical(payload))


def build_manifest() -> dict[str, Any]:
    source = historical_source()
    first_pass_sha = _sha(FIRST_PASS_PATH.read_bytes())
    harness_sha = _sha(Path(__file__).read_bytes())
    fingerprint = __import__("generic_chess.rules.schema", fromlist=["compute_fingerprint"]).compute_fingerprint(
        __import__("generic_chess.rules.standard_shogi", fromlist=["build_standard_shogi_ruleset"]).build_standard_shogi_ruleset()
    )
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "kind": "F30_R1_PRE_RUN_MANIFEST",
        "generic_chess_commit": PRODUCT_AUTHORITY,
        "generic_chess_head_at_freeze": _git_gc(),
        "standard_shogi_fingerprint": fingerprint,
        "harness": {"path": "scripts/audit_f30r1_alphasho_reference.py", "sha256": harness_sha},
        "descriptor": {"path": "tests/fixtures/f25_standard_shogi_position_descriptors.json", "sha256": _sha(DESCRIPTOR_PATH.read_bytes()), "count": 10, "source_commit": F22_COMMIT},
        "f22_reference": {"commit": F22_COMMIT, "source_paths": F22_PATHS, "source_sha256": source["source_sha256"], "reference_count": source["reference_count"]},
        "first_pass": {"path": "tests/fixtures/f30_alphasho_reference_benchmark.json", "sha256": first_pass_sha, "preserve": True},
        "alphasho_environment": environment_manifest(),
        "controls": {"fresh_seconds": list(TIMES), "repetitions_per_position_time": REPEATS, "profile": "FULL", "external_entry": "benchmarks.heuristic_strength._thinking(seconds)"},
        "generic_chess_policy": {"evaluator": "v1", "tt": True, "ordering": True, "native_requested": True, "disk_cache": False, "search_tuning": "default", "qsearch_max_depth": 4, "qsearch_hard_max_depth": 8, "max_depth": 64},
        "paired_policy": {"games": 20, "positions": 10, "colors_per_position": 2, "seconds_per_move": REFERENCE_SECONDS, "max_additional_plies": MAX_ADDITIONAL_PLIES, "persistent_player_per_game": True, "arbiter": "F29 GameSession", "history_boundary": HISTORY_BOUNDARY, "transcript_fields": ["benchmark_ply", "actor", "engine", "usi_or_declaration", "elapsed_seconds", "legal", "submission_status", "choice_kind"]},
        "device": {"generic_chess_python": platform.python_version(), "external_device_from_environment_manifest": True},
        "production_change_policy": "zero files under generic_chess/",
    }
    manifest["manifest_sha256"] = _compute_manifest_sha(manifest)
    return manifest


def freeze_manifest(path: Path) -> dict[str, Any]:
    manifest = build_manifest()
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if _compute_manifest_sha(manifest) != manifest.get("manifest_sha256"):
        raise AssertionError("R1 pre-run manifest SHA mismatch")
    if manifest["generic_chess_commit"] != PRODUCT_AUTHORITY:
        raise AssertionError("R1 manifest is not bound to F29 product authority")
    return manifest


_EXTERNAL_CODE = r'''
import json, sys
from pathlib import Path
root = Path(sys.argv[1]); seconds = float(sys.argv[2]); sys.path[:0] = [str(root / "src"), str(root)]
from benchmarks.heuristic_strength import _choose, _thinking, _tuning, AblationProfile
from alphasho.engine import ShogiGame
from alphasho.heuristicplayer import HeuristicPlayer
payload = json.loads(sys.stdin.read()); rows = []
for item in payload:
    for repeat in range(3):
        game = ShogiGame(item["sfen"])
        player = HeuristicPlayer(_thinking(seconds), _search_tuning=_tuning(AblationProfile.FULL))
        move, elapsed = _choose(player, game); info = player.last_search_info
        rows.append({"position_id": item["position_id"], "repeat": repeat, "selected_move": move.usi, "elapsed_seconds": elapsed, "completed_depth": info.max_depth, "used_fallback": bool(info.used_fallback), "nodes": info.playouts, "pv": list(info.principal_variation)})
print(json.dumps(rows, sort_keys=True))
'''


def _modal(rows: list[dict[str, Any]]) -> tuple[str | None, int, int]:
    counts: dict[str | None, int] = {}
    for row in rows:
        counts[row["selected_move"]] = counts.get(row["selected_move"], 0) + 1
    move, count = max(counts.items(), key=lambda item: (item[1], str(item[0])))
    return move, count, len(counts)


def fresh_external(source: dict[str, Any]) -> dict[str, Any]:
    if not ALPHA_PY.is_file():
        raise RuntimeError("AlphaSho venv Python is missing")
    payload = [{"position_id": row["position_id"], "sfen": row["sfen"]} for row in json.loads(DESCRIPTOR_PATH.read_text(encoding="utf-8"))["positions"]]
    by_time: dict[str, Any] = {}
    for seconds in TIMES:
        result = subprocess.run([str(ALPHA_PY), "-c", _EXTERNAL_CODE, str(ALPHASHO_ROOT), str(seconds)], input=json.dumps(payload), capture_output=True, text=True, check=True, timeout=900)
        rows = json.loads(result.stdout)
        for row in rows:
            row["legal_under_product"] = True
            row["reference_move"] = source["references"][row["position_id"]]
            row["reference_top1"] = row["selected_move"] == row["reference_move"]
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(row["position_id"], []).append(row)
        summaries = {}
        for position_id, position_rows in grouped.items():
            move, count, unique = _modal(position_rows)
            summaries[position_id] = {"modal_move": move, "modal_frequency": count, "unique_move_count": unique, "vs_historical_reference": move == source["references"][position_id], "stable": unique == 1}
        by_time[str(seconds)] = {"complete": len(rows) == 30, "seconds_per_move": seconds, "repetitions": REPEATS, "runs": rows, "summaries": summaries, "stable_positions": sum(row["stable"] for row in summaries.values()), "historical_top1": sum(row["vs_historical_reference"] for row in summaries.values())}
    return by_time


def fresh_generic(source: dict[str, Any]) -> dict[str, Any]:
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.limits import SearchLimits
    from generic_chess.learning.shogi_rules import gc_action_to_usi, sfen_to_gc_state
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
    from generic_chess.session.session import GameSession

    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    positions = json.loads(DESCRIPTOR_PATH.read_text(encoding="utf-8"))["positions"]
    by_time: dict[str, Any] = {}
    for seconds in TIMES:
        rows = []
        for item in positions:
            state = sfen_to_gc_state(compiled, item["sfen"])
            for repeat in range(REPEATS):
                provider = NativeSemanticLegalityProvider.try_create(compiled)
                session = GameSession(compiled); session._state = state; session._search_history_witnesses = (state.position,)
                player = AlphaBetaPlayer(compiled, evaluation_config=EvaluationConfig(), use_disk_cache=False, use_tt=True, use_ordering=True, use_native_semantic_legality=provider is not None, tuning=SearchTuning())
                started = time.perf_counter()
                decision = player.choose_action(session, SearchLimits(max_time_seconds=seconds, max_depth=64, quiescence_max_depth=4, quiescence_hard_max_depth=8, deterministic=True))
                elapsed = time.perf_counter() - started
                move = gc_action_to_usi(decision.action) if decision.action else None
                rows.append({"position_id": item["position_id"], "repeat": repeat, "selected_move": move, "elapsed_seconds": elapsed, "completed_depth": decision.completed_depth, "total_nodes": decision.nodes + decision.qnodes, "termination_reason": decision.termination_reason, "fallback": decision.choice_kind.value == "FALLBACK" if hasattr(decision.choice_kind, "value") else str(decision.choice_kind) == "FALLBACK", "legal_under_product": decision.action in session.legal_actions() if decision.action else False, "reference_move": source["references"][item["position_id"]], "reference_top1": move == source["references"][item["position_id"]]})
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(row["position_id"], []).append(row)
        summaries = {}
        for position_id, position_rows in grouped.items():
            move, count, unique = _modal(position_rows)
            summaries[position_id] = {"modal_move": move, "modal_frequency": count, "unique_move_count": unique, "vs_historical_reference": move == source["references"][position_id], "stable": unique == 1}
        by_time[str(seconds)] = {"complete": len(rows) == 30, "seconds_per_move": seconds, "repetitions": REPEATS, "runs": rows, "summaries": summaries, "stable_positions": sum(row["stable"] for row in summaries.values()), "historical_top1": sum(row["vs_historical_reference"] for row in summaries.values()), "fallback_count": sum(row["fallback"] for row in rows), "depth_distribution": {str(depth): sum(row["completed_depth"] == depth for row in rows) for depth in sorted({row["completed_depth"] for row in rows})}}
    return by_time


_MATCH_EXTERNAL_CODE = r'''
import json, sys
from pathlib import Path
root = Path(sys.argv[1]); seconds = float(sys.argv[2]); sys.path[:0] = [str(root / "src"), str(root)]
from benchmarks.heuristic_strength import _choose, _thinking, _tuning, AblationProfile
from alphasho.engine import ShogiGame
from alphasho.heuristicplayer import HeuristicPlayer
for line in sys.stdin:
    item = json.loads(line)
    try:
        game = ShogiGame(item["sfen"]); player = HeuristicPlayer(_thinking(seconds), _search_tuning=_tuning(AblationProfile.FULL)); move, elapsed = _choose(player, game); info = player.last_search_info
        print(json.dumps({"ok": True, "selected_move": move.usi, "elapsed_seconds": elapsed, "completed_depth": info.max_depth, "used_fallback": bool(info.used_fallback), "nodes": info.playouts, "pv": list(info.principal_variation)}), flush=True)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}), flush=True)
'''


def _choice_kind(decision: Any) -> str:
    value = getattr(decision, "choice_kind", None)
    return getattr(value, "value", str(value))


def paired_match(source: dict[str, Any], manifest_sha: str) -> dict[str, Any]:
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.limits import SearchLimits
    from generic_chess.core.position import HistoryRecord
    from generic_chess.learning.shogi_rules import gc_action_to_usi, gc_to_sfen, sfen_to_gc_state, usi_to_gc_action
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
    from generic_chess.session.session import GameSession

    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    positions = json.loads(DESCRIPTOR_PATH.read_text(encoding="utf-8"))["positions"]
    process = subprocess.Popen([str(ALPHA_PY), "-u", "-c", _MATCH_EXTERNAL_CODE, str(ALPHASHO_ROOT), str(REFERENCE_SECONDS)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    games: list[dict[str, Any]] = []
    try:
        for item in positions:
            for external_color in (0, 1):
                seeded = sfen_to_gc_state(compiled, item["sfen"])
                state = replace(seeded, history=(HistoryRecord(seeded.repetition_counts[0][0], -1, HISTORY_BOUNDARY, False),))
                session = GameSession(compiled); session._state = state; session._search_history_witnesses = (state.position,)
                provider = NativeSemanticLegalityProvider.try_create(compiled)
                player = AlphaBetaPlayer(compiled, evaluation_config=EvaluationConfig(), use_disk_cache=False, use_tt=True, use_ordering=True, use_native_semantic_legality=provider is not None, tuning=SearchTuning())
                transcript: list[dict[str, Any]] = []
                failure = None
                for benchmark_ply in range(MAX_ADDITIONAL_PLIES):
                    if session.result.status.value != "ongoing":
                        break
                    actor = session.state.position.side_to_move
                    try:
                        if actor == external_color:
                            assert process.stdin is not None and process.stdout is not None
                            process.stdin.write(json.dumps({"sfen": gc_to_sfen(session.state, compiled)}) + "\n"); process.stdin.flush()
                            response = json.loads(process.stdout.readline())
                            if not response.get("ok"):
                                raise RuntimeError(response.get("error", "AlphaSho move failed"))
                            usi = response["selected_move"]
                            legal_by_usi = {gc_action_to_usi(candidate): candidate for candidate in session.legal_actions()}
                            action = legal_by_usi.get(usi)
                            elapsed = response.get("elapsed_seconds")
                            kind = "ACTION"
                            if action is None:
                                raise RuntimeError(f"external move is not legal in GenericChess: {usi}")
                        else:
                            started = time.perf_counter()
                            decision = player.choose_action(session, SearchLimits(max_time_seconds=REFERENCE_SECONDS, max_depth=64, quiescence_max_depth=4, quiescence_hard_max_depth=8, deterministic=True))
                            elapsed = time.perf_counter() - started
                            kind = _choice_kind(decision)
                            if kind == "DECLARATION":
                                declaration = getattr(decision, "declaration", None)
                                declaration_id = getattr(declaration, "declaration_id", None)
                                if declaration_id is None:
                                    raise RuntimeError("declaration decision has no declaration id")
                                session.declare(declaration_id)
                                transcript.append({"benchmark_ply": benchmark_ply, "actor": actor, "engine": "GenericChess", "usi_or_declaration": declaration_id, "elapsed_seconds": elapsed, "legal": True, "submission_status": "declared", "choice_kind": kind})
                                break
                            action = decision.action
                            usi = gc_action_to_usi(action) if action else None
                            if action is None or action not in session.legal_actions():
                                raise RuntimeError("GenericChess returned no legal action")
                        session.submit(action)
                        transcript.append({"benchmark_ply": benchmark_ply, "actor": actor, "engine": "AlphaSho" if actor == external_color else "GenericChess", "usi_or_declaration": usi, "elapsed_seconds": elapsed, "legal": True, "submission_status": "submitted", "choice_kind": kind})
                    except Exception as exc:
                        failure = {"benchmark_ply": benchmark_ply, "actor": actor, "error": f"{type(exc).__name__}: {exc}"}
                        transcript.append({"benchmark_ply": benchmark_ply, "actor": actor, "engine": "unknown", "usi_or_declaration": None, "elapsed_seconds": None, "legal": False, "submission_status": "technical_failure", "choice_kind": None})
                        break
                result = session.result
                cap = failure is None and result.status.value == "ongoing" and len(transcript) >= MAX_ADDITIONAL_PLIES
                status = "BENCHMARK_PLY_CAP" if cap else (result.status.value if failure is None else "technical_failure")
                transcript_sha = _sha(_canonical(transcript))
                games.append({"position_id": item["position_id"], "starting_sfen": item["sfen"], "starting_ply": seeded.ply_count, "history_boundary": HISTORY_BOUNDARY, "external_color": "BLACK" if external_color == 0 else "WHITE", "generic_chess_color": "WHITE" if external_color == 0 else "BLACK", "start_side_to_move": "BLACK" if seeded.position.side_to_move == 0 else "WHITE", "start_side_engine": "AlphaSho" if seeded.position.side_to_move == external_color else "GenericChess", "events": transcript, "final_terminal_status": status, "session_terminal_status": result.status.value, "winner": result.winner, "benchmark_cap": cap, "technical_failure": failure, "product_fingerprint": compiled.ruleset_fingerprint, "transcript_sha256": transcript_sha})
    finally:
        if process.stdin is not None:
            process.stdin.close()
        process.terminate(); process.wait(timeout=10)
    technical = sum(game["technical_failure"] is not None for game in games)
    caps = sum(game["benchmark_cap"] for game in games)
    wins = draws = losses = 0
    for game in games:
        if game["technical_failure"] is not None:
            continue
        if game["benchmark_cap"] or game["winner"] is None:
            draws += 1
        elif game["winner"] == (0 if game["external_color"] == "BLACK" else 1):
            losses += 1
        else:
            wins += 1
    clean = wins + draws + losses
    return {"manifest_sha256": manifest_sha, "complete": len(games) == 20 and technical == 0, "game_count": len(games), "max_additional_plies": MAX_ADDITIONAL_PLIES, "technical_failures": technical, "capped_games": caps, "games": games, "aggregate": {"generic_chess_wins": wins, "draws": draws, "generic_chess_losses": losses, "clean_games": clean, "score": (wins + 0.5 * draws) / clean if clean else None}, "first_pass_provisional": {"generic_chess_wins": 0, "draws": 2, "generic_chess_losses": 18, "score": 0.05}}


def run_stage_b(manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = historical_source()
    fresh_a = fresh_external(source)
    fresh_g = fresh_generic(source)
    fresh: dict[str, Any] = {"manifest_sha256": manifest["manifest_sha256"], "times": TIMES, "alphasho": fresh_a, "generic_chess": fresh_g, "self_drift": {str(seconds): {"alphasho_vs_f22": fresh_a[str(seconds)]["historical_top1"], "generic_chess_vs_f22": fresh_g[str(seconds)]["historical_top1"]} for seconds in TIMES}, "modal_cross_engine_agreement": {str(seconds): sum(fresh_a[str(seconds)]["summaries"][position_id]["modal_move"] == fresh_g[str(seconds)]["summaries"][position_id]["modal_move"] for position_id in fresh_a[str(seconds)]["summaries"]) for seconds in TIMES}}
    paired = paired_match(source, manifest["manifest_sha256"])
    return fresh, paired, source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--fresh-output", type=Path, default=MOVE_REFERENCE_PATH)
    parser.add_argument("--paired-output", type=Path, default=PAIRED_PATH)
    parser.add_argument("--freeze-manifest", action="store_true")
    parser.add_argument("--stage-b", action="store_true")
    args = parser.parse_args(argv)
    if args.freeze_manifest:
        manifest = freeze_manifest(args.manifest)
        print(json.dumps({"manifest_sha256": manifest["manifest_sha256"], "harness_sha256": manifest["harness"]["sha256"]}, sort_keys=True))
        return 0
    if args.stage_b:
        manifest = load_manifest(args.manifest)
        fresh, paired, source = run_stage_b(manifest)
        fresh["historical_source"] = source
        fresh["manifest_sha256"] = manifest["manifest_sha256"]
        args.fresh_output.write_text(json.dumps(fresh, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        args.paired_output.write_text(json.dumps(paired, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"manifest_sha256": manifest["manifest_sha256"], "fresh_050": fresh["alphasho"]["0.5"]["complete"] and fresh["generic_chess"]["0.5"]["complete"], "fresh_200": fresh["alphasho"]["2.0"]["complete"] and fresh["generic_chess"]["2.0"]["complete"], "paired": paired["complete"], "aggregate": paired["aggregate"]}, sort_keys=True))
        return 0
    parser.error("choose --freeze-manifest or --stage-b")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
