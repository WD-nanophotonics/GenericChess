"""Read-only bridge to the local AlphaSho repository (external positive
control for Learning Phase 1.8).

This module never writes into the AlphaSho repository: it only reads git
state, source files, documentation and (optionally) executes the AlphaSho
venv python for cshogi version detection.  All Phase 1.8 artifacts are
written under GenericChess's own ``artifacts/`` tree.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
from pathlib import Path

from .shogi_rules import CSHOGI_INDEX, HAND_ORDER


ALPHASHO_ROOT = Path(
    os.environ.get(
        "GC_ALPHASHO_ROOT",
        r"C:\Users\icywo\PycharmProjects\alphasho",
    )
)
LEGACY_REL = Path("benchmarks") / "legacy_3262cc8.py"
CURRENT_EVAL_REL = Path("src") / "alphasho" / "heuristicplayer" / "evaluation.py"
BENCHMARK_DOC_REL = Path("docs") / "ABP_BENCHMARK.md"


def alphasho_available() -> bool:
    return ALPHASHO_ROOT.is_dir() and (ALPHASHO_ROOT / ".git").is_dir()


def alphasho_python() -> Path | None:
    candidates = (
        ALPHASHO_ROOT / ".venv" / "Scripts" / "python.exe",
        ALPHASHO_ROOT / ".venv" / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _git_capture(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ALPHASHO_ROOT), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def capture_repo_state() -> dict:
    """HEAD, branch and porcelain status of the AlphaSho working tree."""
    return {
        "head": _git_capture("rev-parse", "HEAD"),
        "branch": _git_capture("branch", "--show-current"),
        "status_porcelain": _git_capture("status", "--porcelain"),
    }


def _python_env() -> dict:
    py = alphasho_python()
    if py is None:
        return {"python": None, "cshogi": None, "error": "no venv python found"}
    try:
        version = subprocess.run(
            [str(py), "-c", "import sys; print(sys.version.split()[0])"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
        cshogi = subprocess.run(
            [
                str(py),
                "-c",
                "import cshogi; print(getattr(cshogi, '__version__', 'unknown'))",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        ).stdout.strip()
        return {"python": version, "cshogi": cshogi}
    except Exception as exc:
        return {
            "python": None,
            "cshogi": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def extract_legacy_material() -> dict:
    """AST-extract material tables from the frozen legacy benchmark copy."""
    path = ALPHASHO_ROOT / LEGACY_REL
    if not path.exists():
        raise FileNotFoundError(f"legacy benchmark not found: {path}")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    values: dict[str, object] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in ("PIECE_VALUES", "HAND_VALUES", "SOURCE_COMMIT")
        ):
            try:
                values[node.targets[0].id] = ast.literal_eval(node.value)
            except Exception:
                values[node.targets[0].id] = None
    check_match = re.search(r"score\s*-\s*(\d+)\s*if\s+board\.is_check\(\)", source)
    return {
        "source_file": str(path),
        "source_commit": values.get("SOURCE_COMMIT"),
        "piece_values": values.get("PIECE_VALUES"),
        "hand_values": values.get("HAND_VALUES"),
        "nonmaterial_terms": {
            "check_penalty": int(check_match.group(1)) if check_match else None,
            "note": (
                "the legacy evaluator is material + a -35 check penalty; "
                "this is recorded as EVALUATOR_NONMATERIAL_DELTA and is not "
                "representable in the GenericChess material-table framework"
            ),
        },
    }


def current_evaluator_terms() -> dict:
    """Extra non-material terms in the current (non-legacy) evaluator."""
    path = ALPHASHO_ROOT / CURRENT_EVAL_REL
    if not path.exists():
        return {"present": False}
    source = path.read_text(encoding="utf-8")
    constants: dict[str, object] = {}
    for name in (
        "PIECE_VALUES",
        "HAND_VALUES",
        "CHECK_PENALTY",
        "TEMPO_BONUS",
        "MAX_POSITIONAL",
        "MAX_MOBILITY",
        "MAX_KING_SAFETY",
    ):
        match = re.search(rf"^{name}\s*=\s*(.+)$", source, re.MULTILINE)
        if match:
            try:
                constants[name] = ast.literal_eval(match.group(1))
            except Exception:
                constants[name] = match.group(1).strip()
    return {
        "present": True,
        "constants": constants,
        "extra_terms": [
            "piece-square",
            "mobility",
            "king_safety",
            "check_penalty",
            "tempo",
        ],
    }


def benchmark_protocol_summary() -> dict:
    path = ALPHASHO_ROOT / BENCHMARK_DOC_REL
    if not path.exists():
        return {"present": False}
    lines = path.read_text(encoding="utf-8").splitlines()[:40]
    return {
        "present": True,
        "doc": str(path),
        "head": lines,
        "protocol": {
            "seconds_per_move": [1, 5],
            "positions": 10,
            "max_plies": 256,
            "paired_colors": True,
            "unresolved_excluded_from_score": True,
            "fallback_and_timing_invalid_excluded": True,
        },
    }


def human_material_reference(compiled) -> dict:
    """Map AlphaSho legacy values to GenericChess shogi type ids."""
    legacy = extract_legacy_material()
    piece_values = legacy["piece_values"]
    hand_values = legacy["hand_values"]
    board: dict[str, int] = {}
    hand: dict[str, int] = {}
    for tid, cshogi_idx in CSHOGI_INDEX.items():
        if tid == "K":
            continue  # anchor: excluded from the material table
        board[tid] = piece_values[cshogi_idx]
        if tid in ("P", "L", "N", "S", "G", "B", "R"):
            hand[tid] = hand_values[HAND_ORDER[tid]]
    return {
        "schema_version": 1,
        "source_commit": legacy["source_commit"],
        "board_value_by_type": board,
        "hand_value_by_base_type": hand,
        "nonmaterial_delta": legacy["nonmaterial_terms"],
    }


def audit_alphasho(compiled) -> dict:
    if not alphasho_available():
        return {"available": False, "error": "AlphaSho repository not found"}
    return {
        "available": True,
        "root": str(ALPHASHO_ROOT),
        "repo_state": capture_repo_state(),
        "python_env": _python_env(),
        "legacy": extract_legacy_material(),
        "current_evaluator": current_evaluator_terms(),
        "benchmark_protocol": benchmark_protocol_summary(),
        "distinction": {
            "legacy": (
                "frozen material+check-penalty negamax with TT, iterative "
                "deepening and capture ordering (commit 3262cc8)"
            ),
            "current_full": (
                "material + PST + mobility + king safety + check penalty + "
                "tempo, plus mature ABP profiles (PVS/aspiration, SEE, LMR, "
                "null move, qsearch)"
            ),
        },
    }


def assert_alphasho_unchanged(before: dict) -> dict:
    after = capture_repo_state()
    return {
        "before": before,
        "after": after,
        "unchanged": before == after,
        "note": (
            "AlphaSho repository is read-only for Phase 1.8; unchanged "
            "means HEAD, branch and porcelain status are identical."
        ),
    }
