"""Build the bounded, feature-blind F23C evaluator diagnostic corpus.

F23C extends the F23B artifact without rewriting it.  New labels are either
exact legal-action sets or exact terminal outcomes from small generic games;
no evaluator value is consulted while selecting or labeling a case.
"""

from __future__ import annotations

import argparse
import copy
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

from scripts import build_f23b_evaluator_corpus as f23b

V1_FIXTURE = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"


def _imports():
    from generic_chess.core.actions import action_to_dict
    from generic_chess.core.attacks import pseudo_attacks
    from generic_chess.core.movement import LeapAtom, RayAtom
    from generic_chess.core.pieces import Piece
    from generic_chess.core.transition import apply_action
    from generic_chess.rules.compiler import compile_semantic_ruleset
    from generic_chess.rules.schema import canonical_json
    from ai_fixtures import king, rook
    from conftest import T, make_compiled, make_state
    from rule_semantics_ir_fixtures import cannon_ruleset, nifu_ruleset

    return locals()


def _rows(n: int, pieces: dict[tuple[int, int], str]) -> list[str]:
    board = [["."] * n for _ in range(n)]
    for (file, rank), piece in pieces.items():
        if board[rank][file] != ".":
            raise ValueError(f"overlapping fixture square {(file, rank)}")
        board[rank][file] = piece
    return ["".join(board[rank]) for rank in range(n - 1, -1, -1)]


def _ray_compiled(n: int, m: dict[str, Any]):
    return m["make_compiled"](n, [m["king"](), m["rook"](), m["T"]("D")])


def _mate_rows(n: int, *, victim: bool) -> list[str]:
    pieces = {
        (0, 0): "k",
        (2, 0): "K",
        (1, n - 4): "R",
        (n - 1, 1): "R",
    }
    if victim:
        pieces[(1, 0)] = "d"
    return _rows(n, pieces)


def _capture_recapture_rows(n: int, variant: int) -> list[str]:
    pieces = {(0, 0): "K", (n - 1, n - 1): "k", (1, 1): "R"}
    if variant == 0:
        pieces.update({(1, 3): "d", (1, 4): "r"})
    elif variant == 1:
        pieces.update({(3, 1): "d", (3, 3): "r"})
    else:
        pieces.update({(1, 2): "d", (1, 4): "r", (2, 1): "D"})
    return _rows(n, pieces)


def _drop_rows(n: int, variant: int) -> list[str]:
    pieces = {(0, 0): "K", (n - 1, n - 1): "k"}
    if variant:
        pieces.update({(1, 1): "R", (n - 2, n - 2): "r"})
    return _rows(n, pieces)


def _cannon_rows(variant: int) -> list[str]:
    # White C has one screen before the black target.  After the capture,
    # black C has one screen and can recapture the landing C.
    if variant == 0:
        files = (2, 2, 2, 2, 2, 2)
    else:
        files = (3, 3, 3, 3, 3, 3)
    pieces = {
        (0, 0): "K",
        (7, 7): "k",
        (files[0], 2): "C",
        (files[1], 3): "C",
        (files[2], 4): "c",
        (files[3], 5): "c",
        (files[4], 6): "c",
    }
    # A second distant black cannon makes the two states materially distinct
    # while preserving the same exact recapture witness.
    if variant:
        pieces[(6, 4)] = "c"
    return _rows(8, pieces)


def _nifu_rows(file_no: int) -> list[str]:
    pieces = {(0, 0): "K", (7, 7): "k", (file_no, 1): "P"}
    return _rows(8, pieces)


def _public_actions(compiled, state, m: dict[str, Any]):
    engine = f23b._imports()["semantic_engine_for"](compiled)
    if engine is not None:
        rows = []
        for action, binding in engine.iter_legal_action_bindings(state.position):
            public = f23b._imports()["_semantic_public_action"](engine, action)
            rows.append((public, engine._transition(state.position, action, binding)))
        return tuple(rows)
    return tuple(
        (action, f23b._imports()["_apply_action_unchecked"](state.position, action, compiled))
        for action in f23b._imports()["legal_actions_from_position"](state.position, compiled)
    )


def _is_capture(position, action, n: int) -> bool:
    if not hasattr(action, "to_square") or not hasattr(action, "from_square"):
        return False
    target = position.board[action.to_square.rank * n + action.to_square.file]
    return target is not None and target.owner != position.side_to_move


def _recapture_witness(compiled, state, action, m: dict[str, Any]) -> bool:
    child = m["apply_action"](state, action, compiled)
    n = compiled.board_size
    target = (action.to_square.file, action.to_square.rank)
    for reply, _position in _public_actions(compiled, child, m):
        if not _is_capture(child.position, reply, n):
            continue
        if (reply.to_square.file, reply.to_square.rank) == target:
            return True
    return False


