"""Build the compact, provenance-safe F23B evaluator diagnostic corpus.

F23B is corpus work only.  Reference labels come either from the preserved
F22 artifact (read-only) or from bounded exact legality/terminal solvers over
small generic rulesets.  No evaluator score participates in sampling or
labeling.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

F22_COMMIT = "3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38"
F22_CORPUS_PATH = "artifacts/f22_post_f21_rebaseline_strength/round5_frozen_positions.json"
F22_REFERENCE_PATH = "artifacts/f22_post_f21_rebaseline_strength/alphasho_reference_provenance.json"


def _imports():
    from generic_chess.core.actions import BoardMove, DropMove, action_to_dict
    from generic_chess.core.attacks import is_in_check
    from generic_chess.core.coordinates import index_to_square
    from generic_chess.core.movement import RayAtom
    from generic_chess.core.movegen import _apply_action_unchecked, legal_actions_from_position
    from generic_chess.core.position import Hands, Position
    from generic_chess.core.semantic_executor import _semantic_public_action, semantic_engine_for
    from generic_chess.core.terminal import TerminalStatus
    from generic_chess.core.transition import apply_action, initial_state
    from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset
    from generic_chess.learning.shogi_rules import sfen_to_gc_state
    from generic_chess.rules.compiler import compile_ruleset, compile_semantic_ruleset
    from generic_chess.rules.schema import canonical_json
    from generic_chess.rules.ir import CompiledSemanticRuleset
    from conftest import make_position, make_ruleset, make_state, T, king_type
    from ai_fixtures import build_mate
    from test_promotion import _promo_compiled
    from rule_semantics_ir_fixtures import nifu_ruleset
    from phase19b3_s4_fixtures import forbidden_no_reply_drop_ruleset

    return locals()


def _git_show(path: str) -> Any:
    import subprocess

    result = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{F22_COMMIT}:{path}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(result.stdout)


def recover_f22_stratum() -> dict[str, Any]:
    corpus = _git_show(F22_CORPUS_PATH)
    refs = _git_show(F22_REFERENCE_PATH)
    positions = corpus["positions"]
    references = refs["references"]
    if len(positions) != 10 or len(references) != 10:
        raise RuntimeError("F22_PROVENANCE_COUNT_MISMATCH")
    return {
        "source_commit": F22_COMMIT,
        "source_artifact": F22_CORPUS_PATH,
        "reference_artifact": F22_REFERENCE_PATH,
        "positions": positions,
        "references": references,
        "reference_authority": "preserved AlphaSho move at frozen F22 state",
    }


def _piece_char(piece) -> str:
    char = piece.current_type_id
    if len(char) != 1:
        raise ValueError(f"generic fixture serialization needs one-character type ids: {char}")
    return char.upper() if piece.owner == 0 else char.lower()


def state_spec(state, m: dict[str, Any]) -> dict[str, Any]:
    n = len(state.position.board) ** 0.5
    if int(n) != n:
        raise ValueError("non-square position")
    n = int(n)
    rows = []
    for rank in range(n - 1, -1, -1):
        rows.append(
            "".join(
                "." if (piece := state.position.board[rank * n + file]) is None else _piece_char(piece)
                for file in range(n)
            )
        )
    return {
        "board_size": n,
        "rows": rows,
        "side_to_move": state.position.side_to_move,
        "hands": [
            [[type_id, count] for type_id, count in state.position.hands[0].counts],
            [[type_id, count] for type_id, count in state.position.hands[1].counts],
        ],
    }


def _action_key(action) -> tuple:
    if hasattr(action, "from_square"):
        return (
            "board",
            action.from_square.file,
            action.from_square.rank,
            action.to_square.file,
            action.to_square.rank,
            action.promotion_target_id,
        )
    return ("drop", action.base_type_id, action.to_square.file, action.to_square.rank)


def _public_actions(compiled, position, m: dict[str, Any]):
    engine = m["semantic_engine_for"](compiled)
    if engine is not None:
        rows = []
        for action, binding in engine.iter_legal_action_bindings(position):
            public = m["_semantic_public_action"](engine, action)
            rows.append((public, engine._transition(position, action, binding)))
        return tuple(rows)
    return tuple(
        (action, m["_apply_action_unchecked"](position, action, compiled))
        for action in m["legal_actions_from_position"](position, compiled)
    )


def _exact_mate_in_one(compiled, state, m: dict[str, Any]) -> list[Any]:
    actor = state.position.side_to_move
    winners = []
    for action, _child_position in _public_actions(compiled, state.position, m):
        child = m["apply_action"](state, action, compiled)
        if (
            child.terminal_status.status is m["TerminalStatus"].CHECKMATE
            and child.terminal_status.winner == actor
        ):
            winners.append(action)
    return winners


def _forced_promotions(compiled, state, m: dict[str, Any]) -> list[Any]:
    actions = _public_actions(compiled, state.position, m)
    promoted = [action for action, _child in actions if action.promotion_target_id is not None]
    if not promoted:
        raise RuntimeError("FORCED_PROMOTION_CASE_HAS_NO_PROMOTION_ACTION")
    unpromoted_same_destination = {
        (action.from_square, action.to_square)
        for action, _child in actions
        if hasattr(action, "from_square") and action.promotion_target_id is None
    }
    if any((action.from_square, action.to_square) in unpromoted_same_destination for action in promoted):
        raise RuntimeError("PROMOTION_CASE_IS_NOT_FORCED")
    return promoted


def _semantic_suppression(compiled, state, m: dict[str, Any]) -> dict[str, Any]:
    engine = m["semantic_engine_for"](compiled)
    if engine is None:
        raise RuntimeError("SEMANTIC_CASE_DID_NOT_COMPILE_SEMANTICALLY")
    semantic = {_action_key(action) for action, _child in _public_actions(compiled, state.position, m)}
    legacy = m["compile_ruleset"]
    legacy_compiled = legacy(replace(m["nifu_ruleset"](), semantic_actions=()))
    legacy_position = m["Position"](
        board=state.position.board,
        hands=state.position.hands,
        side_to_move=state.position.side_to_move,
        ruleset_fingerprint=legacy_compiled.ruleset_fingerprint,
        aux_state=state.position.aux_state,
    )
    legacy_keys = {_action_key(action) for action in m["legal_actions_from_position"](legacy_position, legacy_compiled)}
    suppressed = [list(item) for item in sorted(legacy_keys - semantic, key=str)]
    added = [list(item) for item in sorted(semantic - legacy_keys, key=str)]
    if not suppressed:
        raise RuntimeError("SEMANTIC_SUPPRESSION_CASE_HAS_NO_SUPPRESSED_ACTION")
    return {"suppressed_actions": suppressed, "added_actions": added}


def _generic_strata(m: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    ray = m["build_mate"](2)
    ray_state = m["initial_state"](ray)
    cases.append({
        "id": "generic-ray-mate-in-one",
        "ruleset_id": "legacy-ray-8x8",
        "family": "checking_anchor_pressure",
        "label_kind": "terminal_mate_in_one",
        "solver": {"kind": "mate_in_one", "max_nodes": 128},
        "state": state_spec(ray_state, m),
        "compiled": ray,
        "state_object": ray_state,
    })

    down_ray = m["T"]("R", m["RayAtom"]((0, -1)))
    drop = m["compile_ruleset"](m["make_ruleset"](8, [m["king_type"](), down_ray], auto_drop=False))
    # The canonical test position places the two anchors on ranks 1 and 0.
    drop_state = m["make_state"](
        drop,
        ["........", "........", "........", "........", "........", "........", "..K.....", "k......."],
        hands=([("R", 1)], []),
    )
    cases.append({
        "id": "generic-drop-mate-in-one",
        "ruleset_id": "legacy-drop-ray-8x8",
        "family": "drops_hands",
        "label_kind": "terminal_mate_in_one",
        "solver": {"kind": "mate_in_one", "max_nodes": 256},
        "state": state_spec(drop_state, m),
        "compiled": drop,
        "state_object": drop_state,
    })

    promo = m["_promo_compiled"]()
    promotion_cases = (
        ("pawn", [".......k", "....P...", "........", "........", "........", "........", "........", "K......."]),
        ("lance", [".......k", "....L...", "........", "........", "........", "........", "........", "K......."]),
        ("knight", [".......k", "........", "........", "....N...", "........", "........", "........", "K......."]),
    )
    for name, rows in promotion_cases:
        state = m["make_state"](promo, rows)
        cases.append({
            "id": f"generic-promotion-{name}",
            "ruleset_id": "legacy-promotion-8x8",
            "family": "promotion_structure",
            "label_kind": "forced_promotion_actions",
            "solver": {"kind": "forced_promotion", "max_nodes": 256},
            "state": state_spec(state, m),
            "compiled": promo,
            "state_object": state,
        })

    semantic_base = m["nifu_ruleset"]()
    semantic = m["compile_semantic_ruleset"](semantic_base)
    for file_no in (4, 3):
        rows = [".......k"] + ["........"] * 6 + ["K......."]
        row = list(rows[-2])
        row[file_no] = "P"
        rows[-2] = "".join(row)
        state = m["make_state"](semantic, rows, hands=([("P", 1)], []))
        cases.append({
            "id": f"generic-semantic-file-guard-{file_no}",
            "ruleset_id": "semantic-file-guard-8x8",
            "family": "semantic_constraint_effect",
            "label_kind": "semantic_suppression_set",
            "solver": {"kind": "semantic_suppression", "max_nodes": 512},
            "state": state_spec(state, m),
            "compiled": semantic,
            "state_object": state,
        })

    # S4 fixture: the exact label is the semantic legal-action set after the
    # bounded no-reply postcondition, not an evaluator preference.
    s4_ruleset = m["forbidden_no_reply_drop_ruleset"]()
    s4 = m["compile_semantic_ruleset"](s4_ruleset)
    s4_state = m["make_state"](
        s4,
        [".......k", ".......P", "........", "........", "........", "........", "........", "K......."],
        hands=([("P", 1)], []),
    )
    cases.append({
        "id": "generic-semantic-s4-no-reply-filter",
        "ruleset_id": "semantic-s4-drop-8x8",
        "family": "semantic_constraint_effect",
        "label_kind": "semantic_legal_action_set",
        "solver": {"kind": "semantic_legal_set", "max_nodes": 512},
        "state": state_spec(s4_state, m),
        "compiled": s4,
        "state_object": s4_state,
    })
    return cases


def _solve_case(case: dict[str, Any], m: dict[str, Any]) -> dict[str, Any]:
    kind = case["solver"]["kind"]
    compiled, state = case["compiled"], case["state_object"]
    if kind == "mate_in_one":
        actions = _exact_mate_in_one(compiled, state, m)
        if not actions:
            raise RuntimeError(f"{case['id']} has no exact mate-in-one action")
        result = {"reference_actions": [m["action_to_dict"](action) for action in actions]}
    elif kind == "forced_promotion":
        result = {"reference_actions": [m["action_to_dict"](action) for action in _forced_promotions(compiled, state, m)]}
    elif kind == "semantic_suppression":
        result = _semantic_suppression(compiled, state, m)
    elif kind == "semantic_legal_set":
        result = {"reference_actions": [m["action_to_dict"](action) for action, _ in _public_actions(compiled, state.position, m)]}
    else:
        raise RuntimeError(f"unknown exact solver {kind}")
    # This is a deterministic observation child for the F23A feature probe.
    # It is selected from the exact legal set, never from evaluator scores.
    legal = _public_actions(compiled, state.position, m)
    if legal:
        result["diagnostic_reference_action"] = m["action_to_dict"](legal[0][0])
    return result


def _stable_identity(case: dict[str, Any], m: dict[str, Any]) -> str:
    payload = {
        "ruleset_id": case["ruleset_id"],
        "state": case["state"],
        "label_kind": case["label_kind"],
    }
    return hashlib.sha256(m["canonical_json"](payload).encode("utf-8")).hexdigest()


def build_corpus() -> dict[str, Any]:
    m = _imports()
    f22 = recover_f22_stratum()
    generic_cases = _generic_strata(m)
    output_cases = []
    for case in generic_cases:
        result = _solve_case(case, m)
        identity = _stable_identity(case, m)
        split = "HOLDOUT" if int(identity[:8], 16) % 4 == 0 else "DEVELOPMENT"
        output_cases.append({
            "id": case["id"],
            "ruleset_id": case["ruleset_id"],
            "family": case["family"],
            "label_kind": case["label_kind"],
            "reference_authority": "bounded exact GenericChess legality/terminal solver",
            "solver": case["solver"],
            "state": case["state"],
            "state_identity_sha256": identity,
            "split": split,
            "label": result,
        })
    return {
        "schema_version": 1,
        "corpus_id": "evaluator-v2-corpus-v1",
        "sampling": {
            "feature_blind": True,
            "algorithm": "preserve F22; generic cases selected by provenance/rule-family coverage and exact-solver availability",
            "deduplication": "sha256(canonical ruleset_id/state/label_kind)",
        },
        "frozen_legacy_f22": f22,
        "generic_exact": output_cases,
        "split": {
            "algorithm": "HOLDOUT iff int(state_identity_sha256[:8], 16) mod 4 == 0; otherwise DEVELOPMENT",
            "frozen_before_fitting": True,
            "development_count": sum(case["split"] == "DEVELOPMENT" for case in output_cases),
            "holdout_count": sum(case["split"] == "HOLDOUT" for case in output_cases),
        },
        "coverage": {
            "shogi_positions_available": len(f22["positions"]),
            "shogi_positions_added": 0,
            "generic_positions": len(output_cases),
            "generic_rulesets": len({case["ruleset_id"] for case in output_cases}),
            "families": sorted({case["family"] for case in output_cases}),
        },
        "production_changed": False,
        "alpha_sho_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus = build_corpus()
    args.output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "shogi": corpus["coverage"]["shogi_positions_available"], "generic": corpus["coverage"]["generic_positions"], "split": corpus["split"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
