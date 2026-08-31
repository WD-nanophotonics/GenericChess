"""F30 read-only AlphaSho reference re-entry audit.

This audit deliberately keeps the external AlphaSho checkout out of the
GenericChess process.  It records identity with a per-command safe-directory
override, runs the frozen F22 replay against the current product, and invokes
the current AlphaSho heuristic entry point in a subprocess without asking it
to write artifacts.
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
ALPHASHO_ROOT = Path(
    __import__("os").environ.get(
        "GC_ALPHASHO_ROOT", r"C:\Users\icywo\PycharmProjects\alphasho"
    )
).resolve()
ALPHA_PY = ALPHASHO_ROOT / ".venv" / "Scripts" / "python.exe"
F22_COMMIT = "3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38"
F22_PATHS = {
    "positions": "artifacts/f22_post_f21_rebaseline_strength/round5_frozen_positions.json",
    "provenance": "artifacts/f22_post_f21_rebaseline_strength/alphasho_reference_provenance.json",
    "agreement": "artifacts/f22_post_f21_rebaseline_strength/alphasho_move_agreement.json",
}
DESCRIPTOR_PATH = ROOT / "tests" / "fixtures" / "f25_standard_shogi_position_descriptors.json"
FROZEN_BUDGETS = (128, 256, 512, 1024, 2048)
REFERENCE_SECONDS = 0.50


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", f"-c", f"safe.directory={ALPHASHO_ROOT}", "-C", str(ALPHASHO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_show(path: str) -> bytes:
    return subprocess.run(
        ["git", f"-c", f"safe.directory={ROOT}", "-C", str(ROOT), "show", f"{F22_COMMIT}:{path}"],
        check=True,
        capture_output=True,
    ).stdout


def environment_manifest() -> dict[str, Any]:
    files = (
        "benchmarks/heuristic_strength.py",
        "benchmarks/legacy_3262cc8.py",
        "src/alphasho/heuristicplayer/player.py",
        "src/alphasho/heuristicplayer/search.py",
        "src/alphasho/heuristicplayer/evaluation.py",
    )
    checkpoint = ALPHASHO_ROOT / "artifacts" / "checkpoints" / "best.pt"
    versions = subprocess.run(
        [str(ALPHA_PY), "-c", "import sys; print(sys.version); import cshogi, torch; print('cshogi='+getattr(cshogi, '__version__', 'unknown')); print('torch='+torch.__version__); print('cuda='+str(torch.cuda.is_available()))"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    cshogi_version = next((x.split("=", 1)[1] for x in versions if x.startswith("cshogi=")), None)
    if cshogi_version == "unknown":
        metadata = subprocess.run(
            [str(ALPHA_PY), "-c", "from importlib.metadata import version; print(version('cshogi'))"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        cshogi_version = metadata or cshogi_version
    return {
        "alphasho_root": str(ALPHASHO_ROOT),
        "repo": {
            "head": _git("rev-parse", "HEAD"),
            "branch": _git("branch", "--show-current"),
            "status_porcelain": _git("status", "--porcelain"),
            "origin": _git("remote", "get-url", "origin"),
        },
        "python": {
            "executable": str(ALPHA_PY),
            "raw_version": versions[0] if versions else None,
            "cshogi": cshogi_version,
            "torch": next((x.split("=", 1)[1] for x in versions if x.startswith("torch=")), None),
            "cuda": next((x.split("=", 1)[1] for x in versions if x.startswith("cuda=")), None),
        },
        "entry_point": {
            "kind": "AlphaSho current heuristic full profile",
            "module": "benchmarks.heuristic_strength",
            "class": "alphasho.heuristicplayer.HeuristicPlayer",
            "profile": "FULL",
            "seconds_per_move": REFERENCE_SECONDS,
        },
        "source_sha256": {
            path: _sha((ALPHASHO_ROOT / path).read_bytes()) for path in files
        },
        "checkpoint": {
            "path": str(checkpoint),
            "present": checkpoint.is_file(),
            "sha256": _sha(checkpoint.read_bytes()) if checkpoint.is_file() else None,
            "used_by_entry_point": False,
        },
        "audit_host": {"python": platform.python_version()},
    }


def historical_source() -> dict[str, Any]:
    raw = {name: _git_show(path) for name, path in F22_PATHS.items()}
    positions = json.loads(raw["positions"])["positions"]
    provenance = json.loads(raw["provenance"])
    return {
        "source_commit": F22_COMMIT,
        "source_sha256": {name: _sha(value) for name, value in raw.items()},
        "positions": positions,
        "references": provenance["references"],
        "reference_count": provenance["reference_count"],
    }


def _generic_replay(source: dict[str, Any]) -> dict[str, Any]:
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
    current = json.loads(DESCRIPTOR_PATH.read_text(encoding="utf-8"))["positions"]
    if [(x["position_id"], x["sfen"]) for x in current] != [
        (x["name"], x["sfen"]) for x in source["positions"]
    ]:
        raise AssertionError("F22 source positions differ from current frozen descriptors")
    legal_rows = []
    for position in current:
        state = sfen_to_gc_state(compiled, position["sfen"])
        legal = {
            gc_action_to_usi(action)
            for action in __import__("generic_chess.core.movegen", fromlist=["legal_actions"]).legal_actions(state, compiled)
        }
        reference_move = source["references"][position["position_id"]]
        legal_rows.append({"position_id": position["position_id"], "reference_move": reference_move, "legal": reference_move in legal, "legal_move_count": len(legal)})
    if not all(row["legal"] for row in legal_rows):
        raise AssertionError("historical AlphaSho reference move is illegal in current product")

    rows = []
    for position in current:
        state = sfen_to_gc_state(compiled, position["sfen"])
        for budget in FROZEN_BUDGETS:
            repeats = []
            for _ in range(2):
                provider = NativeSemanticLegalityProvider.try_create(compiled)
                player = AlphaBetaPlayer(
                    compiled,
                    evaluation_config=EvaluationConfig(),
                    use_disk_cache=False,
                    use_tt=True,
                    use_ordering=True,
                    use_native_semantic_legality=provider is not None,
                    tuning=SearchTuning(),
                )
                started = time.perf_counter()
                session = GameSession(compiled)
                session._state = state
                session._search_history_witnesses = (state.position,)
                decision = player.choose_action(
                    session,
                    SearchLimits(max_nodes=budget, max_depth=8, quiescence_max_depth=4, quiescence_hard_max_depth=8, deterministic=True),
                )
                elapsed = time.perf_counter() - started
                repeats.append({
                    "selected_move": gc_action_to_usi(decision.action) if decision.action else None,
                    "reference_move": source["references"][position["position_id"]],
                    "reference_top1": bool(decision.action and gc_action_to_usi(decision.action) == source["references"][position["position_id"]]),
                    "score": decision.score,
                    "total_nodes": decision.nodes + decision.qnodes,
                    "completed_depth": decision.completed_depth,
                    "termination_reason": decision.termination_reason,
                    "elapsed_seconds": elapsed,
                })
            rows.append({
                "position_id": position["position_id"],
                "budget": budget,
                "repeats": repeats,
                "deterministic": all(
                    repeats[0][key] == repeats[1][key]
                    for key in (
                        "selected_move",
                        "reference_move",
                        "reference_top1",
                        "score",
                        "total_nodes",
                        "completed_depth",
                        "termination_reason",
                    )
                ),
            })
    return {"legal_reference_moves": legal_rows, "budgets": list(FROZEN_BUDGETS), "runs": rows, "all_deterministic": all(x["deterministic"] for x in rows)}


_EXTERNAL_CODE = r'''
import json, sys, time
from pathlib import Path
root = Path(sys.argv[1]); sys.path[:0] = [str(root / "src"), str(root)]
from benchmarks.heuristic_strength import _choose, _thinking, _tuning, AblationProfile
from alphasho.engine import ShogiGame
payload = json.loads(sys.stdin.read())
rows = []
for item in payload:
    for repeat in range(3):
        game = ShogiGame(item["sfen"])
        player = __import__("alphasho.heuristicplayer", fromlist=["HeuristicPlayer"]).HeuristicPlayer(_thinking(0.5), _search_tuning=_tuning(AblationProfile.FULL))
        move, elapsed = _choose(player, game)
        info = player.last_search_info
        rows.append({"position_id": item["position_id"], "repeat": repeat, "selected_move": move.usi, "elapsed_seconds": elapsed, "completed_depth": info.max_depth, "used_fallback": bool(info.used_fallback), "nodes": info.playouts})
print(json.dumps(rows, sort_keys=True))
'''


_EXTERNAL_MATCH_CODE = r'''
import json, sys
from pathlib import Path
root = Path(sys.argv[1]); sys.path[:0] = [str(root / "src"), str(root)]
from benchmarks.heuristic_strength import _choose, _thinking, _tuning, AblationProfile
from alphasho.engine import ShogiGame
from alphasho.heuristicplayer import HeuristicPlayer
for line in sys.stdin:
    item = json.loads(line)
    try:
        game = ShogiGame(item["sfen"])
        player = HeuristicPlayer(_thinking(0.5), _search_tuning=_tuning(AblationProfile.FULL))
        move, elapsed = _choose(player, game)
        info = player.last_search_info
        print(json.dumps({"ok": True, "selected_move": move.usi, "elapsed_seconds": elapsed, "completed_depth": info.max_depth, "used_fallback": bool(info.used_fallback), "nodes": info.playouts}), flush=True)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}), flush=True)
'''


def fresh_external(source: dict[str, Any]) -> dict[str, Any]:
    if not ALPHA_PY.is_file():
        return {"complete": False, "reason": "ALPHASHO_PYTHON_MISSING", "runs": []}
    payload = [{"position_id": x["position_id"], "sfen": x["sfen"]} for x in json.loads(DESCRIPTOR_PATH.read_text(encoding="utf-8"))["positions"]]
    result = subprocess.run([str(ALPHA_PY), "-c", _EXTERNAL_CODE, str(ALPHASHO_ROOT)], input=json.dumps(payload), capture_output=True, text=True, check=True, timeout=600)
    runs = json.loads(result.stdout)
    for row in runs:
        row["reference_move"] = source["references"][row["position_id"]]
        row["reference_top1"] = row["selected_move"] == row["reference_move"]
    grouped = {}
    for row in runs:
        grouped.setdefault(row["position_id"], []).append(row)
    return {"complete": len(runs) == 30, "seconds_per_move": REFERENCE_SECONDS, "repeat_count": 3, "runs": runs, "modal_move_by_position": {key: max({move: sum(r["selected_move"] == move for r in values) for move in {r["selected_move"] for r in values}}, key=lambda move: sum(r["selected_move"] == move for r in values)) for key, values in grouped.items()}, "stable_positions": sum(len({r["selected_move"] for r in values}) == 1 for values in grouped.values())}


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
    rows = []
    for item in json.loads(DESCRIPTOR_PATH.read_text(encoding="utf-8"))["positions"]:
        state = sfen_to_gc_state(compiled, item["sfen"])
        for repeat in range(3):
            provider = NativeSemanticLegalityProvider.try_create(compiled)
            session = GameSession(compiled)
            session._state = state
            session._search_history_witnesses = (state.position,)
            player = AlphaBetaPlayer(compiled, evaluation_config=EvaluationConfig(), use_disk_cache=False, use_tt=True, use_ordering=True, use_native_semantic_legality=provider is not None, tuning=SearchTuning())
            started = time.perf_counter()
            decision = player.choose_action(session, SearchLimits(max_time_seconds=REFERENCE_SECONDS, max_depth=64, quiescence_max_depth=4, quiescence_hard_max_depth=8, deterministic=True))
            elapsed = time.perf_counter() - started
            move = gc_action_to_usi(decision.action) if decision.action else None
            rows.append({"position_id": item["position_id"], "repeat": repeat, "selected_move": move, "reference_move": source["references"][item["position_id"]], "reference_top1": move == source["references"][item["position_id"]], "elapsed_seconds": elapsed, "completed_depth": decision.completed_depth, "total_nodes": decision.nodes + decision.qnodes, "termination_reason": decision.termination_reason})
    grouped = {}
    for row in rows:
        grouped.setdefault(row["position_id"], []).append(row)
    return {"complete": len(rows) == 30, "seconds_per_move": REFERENCE_SECONDS, "repeat_count": 3, "runs": rows, "modal_move_by_position": {key: max({move: sum(r["selected_move"] == move for r in values) for move in {r["selected_move"] for r in values}}, key=lambda move: sum(r["selected_move"] == move for r in values)) for key, values in grouped.items()}, "stable_positions": sum(len({r["selected_move"] for r in values}) == 1 for values in grouped.values())}


def paired_match(source: dict[str, Any]) -> dict[str, Any]:
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.limits import SearchLimits
    from generic_chess.learning.shogi_rules import gc_action_to_usi, gc_to_sfen, sfen_to_gc_state, usi_to_gc_action
    from generic_chess.core.position import HistoryRecord
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
    from generic_chess.session.session import GameSession

    if not ALPHA_PY.is_file():
        return {"complete": False, "game_count": 0, "technical_failures": 20, "reason": "ALPHASHO_PYTHON_MISSING", "games": []}
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    positions = json.loads(DESCRIPTOR_PATH.read_text(encoding="utf-8"))["positions"]
    process = subprocess.Popen([str(ALPHA_PY), "-u", "-c", _EXTERNAL_MATCH_CODE, str(ALPHASHO_ROOT)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    games = []
    technical_failures = 0
    try:
        for item in positions:
            for external_color in (0, 1):
                session = GameSession(compiled)
                seeded = sfen_to_gc_state(compiled, item["sfen"])
                state = replace(
                    seeded,
                    ply_count=0,
                    history=(HistoryRecord(seeded.repetition_counts[0][0], -1, "", False),),
                )
                session._state = state
                session._search_history_witnesses = (state.position,)
                moves = []
                failure = None
                for ply in range(256):
                    if session.result.status.value != "ongoing":
                        break
                    actor = session.state.position.side_to_move
                    try:
                        if actor == external_color:
                            assert process.stdin is not None and process.stdout is not None
                            process.stdin.write(json.dumps({"sfen": gc_to_sfen(session.state, compiled)}) + "\n")
                            process.stdin.flush()
                            response = json.loads(process.stdout.readline())
                            if not response.get("ok"):
                                raise RuntimeError(response.get("error", "AlphaSho move failed"))
                            usi = response["selected_move"]
                            action = usi_to_gc_action(compiled, session.state, usi)
                            legal_by_usi = {gc_action_to_usi(candidate): candidate for candidate in session.legal_actions()}
                            action = legal_by_usi.get(usi)
                            if action is None:
                                raise RuntimeError(f"external move is not legal in GenericChess: {usi}")
                        else:
                            provider = NativeSemanticLegalityProvider.try_create(compiled)
                            player = AlphaBetaPlayer(compiled, evaluation_config=EvaluationConfig(), use_disk_cache=False, use_tt=True, use_ordering=True, use_native_semantic_legality=provider is not None, tuning=SearchTuning())
                            decision = player.choose_action(session, SearchLimits(max_time_seconds=REFERENCE_SECONDS, max_depth=64, quiescence_max_depth=4, quiescence_hard_max_depth=8, deterministic=True))
                            action = decision.action
                            usi = gc_action_to_usi(action) if action else None
                            if action is None or action not in session.legal_actions():
                                raise RuntimeError("GenericChess returned no legal action")
                        session.submit(action)
                        moves.append(usi)
                    except Exception as exc:
                        failure = {"ply": ply, "actor": actor, "error": f"{type(exc).__name__}: {exc}"}
                        technical_failures += 1
                        break
                result = session.result
                games.append({"position_id": item["position_id"], "external_color": "BLACK" if external_color == 0 else "WHITE", "played_plies": len(moves), "moves_sha256": _sha(" ".join(moves).encode()), "status": result.status.value if failure is None else "technical_failure", "winner": result.winner, "failure": failure})
    finally:
        if process.stdin is not None:
            process.stdin.close()
        process.terminate()
        process.wait(timeout=10)
    return {"complete": len(games) == 20 and technical_failures == 0, "game_count": len(games), "max_plies": 256, "seconds_per_move": REFERENCE_SECONDS, "technical_failures": technical_failures, "games": games}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-fresh", action="store_true")
    parser.add_argument("--fresh-only", action="store_true")
    parser.add_argument("--paired-only", action="store_true")
    parser.add_argument("--refresh-environment", action="store_true")
    args = parser.parse_args(argv)
    if args.refresh_environment:
        result = json.loads(args.output.read_text(encoding="utf-8"))
        result["environment"] = environment_manifest()
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"alphasho_head": result["environment"]["repo"]["head"], "cshogi": result["environment"]["python"]["cshogi"], "status": result["status"]}, sort_keys=True))
        return 0
    if args.paired_only:
        result = json.loads(args.output.read_text(encoding="utf-8"))
        paired = paired_match(result["historical_reference"])
        result["paired_benchmark"] = paired
        result["flags"]["ALPHASHO_PAIRED_BENCHMARK_COMPLETE"] = bool(paired.get("complete"))
        result["flags"]["STANDARD_SHOGI_EXTERNAL_STRENGTH_BASELINE_FROZEN"] = bool(paired.get("complete"))
        result["next_boundary"] = "F31_STANDARD_SHOGI_PAIRED_EXTERNAL_BENCHMARK" if paired.get("complete") else "F30A_ALPHASHO_EXTERNAL_ENVIRONMENT_RECOVERY"
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "games": paired.get("game_count", 0), "technical_failures": paired.get("technical_failures", 0), "next": result["next_boundary"]}, sort_keys=True))
        return 0
    if args.fresh_only:
        result = json.loads(args.output.read_text(encoding="utf-8"))
        source = result["historical_reference"]
        fresh = fresh_external(source)
        fresh_gc = fresh_generic(source)
        result["fresh_alphasho"] = fresh
        result["fresh_generic_chess"] = fresh_gc
        result["flags"]["ALPHASHO_EXTERNAL_REFERENCE_REPRODUCIBLE"] = bool(result["environment"]["repo"]["status_porcelain"] == "" and fresh.get("complete"))
        result["flags"]["ALPHASHO_FRESH_MOVE_REFERENCE_COMPLETE"] = bool(fresh.get("complete") and fresh_gc.get("complete"))
        result["next_boundary"] = "F30A_ALPHASHO_EXTERNAL_ENVIRONMENT_RECOVERY" if not result["flags"]["ALPHASHO_FRESH_MOVE_REFERENCE_COMPLETE"] else "F31_STANDARD_SHOGI_PAIRED_EXTERNAL_BENCHMARK"
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "historical": result["flags"]["F22_HISTORICAL_REFERENCE_REPLAY_COMPLETE"], "fresh": result["flags"]["ALPHASHO_FRESH_MOVE_REFERENCE_COMPLETE"], "next": result["next_boundary"]}, sort_keys=True))
        return 0
    env = environment_manifest()
    source = historical_source()
    replay = _generic_replay(source)
    fresh = {"complete": False, "reason": "SKIPPED", "runs": []} if args.skip_fresh else fresh_external(source)
    result = {
        "schema_version": 1,
        "status": "PASS" if replay["all_deterministic"] and all(x["legal"] for x in replay["legal_reference_moves"]) else "FAIL",
        "generic_chess_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
        "standard_shogi_fingerprint": __import__("generic_chess.rules.schema", fromlist=["compute_fingerprint"]).compute_fingerprint(__import__("generic_chess.rules.standard_shogi", fromlist=["build_standard_shogi_ruleset"]).build_standard_shogi_ruleset()),
        "environment": env,
        "historical_reference": source,
        "historical_replay": replay,
        "fresh_alphasho": fresh,
        "fresh_generic_chess": {"complete": False, "reason": "SKIPPED", "runs": []},
        "flags": {
            "ALPHASHO_EXTERNAL_REFERENCE_REPRODUCIBLE": bool(env["repo"]["status_porcelain"] == "" and fresh.get("complete")),
            "F22_HISTORICAL_REFERENCE_REPLAY_COMPLETE": bool(replay["all_deterministic"] and all(x["legal"] for x in replay["legal_reference_moves"])),
            "ALPHASHO_FRESH_MOVE_REFERENCE_COMPLETE": bool(fresh.get("complete")),
            "ALPHASHO_PAIRED_BENCHMARK_COMPLETE": False,
            "STANDARD_SHOGI_EXTERNAL_STRENGTH_BASELINE_FROZEN": False,
        },
        "next_boundary": "F30A_ALPHASHO_EXTERNAL_ENVIRONMENT_RECOVERY" if not fresh.get("complete") else "F31_STANDARD_SHOGI_PAIRED_EXTERNAL_BENCHMARK",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "historical": result["flags"]["F22_HISTORICAL_REFERENCE_REPLAY_COMPLETE"], "fresh": result["flags"]["ALPHASHO_FRESH_MOVE_REFERENCE_COMPLETE"], "next": result["next_boundary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