def _event_evidence(compiled, state, actions, m: dict[str, Any]) -> dict[str, Any]:
    n = compiled.board_size
    captures = [action for action in actions if _is_capture(state.position, action, n)]
    recaptures = [action for action in captures if _recapture_witness(compiled, state, action, m)]
    legacy = getattr(compiled, "_legacy_compiled", compiled)
    maps = m["pseudo_attacks"](state.position, 0, legacy), m["pseudo_attacks"](state.position, 1, legacy)
    defended = []
    for action in captures:
        idx = action.to_square.rank * n + action.to_square.file
        target = state.position.board[idx]
        if target is not None and action.to_square in maps[target.owner]:
            defended.append(action)
    drops = [action for action in actions if not hasattr(action, "from_square")]
    return {
        "capture_action_count": len(captures),
        "recapture_witness_count": len(recaptures),
        "defended_capture_count": len(defended),
        "drop_action_count": len(drops),
        "legal_action_count": len(actions),
    }


def _exact_mate_actions(compiled, state, m: dict[str, Any]):
    terminal = f23b._imports()
    actor = state.position.side_to_move
    winners = []
    for action, _child_position in _public_actions(compiled, state, m):
        child = m["apply_action"](state, action, compiled)
        if child.terminal_status.status is terminal["TerminalStatus"].CHECKMATE and child.terminal_status.winner == actor:
            winners.append(action)
    return winners


def _exact_legal_set(compiled, state, m: dict[str, Any]):
    return [action for action, _child in _public_actions(compiled, state, m)]


def _case(case_id, ruleset_id, family, label_kind, solver, compiled, state, *, source, event_tags, m):
    actions = _exact_mate_actions(compiled, state, m) if solver["kind"] == "mate_in_one" else _exact_legal_set(compiled, state, m)
    if not actions:
        raise RuntimeError(f"{case_id} has no exact reference actions")
    evidence = _event_evidence(compiled, state, actions, m)
    if "capture" in event_tags and evidence["capture_action_count"] == 0:
        raise RuntimeError(f"{case_id} lost its capture event")
    if "recapture" in event_tags and evidence["recapture_witness_count"] == 0:
        raise RuntimeError(f"{case_id} lost its recapture witness")
    if "drop" in event_tags and evidence["drop_action_count"] == 0:
        raise RuntimeError(f"{case_id} lost its drop event")
    diagnostic = next((action for action in actions if _is_capture(state.position, action, compiled.board_size)), actions[0])
    if "recapture" in event_tags:
        diagnostic = next(action for action in actions if _recapture_witness(compiled, state, action, m))
    return {
        "id": case_id,
        "ruleset_id": ruleset_id,
        "family": family,
        "label_kind": label_kind,
        "reference_authority": "exact GenericChess legal-action or terminal-outcome solver",
        "reference_authority_class": "exact one-ply terminal outcome" if solver["kind"] == "mate_in_one" else "exact legal-action set",
        "solver": solver,
        "source": source,
        "event_tags": sorted(event_tags),
        "event_evidence": evidence,
        "state": f23b.state_spec(state, m),
        "compiled": compiled,
        "state_object": state,
        "diagnostic_action": diagnostic,
    }


