"""Build V3 with independently certified generic PREFERENCE_STRONG roots."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_f23b_evaluator_corpus as f23b
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts.exact_generic_preference_solver import solve_root

V1 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json"
SOLVER_VERSION = "f23e-exact-generic-preference-solver-v1"


def _rows(n: int, pieces: dict[tuple[int, int], str]) -> list[str]:
    board = [["."] * n for _ in range(n)]
    for (file, rank), piece in pieces.items():
        if board[rank][file] != ".":
            raise ValueError(f"overlap {(file, rank)}")
        board[rank][file] = piece
    return ["".join(board[rank]) for rank in range(n - 1, -1, -1)]


def _orthogonal(n: int, m: dict[str, Any], tid: str = "R"):
    rays = tuple(m["RayAtom"](direction) for direction in ((0, 1), (0, -1), (1, 0), (-1, 0)))
    return m["make_compiled"](n, [m["king"](), m["T"](tid, *rays), m["T"]("D")], max_ply=1)


def _bishop_knight(n: int, m: dict[str, Any]):
    bishop = m["T"]("B", *(m["RayAtom"](direction) for direction in ((1, 1), (1, -1), (-1, 1), (-1, -1))))
    knight = m["T"]("N", *(m["LeapAtom"](offset) for offset in ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))))
    return m["make_compiled"](n, [m["king"](), bishop, knight, m["T"]("D")], max_ply=1)


def _knights(n: int, m: dict[str, Any]):
    knight = m["T"]("N", *(m["LeapAtom"](offset) for offset in ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))))
    return m["make_compiled"](n, [m["king"](), knight, m["T"]("D")], max_ply=1)


def _drop_lance(n: int, m: dict[str, Any]):
    lance = m["T"]("L", m["RayAtom"]((0, -1)))
    knight = m["T"]("N", *(m["LeapAtom"](offset) for offset in ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))))
    return m["make_compiled"](n, [m["king"](), lance, knight, m["T"]("D")], max_ply=1)


def _variant_rows(family: str, variant: int, n: int) -> tuple[list[str], tuple[list, list]]:
    if family == "orthogonal":
        pieces = {(0, 0): "k", (2, 0): "K", (1, n - 4): "R", (n - 1, 1): "R"}
        dead = ((n - 1, n - 1), (n - 2, n - 1), (n - 1, n - 2), (n - 2, n - 2), (n - 3, n - 1), (n - 1, n - 3))[variant]
        pieces[dead] = "D"
        return _rows(n, pieces), ([], [])
    if family == "bishop_knight":
        pieces = {(0, 0): "k", (2, 1): "K", (0, 2): "B", (2, 2): "N"}
        dead = ((n - 1, n - 1), (n - 2, n - 1), (n - 1, n - 2), (n - 2, n - 2), (n - 3, n - 1), (n - 1, n - 3))[variant]
        pieces[dead] = "D"
        return _rows(n, pieces), ([], [])
    if family == "knights":
        pieces = {(0, 0): "k", (2, 1): "K", (2, 4): "N", (2, 2): "N"}
        dead = ((n - 1, n - 1), (n - 2, n - 1), (n - 1, n - 2), (n - 2, n - 2), (n - 3, n - 1), (n - 1, n - 3))[variant]
        pieces[dead] = "D"
        return _rows(n, pieces), ([], [])
    if family == "drop_lance":
        pieces = {(0, 0): "k", (2, 1): "K", (2, 2): "N"}
        dead = ((n - 1, n - 1), (n - 2, n - 1), (n - 1, n - 2), (n - 2, n - 2), (n - 3, n - 1), (n - 1, n - 3))[variant]
        pieces[dead] = "D"
        return _rows(n, pieces), ([('L', 1)], [])
    raise ValueError(family)


def _case_specs(m: dict[str, Any]) -> list[dict[str, Any]]:
    configs = (
        ("orthogonal", "strong-ray-8x8", 8, _orthogonal, "R"),
        ("bishop_knight", "strong-bishop-knight-7x7", 7, _bishop_knight, "B"),
        ("knights", "strong-knight-6x6", 6, _knights, "N"),
        ("drop_lance", "strong-drop-lance-8x8", 8, _drop_lance, "L"),
    )
    out = []
    for family, ruleset_id, n, compile_fn, _tid in configs:
        compiled = compile_fn(n, m)
        for variant in range(6):
            rows, hands = _variant_rows(family, variant, n)
            state = m["make_state"](compiled, rows, hands=hands)
            result = solve_root(compiled, state, max_nodes=5000, max_depth=1)
            if not result.strong:
                raise RuntimeError(f"REFERENCE_SOLVE_UNRESOLVED:{family}:{variant}:{result.unresolved_reason}")
            out.append({
                "id": f"generic-strong-{family}-{variant}",
                "ruleset_id": ruleset_id,
                "family": "exact_game_theoretic_preference",
                "label_kind": "exact_game_theoretic_optimal_set",
                "reference_authority": "complete bounded exact GenericChess game-theoretic solver",
                "reference_authority_class": "exact terminal minimax",
                "source": f"fixture:{family}-mate-or-draw-construction",
                "state": f23b.state_spec(state, m),
                "state_object": state,
                "compiled": compiled,
                "solver": {"kind": "exact_root_wdl", "version": SOLVER_VERSION, "max_nodes": 5000, "max_depth": 1},
                "result": result,
            })
    return out


def _identity(case: dict[str, Any], m: dict[str, Any]) -> str:
    payload = {"ruleset_id": case["ruleset_id"], "state": case["state"], "label_kind": case["label_kind"]}
    return hashlib.sha256(m["canonical_json"](payload).encode("utf-8")).hexdigest()


def _supervision_class(entry: dict[str, Any]) -> str:
    if entry.get("label_kind") == "exact_game_theoretic_optimal_set":
        return "PREFERENCE_STRONG"
    if entry.get("label_kind") == "terminal_mate_in_one":
        return "PREFERENCE_WEAK"
    return "STRUCTURAL_ONLY"


def build_corpus() -> dict[str, Any]:
    m = f23c._imports()
    v1_bytes, v2_bytes = V1.read_bytes(), V2.read_bytes()
    v1, v2 = json.loads(v1_bytes), json.loads(v2_bytes)
    if v2["generic_exact"][: len(v1["generic_exact"])] != v1["generic_exact"]:
        raise RuntimeError("V1_PREFIX_MISMATCH")
    strong_cases = []
    for case in _case_specs(m):
        result = case["result"]
        identity = _identity(case, m)
        optimal = list(result.optimal_actions)
        strong_cases.append({
            "id": case["id"], "ruleset_id": case["ruleset_id"], "family": case["family"],
            "label_kind": case["label_kind"], "reference_authority": case["reference_authority"],
            "reference_authority_class": case["reference_authority_class"], "source": case["source"],
            "solver": case["solver"], "state": case["state"], "state_identity_sha256": identity,
            "split": "HOLDOUT" if int(identity[:8], 16) % 4 == 0 else "DEVELOPMENT",
            "supervision_class": "PREFERENCE_STRONG",
            "preference_authority": {
                "root_actor": case["state"]["side_to_move"], "root_value": result.root_value,
                "legal_root_action_count": len(result.action_values),
                "optimal_root_actions": optimal, "all_root_action_values": list(result.action_values),
                "states_expanded": result.stats["states_expanded"], "terminal_leaves": result.stats["terminal_leaves"],
                "cycle_edges": result.stats["cycle_edges"], "cap_hits": result.stats["cap_hits"],
                "unresolved": result.stats["unresolved"], "solver_version": SOLVER_VERSION,
            },
            "label": {"reference_actions": optimal, "diagnostic_reference_action": optimal[0]},
        })
    generic = copy.deepcopy(v2["generic_exact"]) + strong_cases
    identities = [entry["state_identity_sha256"] for entry in generic]
    if len(identities) != len(set(identities)):
        raise RuntimeError("V3_CANONICAL_DUPLICATE")
    classes = {entry["id"]: (entry.get("supervision_class") or _supervision_class(entry)) for entry in generic}
    dev = sum(entry["split"] == "DEVELOPMENT" for entry in generic)
    holdout = sum(entry["split"] == "HOLDOUT" for entry in generic)
    strong_dev = [entry for entry in generic if entry["split"] == "DEVELOPMENT" and classes[entry["id"]] == "PREFERENCE_STRONG"]
    rulesets = {entry["ruleset_id"] for entry in strong_dev}
    if len(strong_dev) < 10 or len([entry for entry in generic if entry["split"] == "HOLDOUT" and classes[entry["id"]] == "PREFERENCE_STRONG"]) < 3:
        raise RuntimeError("STRONG_SPLIT_MINIMUM_NOT_MET")
    if max(Counter(entry["ruleset_id"] for entry in strong_dev).values()) > len(strong_dev) / 2:
        raise RuntimeError("STRONG_RULESET_DOMINANCE")
    return {
        "schema_version": 3, "corpus_id": "evaluator-v2-corpus-v3",
        "source_v1_fixture": str(V1.relative_to(ROOT)).replace("\\", "/"),
        "source_v2_fixture": str(V2.relative_to(ROOT)).replace("\\", "/"),
        "source_v1_sha256": hashlib.sha256(v1_bytes).hexdigest(),
        "source_v2_sha256": hashlib.sha256(v2_bytes).hexdigest(),
        "frozen_legacy_f22": copy.deepcopy(v2["frozen_legacy_f22"]),
        "generic_exact": generic,
        "supervision_classes": classes,
        "sampling": {"feature_blind": True, "algorithm": "copy V2; deterministic four-ruleset strong roots with max_ply=1; split after canonical deduplication", "deduplication": "sha256(canonical ruleset_id/state/label_kind)"},
        "split": {"algorithm": v2["split"]["algorithm"], "frozen_before_fitting": True, "development_count": dev, "holdout_count": holdout},
        "coverage": {"generic_positions_v2": len(v2["generic_exact"]), "generic_positions_added_v3": len(strong_cases), "generic_positions": len(generic), "strong_development": len(strong_dev), "strong_holdout": sum(entry["split"] == "HOLDOUT" and classes[entry["id"]] == "PREFERENCE_STRONG" for entry in generic), "strong_rulesets": sorted(rulesets), "strong_ruleset_count": len(rulesets)},
        "production_changed": False, "alpha_sho_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus = build_corpus()
    args.output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "added": corpus["coverage"]["generic_positions_added_v3"], "strong_dev": corpus["coverage"]["strong_development"], "strong_holdout": corpus["coverage"]["strong_holdout"], "rulesets": corpus["coverage"]["strong_ruleset_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
