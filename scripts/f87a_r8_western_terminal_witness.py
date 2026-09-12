"""F87A-R8 minimal Western terminal-witness evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_chess.benchmark.qualification import initial_state, semantic_engine_for, semantic_public_actions
from generic_chess.core.actions import action_to_dict
from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


BASELINE_SHA = "8fbf24a475b8390b8a4d27a6dd489d4567bb7dd1"
ARTIFACT_DIR = Path("artifacts/f87a_r8_western_terminal_witness")
MOVES = (
    ((4, 1), (4, 3)),
    ((4, 6), (4, 4)),
    ((5, 0), (2, 3)),
    ((1, 7), (2, 5)),
    ((3, 0), (7, 4)),
    ((6, 7), (5, 5)),
    ((7, 4), (5, 6)),
)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(output_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    engine = semantic_engine_for(compiled)
    state = initial_state(compiled)
    rows = []
    for ply, (source, target) in enumerate(MOVES, start=1):
        action = next(
            action
            for action in semantic_public_actions(engine, state.position)
            if action_to_dict(action).get("from") == list(source)
            and action_to_dict(action).get("to") == list(target)
        )
        state = apply_action(state, action, compiled)
        rows.append({
            "ply": ply,
            "action": action_to_dict(action),
            "terminal_status": state.terminal_status.status.value,
            "winner": state.terminal_status.winner,
        })
    result = {
        "schema_version": 1,
        "experiment": "GENERICCHESS-F87A-R8-WESTERN-TERMINAL-WITNESS",
        "status": "RESULT_COMPLETE",
        "baseline_sha": BASELINE_SHA,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "plies": len(rows),
        "rows": rows,
        "terminal_status": state.terminal_status.status.value,
        "winner": state.terminal_status.winner,
        "natural_legal_witness": True,
        "dynamic_viability_pass": False,
        "qualification_effect": "TERMINATION_RUNTIME_WITNESS_ONLY_NOT_DYNAMIC_VIABILITY_PASS",
        "external_engine_used": False,
        "training_steps": 0,
    }
    _write_json(output_dir / "manifest.json", {
        "schema_version": 1,
        "experiment": result["experiment"],
        "status": "PREP_FROZEN",
        "baseline_sha": BASELINE_SHA,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "move_count": len(MOVES),
        "witness": "standard_legal_scholars_mate_from_builtin_western_initial_position",
        "dynamic_viability_pass": False,
    })
    _write_json(output_dir / "results.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