def _new_case_specs(m: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for n, suffix in ((8, "8x8"), (6, "6x6")):
        compiled = _ray_compiled(n, m)
        for victim, kind in ((True, "capture"), (False, "quiet")):
            state = m["make_state"](compiled, _mate_rows(n, victim=victim))
            tags = {"anchor", "attack_defense"}
            if victim:
                tags.add("capture")
            cases.append(_case(
                f"generic-{suffix}-mate-{kind}", f"legacy-ray-{suffix}",
                "anchor_check_pressure", "terminal_mate_in_one",
                {"kind": "mate_in_one", "max_nodes": 256, "max_depth": 1},
                compiled, state, source="fixture:ray-mate-construction", event_tags=tags, m=m,
            ))

    compiled5 = _ray_compiled(5, m)
    for variant in range(3):
        state = m["make_state"](compiled5, _capture_recapture_rows(5, variant))
        cases.append(_case(
            f"generic-ray-5x5-capture-recapture-{variant}", "legacy-ray-5x5",
            "capture_recapture_pressure", "exact_legal_action_set",
            {"kind": "legal_set", "max_nodes": 512, "max_depth": 0},
            compiled5, state, source="fixture:ray-capture-recapture-construction",
            event_tags={"capture", "recapture", "attack_defense"}, m=m,
        ))

    compiled_drop = _ray_compiled(5, m)
    for variant in (0, 1):
        state = m["make_state"](compiled_drop, _drop_rows(5, variant), hands=([("R", 1)], []))
        cases.append(_case(
            f"generic-ray-5x5-drop-mobility-{variant}", "legacy-drop-ray-5x5",
            "hand_drop_pressure", "exact_legal_action_set",
            {"kind": "legal_set", "max_nodes": 512, "max_depth": 0},
            compiled_drop, state, source="fixture:generic-drop-mobility-construction",
            event_tags={"drop", "mobility"}, m=m,
        ))

    compiled_cannon = m["compile_semantic_ruleset"](m["cannon_ruleset"]())
    for variant in (0, 1):
        state = m["make_state"](compiled_cannon, _cannon_rows(variant))
        cases.append(_case(
            f"generic-cannon-8x8-recapture-{variant}", "semantic-cannon-8x8",
            "capture_recapture_pressure", "exact_legal_action_set",
            {"kind": "legal_set", "max_nodes": 1024, "max_depth": 0},
            compiled_cannon, state, source="fixture:semantic-cannon-recapture-construction",
            event_tags={"capture", "recapture", "attack_defense", "semantic"}, m=m,
        ))

    semantic = m["compile_semantic_ruleset"](m["nifu_ruleset"]())
    for file_no in (1, 6):
        state = m["make_state"](semantic, _nifu_rows(file_no), hands=([("P", 1)], []))
        cases.append(_case(
            f"generic-semantic-nifu-r2-{file_no}", "semantic-file-guard-8x8-r2",
            "semantic_constraint_effect", "exact_legal_action_set",
            {"kind": "legal_set", "max_nodes": 1024, "max_depth": 0},
            semantic, state, source="fixture:semantic-file-guard-variant",
            event_tags={"semantic", "drop"}, m=m,
        ))
    return cases


def _identity(case: dict[str, Any], m: dict[str, Any]) -> str:
    payload = {"ruleset_id": case["ruleset_id"], "state": case["state"], "label_kind": case["label_kind"]}
    return hashlib.sha256(m["canonical_json"](payload).encode("utf-8")).hexdigest()


def _serialize_case(case: dict[str, Any], m: dict[str, Any]) -> dict[str, Any]:
    actions = _exact_mate_actions(case["compiled"], case["state_object"], m) if case["solver"]["kind"] == "mate_in_one" else _exact_legal_set(case["compiled"], case["state_object"], m)
    label = {
        "reference_actions": [m["action_to_dict"](action) for action in actions],
        "diagnostic_reference_action": m["action_to_dict"](case["diagnostic_action"]),
    }
    identity = _identity(case, m)
    return {
        "id": case["id"], "ruleset_id": case["ruleset_id"], "family": case["family"],
        "label_kind": case["label_kind"], "reference_authority": case["reference_authority"],
        "reference_authority_class": case["reference_authority_class"], "solver": case["solver"],
        "source": case["source"], "event_tags": case["event_tags"], "event_evidence": case["event_evidence"],
        "state": case["state"], "state_identity_sha256": identity,
        "split": "HOLDOUT" if int(identity[:8], 16) % 4 == 0 else "DEVELOPMENT", "label": label,
    }


def build_corpus() -> dict[str, Any]:
    m = _imports()
    v1_bytes = V1_FIXTURE.read_bytes()
    v1 = json.loads(v1_bytes)
    if v1["corpus_id"] != "evaluator-v2-corpus-v1":
        raise RuntimeError("F23C_V1_CORPUS_ID_MISMATCH")
    old_cases = copy.deepcopy(v1["generic_exact"])
    new_cases = [_serialize_case(case, m) for case in _new_case_specs(m)]
    all_cases = old_cases + new_cases
    identities = [case["state_identity_sha256"] for case in all_cases]
    if len(identities) != len(set(identities)):
        raise RuntimeError("F23C_CANONICAL_DUPLICATE")
    dev = sum(case["split"] == "DEVELOPMENT" for case in all_cases)
    holdout = sum(case["split"] == "HOLDOUT" for case in all_cases)
    return {
        "schema_version": 2,
        "corpus_id": "evaluator-v2-corpus-v2",
        "source_v1_fixture": str(V1_FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        "source_v1_sha256": hashlib.sha256(v1_bytes).hexdigest(),
        "sampling": {
            "feature_blind": True,
            "selection_inputs": ["deterministic provenance", "ruleset family", "event presence", "exact solver availability", "canonical deduplication"],
            "algorithm": "copy V1 exactly; add bounded generic event cases before split; no evaluator feature values",
            "deduplication": "sha256(canonical ruleset_id/state/label_kind)",
            "near_duplicate_guard": "canonical identity uniqueness; mirrored/renamed variants are invariance-tested controls only",
        },
        "frozen_legacy_f22": copy.deepcopy(v1["frozen_legacy_f22"]),
        "generic_exact": all_cases,
        "split": {
            "algorithm": v1["split"]["algorithm"], "frozen_before_fitting": True,
            "development_count": dev, "holdout_count": holdout,
        },
        "coverage": {
            "shogi_positions_available": len(v1["frozen_legacy_f22"]["positions"]),
            "shogi_positions_added": 0,
            "generic_positions_v1": len(old_cases), "generic_positions_added_r2": len(new_cases),
            "generic_positions": len(all_cases), "generic_rulesets": len({case["ruleset_id"] for case in all_cases}),
            "families": sorted({case["family"] for case in all_cases}),
            "event_tags": sorted({tag for case in new_cases for tag in case["event_tags"]}),
        },
        "production_changed": False, "alpha_sho_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus = build_corpus()
    args.output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "generic": corpus["coverage"]["generic_positions"], "added": corpus["coverage"]["generic_positions_added_r2"], "split": corpus["split"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
