"""Learning Phase 1.8: AlphaSho positive control and learning-direction audit.

Executes the pre-registered stage chain:

    A. read-only AlphaSho audit
    B. GenericChess shogi ruleset construction (generic schema)
    C. cshogi rule parity (curated + large)
    D/E. static material geometry + TD scale decomposition
    (F-J are blocked when SHOGI_RULE_PARITY = FAIL, per the phase gates)
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from ..ai.evaluation.config import EvaluationConfig
from ..ai.evaluation.profile import build_ruleset_profile
from .alphasho_bridge import (
    assert_alphasho_unchanged,
    audit_alphasho,
    capture_repo_state,
    human_material_reference,
)
from .diagnostics import _gen0_checkpoint, load_checkpoints_from_experiment
from .leverage import TimingRecorder, merge_performance
from .shogi_rules import (
    SHOGI_MODEL_GAPS,
    build_shogi_ruleset,
    compare_sfen_parity,
    curated_parity_cases,
    gc_to_sfen,
    generate_reachable_sfens,
    shogi_ruleset_meta,
    sfen_to_gc_state,
)
from .serialization import canonical_json, stable_sha256


PHASE18_SCHEMA_VERSION = 1
PROJECT_VERSION = "0.8.0a5"
NATIVE_VERSION = "0.3.0"

# Pre-registered thresholds (fixed before measurements).
SCALE_DOMINANT_THRESHOLD = 0.75
SCALE_SUBSTANTIAL_THRESHOLD = 0.40
MATERIAL_COSINE_CLOSE = 0.90
MATERIAL_COSINE_SEVERE = 0.50

# Large parity sizes.
FULL_LARGE_PARITY_COUNT = 10_000
SMOKE_LARGE_PARITY_COUNT = 50

R2_LABEL = "R2_weird_generic"
R2_SEEDS = (7, 8, 9)


def _git_head() -> str:
    import subprocess

    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data) + "\n", encoding="utf-8")


def _meta(extra: dict | None = None) -> dict:
    out = {
        "schema_version": PHASE18_SCHEMA_VERSION,
        "gc_commit": _git_head(),
        "project_version": PROJECT_VERSION,
        "native_version": NATIVE_VERSION,
    }
    if extra:
        out.update(extra)
    return out


# ================================================================ stages


def run_audit(compiled) -> dict:
    audit = audit_alphasho(compiled)
    if not audit.get("available"):
        raise FileNotFoundError("AlphaSho repository not available for audit")
    return {**_meta(), "alphasho_audit": audit}


def run_ruleset() -> dict:
    from ..rules.compiler import compile_ruleset

    ruleset = build_shogi_ruleset()
    compiled = compile_ruleset(ruleset)
    meta = shogi_ruleset_meta(compiled)
    return {
        **_meta({"ruleset_fingerprint": compiled.ruleset_fingerprint}),
        "encoding": "generic schema v1 (no special-casing)",
        "board_size": compiled.board_size,
        "piece_types": meta["piece_types"],
        "model_gaps": SHOGI_MODEL_GAPS,
        "initial_sfen": gc_to_sfen(
            sfen_to_gc_state(
                compiled,
                "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
            ),
            compiled,
        ),
    }


def run_curated_parity(compiled) -> dict:
    results = []
    for case in curated_parity_cases():
        comparison = compare_sfen_parity(compiled, case["sfen"])
        results.append({**case, **comparison})
    return {
        **_meta({"ruleset_fingerprint": compiled.ruleset_fingerprint}),
        "cases": results,
        "pass_count": sum(1 for r in results if r["equal"]),
        "total": len(results),
    }


def run_large_parity(compiled, count: int, seed: int) -> dict:
    positions = generate_reachable_sfens(count, seed=seed)
    comparisons = []
    first_divergence: dict | None = None
    for entry in positions:
        comparison = compare_sfen_parity(compiled, entry["sfen"])
        if not comparison["equal"] and first_divergence is None:
            first_divergence = {
                "index": entry["index"],
                "game": entry["game"],
                "ply": entry["ply"],
                "sfen": entry["sfen"],
                "history": entry["history"],
                "missing_in_gc": comparison["missing_in_gc"][:5],
                "extra_in_gc": comparison["extra_in_gc"][:5],
            }
        comparisons.append(
            {
                "index": entry["index"],
                "ply": entry["ply"],
                "sfen": entry["sfen"],
                "equal": comparison["equal"],
                "gc_count": comparison["gc_legal_count"],
                "cshogi_count": comparison["cshogi_legal_count"],
            }
        )
    return {
        **_meta(
            {
                "ruleset_fingerprint": compiled.ruleset_fingerprint,
                "seed": seed,
                "count": len(comparisons),
            }
        ),
        "exact_matches": sum(1 for c in comparisons if c["equal"]),
        "divergences": sum(1 for c in comparisons if not c["equal"]),
        "first_divergence": first_divergence,
        "positions": comparisons,
    }


def _combined_vector(compiled, profile) -> dict[str, float]:
    """Board (all non-anchor types) + hand (base types) weight vector."""
    vec: dict[str, float] = {}
    for tid, value in profile.board_value_by_type.items():
        vec[f"board:{tid}"] = float(value)
    for tid, value in profile.hand_value_by_base_type.items():
        vec[f"hand:{tid}"] = float(value)
    return vec


def _human_vector(compiled, human) -> dict[str, float]:
    vec: dict[str, float] = {}
    for tid, value in human["board_value_by_type"].items():
        vec[f"board:{tid}"] = float(value)
    for tid, value in human["hand_value_by_base_type"].items():
        vec[f"hand:{tid}"] = float(value)
    return vec


def _stats(xs: list[float], ys: list[float]) -> dict:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((a - mean_x) * (b - mean_y) for a, b in zip(xs, ys))
    var_x = sum((a - mean_x) ** 2 for a in xs)
    var_y = sum((b - mean_y) ** 2 for b in ys)
    denom = math.sqrt(var_x * var_y)
    pearson = cov / denom if denom else 0.0
    rx = sorted(range(n), key=lambda i: xs[i])
    ry = sorted(range(n), key=lambda i: ys[i])
    rank_x = [0] * n
    rank_y = [0] * n
    for rank, i in enumerate(rx):
        rank_x[i] = rank
    for rank, i in enumerate(ry):
        rank_y[i] = rank
    d2 = sum((a - b) ** 2 for a, b in zip(rank_x, rank_y))
    spearman = 1.0 - 6.0 * d2 / (n * (n * n - 1)) if n > 1 else 0.0
    return {"pearson": pearson, "spearman": spearman}


def run_material_geometry(compiled, human) -> dict:
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    auto = _combined_vector(compiled, profile)
    human_vec = _human_vector(compiled, human)
    keys = sorted(set(auto) & set(human_vec))
    auto_v = [auto[k] for k in keys]
    human_v = [human_vec[k] for k in keys]
    dot = sum(a * b for a, b in zip(auto_v, human_v))
    norm_auto = math.sqrt(sum(a * a for a in auto_v))
    norm_human = math.sqrt(sum(b * b for b in human_v))
    cosine = dot / (norm_auto * norm_human) if norm_auto and norm_human else 0.0
    # best-fit positive scale c* = (auto.human)/(human.human)
    human_sq = sum(b * b for b in human_v)
    c_star = dot / human_sq if human_sq else 0.0
    scaled_human = [c_star * b for b in human_v]
    # pairwise ordering accuracy over entries with distinct human values.
    agree = 0
    pairs = 0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if human_v[i] == human_v[j]:
                continue
            pairs += 1
            if (auto_v[i] - auto_v[j]) * (human_v[i] - human_v[j]) > 0:
                agree += 1
    per_piece = []
    for k, a, h in zip(keys, auto_v, scaled_human):
        denom = abs(h) if abs(h) > 1e-9 else 1.0
        per_piece.append(
            {
                "key": k,
                "auto": round(a, 4),
                "human_scaled": round(h, 4),
                "relative_error": round(abs(a - h) / denom, 4),
            }
        )
    # board-vs-hand relationship per base type.
    board_hand = {}
    for base in ("P", "L", "N", "S", "G", "B", "R"):
        auto_b = auto.get(f"board:{base}")
        auto_h = auto.get(f"hand:{base}")
        human_b = human_vec.get(f"board:{base}")
        human_h = human_vec.get(f"hand:{base}")
        board_hand[base] = {
            "auto_board_over_hand": (
                round(auto_b / auto_h, 3) if auto_b is not None and auto_h else None
            ),
            "human_board_over_hand": (
                round(human_b / human_h, 3)
                if human_b is not None and human_h
                else None
            ),
        }
    stats = _stats(auto_v, human_v)
    return {
        **_meta({"ruleset_fingerprint": compiled.ruleset_fingerprint}),
        "dimensions": len(keys),
        "best_fit_scale": c_star,
        "cosine_similarity": cosine,
        "pearson": stats["pearson"],
        "spearman": stats["spearman"],
        "pairwise_ordering_accuracy": agree / pairs if pairs else None,
        "pairs_compared": pairs,
        "per_piece": per_piece,
        "board_vs_hand": board_hand,
    }


def run_td_scale_decomposition(compiled) -> dict:
    """Scale-direction decomposition of the frozen R2 TD updates."""
    rows: list[dict] = []
    for seed in R2_SEEDS:
        checkpoints = load_checkpoints_from_experiment(
            compiled, seed, _r2_phase15_dir(seed)
        )
        w0 = _checkpoint_vector(checkpoints[0])
        for g in range(1, len(checkpoints)):
            decomposed = decompose_scale(
                w0, _checkpoint_vector(checkpoints[g])
            )
            rows.append(
                {
                    "seed": seed,
                    "generation": g,
                    "checkpoint_id": checkpoints[g].checkpoint_id,
                    "total_delta_l2": decomposed["total_delta_l2"],
                    "scale_parallel_l2": decomposed["scale_parallel_l2"],
                    "orthogonal_l2": decomposed["orthogonal_l2"],
                    "scale_energy_fraction": decomposed["scale_energy_fraction"],
                }
            )
    mean_fraction = (
        sum(r["scale_energy_fraction"] for r in rows) / len(rows) if rows else 0.0
    )
    return {
        **_meta({"ruleset": R2_LABEL, "seeds": list(R2_SEEDS)}),
        "definition": (
            "scale component = projection of (w_g - w_0) onto the Gen0 "
            "unit weight vector; energy fraction = |parallel|^2 / |delta|^2"
        ),
        "pre_registered_thresholds": {
            "dominant": f">= {SCALE_DOMINANT_THRESHOLD}",
            "substantial": f"{SCALE_SUBSTANTIAL_THRESHOLD}..{SCALE_DOMINANT_THRESHOLD}",
            "minor": f"< {SCALE_SUBSTANTIAL_THRESHOLD}",
        },
        "rows": rows,
        "mean_scale_energy_fraction": round(mean_fraction, 6),
    }


def _checkpoint_vector(checkpoint) -> dict[str, float]:
    vec: dict[str, float] = {}
    for tid, w in checkpoint.board_weights.items():
        vec[f"board:{tid}"] = float(w)
    for tid, w in checkpoint.hand_weights.items():
        vec[f"hand:{tid}"] = float(w)
    return vec


def decompose_scale(w0: dict[str, float], w1: dict[str, float]) -> dict:
    """Decompose ``delta = w1 - w0`` into the global-scale component
    (projection onto the unit Gen0 vector) and its orthogonal complement."""
    keys = sorted(set(w0) | set(w1))
    base = {k: float(w0.get(k, 0.0)) for k in keys}
    updated = {k: float(w1.get(k, 0.0)) for k in keys}
    norm0 = math.sqrt(sum(v * v for v in base.values()))
    if norm0 <= 0.0:
        return {
            "total_delta_l2": 0.0,
            "scale_parallel_l2": 0.0,
            "orthogonal_l2": 0.0,
            "scale_energy_fraction": 0.0,
            "zero_base": True,
        }
    u = {k: v / norm0 for k, v in base.items()}
    delta = {k: updated[k] - base[k] for k in keys}
    dot = sum(delta[k] * u[k] for k in keys)
    parallel = {k: dot * u[k] for k in keys}
    orthogonal = {k: delta[k] - parallel[k] for k in keys}
    total_l2 = math.sqrt(sum(v * v for v in delta.values()))
    parallel_l2 = math.sqrt(sum(v * v for v in parallel.values()))
    orthogonal_l2 = math.sqrt(sum(v * v for v in orthogonal.values()))
    return {
        "total_delta_l2": round(total_l2, 6),
        "scale_parallel_l2": round(parallel_l2, 6),
        "orthogonal_l2": round(orthogonal_l2, 6),
        "scale_energy_fraction": (
            round(parallel_l2**2 / total_l2**2, 6) if total_l2 else 0.0
        ),
        "zero_base": False,
    }


def _r2_phase15_dir(seed: int) -> Path:
    return (
        Path("artifacts")
        / "learning_phase1_5"
        / R2_LABEL
        / f"{R2_LABEL}_seed{seed}"
    )


# ================================================================ verdicts


def verdict_parity(curated: dict, large: dict | None) -> str:
    if curated.get("pass_count", 0) < curated.get("total", 0):
        return "FAIL"
    if large is not None and large["exact_matches"] < large["count"]:
        return "FAIL"
    return "PASS"


def verdict_td_scale(scale: dict) -> str:
    mean = scale.get("mean_scale_energy_fraction", 0.0)
    if mean >= SCALE_DOMINANT_THRESHOLD:
        return "DOMINANT"
    if mean >= SCALE_SUBSTANTIAL_THRESHOLD:
        return "SUBSTANTIAL"
    return "MINOR"


def verdict_material_quality(geometry: dict) -> str:
    cosine = geometry.get("cosine_similarity")
    if cosine is None:
        return "INCONCLUSIVE"
    if cosine >= MATERIAL_COSINE_CLOSE:
        return "CLOSE_TO_HUMAN"
    if cosine >= MATERIAL_COSINE_SEVERE:
        return "MATERIAL_GAP_PRESENT"
    return "SEVERE_MATERIAL_GAP"


def final_verdict(
    audit: dict,
    parity: str,
    scale: str,
    geometry: dict,
) -> dict:
    blocked = {
        "GENERIC_SEARCH_CONTROL": "INCONCLUSIVE",
        "HUMAN_DIRECTION": "INCONCLUSIVE",
        "TD_HUMAN_DIRECTION_ALIGNMENT": "INCONCLUSIVE",
        "LEARNING_STRENGTH_SIGNAL": "INCONCLUSIVE",
        "BASIC_COMPETENCE_SANITY": "INCONCLUSIVE",
        "blocked_reason": (
            "SHOGI_RULE_PARITY = FAIL: stages F-J (search control, "
            "human-direction interpolation, random sanity, cross-engine "
            "matches, shogi training) are gated behind full rule parity"
        ),
    }
    next_phase = (
        "FIX_GENERIC_SHOGI_RULE_EXPRESSIVITY"
        if parity == "FAIL"
        else "INCONCLUSIVE"
    )
    return {
        "schema_version": PHASE18_SCHEMA_VERSION,
        "ALPHASHO_AUDIT": "PASS" if audit.get("available") else "BLOCKED",
        "SHOGI_RULE_PARITY": parity,
        "AUTO_MATERIAL_QUALITY": verdict_material_quality(geometry),
        "TD_SCALE_COMPONENT": scale,
        **blocked,
        "NEXT_PHASE_DECISION": next_phase,
    }


# ================================================================ CLI


def _r2_compiled():
    from ..ai.benchmark.audit_suite import build_compiled, standard_ruleset_specs

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    return build_compiled(specs["gen_free_random_4_102"])


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="generic_chess.learning.phase18")
    parser.add_argument("--phase", default="all")
    parser.add_argument("--artifacts", default="artifacts/learning_phase1_8")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--large-count", type=int, default=None)
    parser.add_argument("--large-seed", type=int, default=20260807)
    parser.add_argument("--alphasho", default=None)
    args = parser.parse_args(argv)

    import os

    if args.alphasho:
        os.environ["GC_ALPHASHO_ROOT"] = args.alphasho

    out = Path(args.artifacts)
    out.mkdir(parents=True, exist_ok=True)
    timings = TimingRecorder()
    smoke = args.smoke

    if not smoke:
        large_count = args.large_count or FULL_LARGE_PARITY_COUNT
    else:
        large_count = args.large_count or SMOKE_LARGE_PARITY_COUNT

    pre = capture_repo_state()
    _write(
        out / "config.json",
        {
            **_meta(),
            "mode": "smoke" if smoke else "full",
            "large_parity_count": large_count,
            "large_parity_seed": args.large_seed,
            "pre_registered_thresholds": {
                "scale_dominant": SCALE_DOMINANT_THRESHOLD,
                "scale_substantial": SCALE_SUBSTANTIAL_THRESHOLD,
                "material_cosine_close": MATERIAL_COSINE_CLOSE,
                "material_cosine_severe": MATERIAL_COSINE_SEVERE,
            },
        },
    )

    from ..rules.compiler import compile_ruleset

    phase = args.phase
    results: dict[str, Any] = {}

    if phase in ("all", "audit"):
        with timings.section("alphasho_audit"):
            shogi_compiled = compile_ruleset(build_shogi_ruleset())
            results["audit"] = run_audit(shogi_compiled)
            _write(out / "alphasho_audit.json", results["audit"])
        print("audit done")

    if phase in ("all", "ruleset"):
        with timings.section("shogi_ruleset_construction"):
            results["ruleset"] = run_ruleset()
            _write(out / "shogi_ruleset.json", results["ruleset"])
        print("ruleset done")

    if phase in ("all", "parity"):
        with timings.section("curated_parity"):
            shogi_compiled = compile_ruleset(build_shogi_ruleset())
            results["curated"] = run_curated_parity(shogi_compiled)
            _write(out / "parity_curated.json", results["curated"])
        print("curated parity done")
        with timings.section("large_parity"):
            results["large"] = run_large_parity(
                shogi_compiled, large_count, args.large_seed
            )
            _write(out / "parity_large.json", results["large"])
        print("large parity done")

    if phase in ("all", "geometry"):
        with timings.section("material_geometry"):
            shogi_compiled = compile_ruleset(build_shogi_ruleset())
            human = human_material_reference(shogi_compiled)
            _write(out / "alphasho_material_reference.json", human)
            results["geometry"] = run_material_geometry(shogi_compiled, human)
            _write(out / "material_geometry.json", results["geometry"])
        print("geometry done")

    if phase in ("all", "scale"):
        with timings.section("td_scale_decomposition"):
            r2_compiled = _r2_compiled()
            results["scale"] = run_td_scale_decomposition(r2_compiled)
            _write(out / "td_scale_decomposition.json", results["scale"])
        print("scale done")

    if phase in ("all", "final"):
        with timings.section("verdicts"):
            audit = json.loads(
                (out / "alphasho_audit.json").read_text(encoding="utf-8")
            )
            curated = json.loads(
                (out / "parity_curated.json").read_text(encoding="utf-8")
            )
            large = json.loads(
                (out / "parity_large.json").read_text(encoding="utf-8")
            )
            scale = json.loads(
                (out / "td_scale_decomposition.json").read_text(encoding="utf-8")
            )
            geometry = json.loads(
                (out / "material_geometry.json").read_text(encoding="utf-8")
            )
            verdict = final_verdict(
                audit["alphasho_audit"],
                verdict_parity(curated, large),
                verdict_td_scale(scale),
                geometry,
            )
            verdict["alphasho_unchanged"] = assert_alphasho_unchanged(pre)
            _write(out / "final_verdict.json", verdict)
            print(json.dumps(verdict, indent=2, sort_keys=True))
        print("final done")

    perf_path = out / "performance.json"
    existing = (
        json.loads(perf_path.read_text(encoding="utf-8"))
        if perf_path.exists()
        else None
    )
    _write(
        perf_path,
        merge_performance(existing, timings.to_dict()["phases"]),
    )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
