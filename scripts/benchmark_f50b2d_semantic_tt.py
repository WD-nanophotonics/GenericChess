"""F50B2D semantic Native transposition-table benchmark.

Raw JSON belongs outside Git; this script writes only the caller-selected
measurement file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from generic_chess.native.semantic import (
    position_key,
    semantic_iterative_search,
)
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.rules.compiler import compile_semantic_ruleset

sys.path.insert(0, str(Path(__file__).parent))
from benchmark_f50b2b_semantic_runtime import (  # noqa: E402
    _case_specs,
    _midgames,
    _pack_initial,
)


TT_SIZES_MB = (0, 64, 256, 512)


@dataclass
class Measurement:
    case: str
    position_index: int
    position_key: str
    legal_plies: int
    tt_megabytes: int
    wall_seconds: float
    reported_search_seconds: float
    score: int
    best_action: int | None
    principal_variation: tuple[int, ...]
    nodes: int
    nps: float
    completed_depth: int
    tt_status: str
    tt_allocated_bytes: int
    tt_entry_bytes: int
    tt_occupied_entries: int
    tt_probes: int
    tt_hits: int
    tt_exact_hits: int
    tt_cutoffs: int
    tt_stores: int
    tt_replacements: int
    tt_collisions: int
    tt_previous_iteration_hits: int
    tt_current_iteration_hits: int


def _measure(case, index, position, legal_plies, depth, tt_megabytes):
    started = time.perf_counter()
    result = semantic_iterative_search(
        case.native, position, depth, tt_megabytes=tt_megabytes
    )
    wall = time.perf_counter() - started
    return Measurement(
        case=case.name,
        position_index=index,
        position_key=position_key(case.native, position),
        legal_plies=legal_plies,
        tt_megabytes=tt_megabytes,
        wall_seconds=wall,
        reported_search_seconds=result["elapsed_seconds"],
        score=result["score"],
        best_action=result["best_action"],
        principal_variation=result["principal_variation"],
        nodes=result["nodes"],
        nps=result["nodes"] / wall if wall else 0.0,
        completed_depth=result["completed_depth"],
        tt_status=result["tt_status"],
        tt_allocated_bytes=result["tt_allocated_bytes"],
        tt_entry_bytes=result["tt_entry_bytes"],
        tt_occupied_entries=result["tt_occupied_entries"],
        tt_probes=result["tt_probes"],
        tt_hits=result["tt_hits"],
        tt_exact_hits=result["tt_exact_hits"],
        tt_cutoffs=result["tt_cutoffs"],
        tt_stores=result["tt_stores"],
        tt_replacements=result["tt_replacements"],
        tt_collisions=result["tt_collisions"],
        tt_previous_iteration_hits=result["tt_previous_iteration_hits"],
        tt_current_iteration_hits=result["tt_current_iteration_hits"],
    )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--midgame-plies", type=int, default=24)
    parser.add_argument("--variants", type=int, default=2)
    parser.add_argument(
        "--cases", default="western,shogi_without_declarations",
        help="comma-separated cases from the F50B2B benchmark fixture",
    )
    args = parser.parse_args(argv)
    selected = frozenset(args.cases.split(","))
    measurements = []
    parity = []
    for name, ruleset in _case_specs():
        if name not in selected:
            continue
        semantic = compile_semantic_ruleset(ruleset)
        native = compile_native_semantic_rules(semantic)
        positions = _midgames(
            native, _pack_initial(semantic, native),
            variants=args.variants, plies=args.midgame_plies,
        )
        case = type("BenchmarkCase", (), {"name": name, "native": native})
        for index, position in enumerate(positions):
            reference = _measure(case, index, position, args.midgame_plies,
                                 args.depth, 0)
            measurements.append(asdict(reference))
            for size in TT_SIZES_MB[1:]:
                result = _measure(case, index, position, args.midgame_plies,
                                  args.depth, size)
                measurements.append(asdict(result))
                parity.append({
                    "case": name, "position_index": index,
                    "tt_megabytes": size,
                    "same_score_action_pv": (
                        result.score, result.best_action,
                        result.principal_variation,
                    ) == (
                        reference.score, reference.best_action,
                        reference.principal_variation,
                    ),
                })
    report = {
        "schema": "F50B2D-SEMANTIC-TT-BENCHMARK-V1",
        "depth": args.depth,
        "midgame_plies": args.midgame_plies,
        "variants": args.variants,
        "tt_sizes_megabytes": TT_SIZES_MB,
        "logical_cpus": os.cpu_count(),
        "measurements": measurements,
        "parity": parity,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "schema": report["schema"],
        "parity_all": all(row["same_score_action_pv"] for row in parity),
        "rows": [{
            "case": row["case"],
            "position_index": row["position_index"],
            "tt_megabytes": row["tt_megabytes"],
            "wall_seconds": row["wall_seconds"],
            "nodes": row["nodes"],
            "nps": row["nps"],
            "tt_hits": row["tt_hits"],
            "tt_cutoffs": row["tt_cutoffs"],
            "previous_iteration_hits": row["tt_previous_iteration_hits"],
        } for row in measurements],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
