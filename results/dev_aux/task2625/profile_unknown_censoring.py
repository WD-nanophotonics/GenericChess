"""Outcome-label-blind structural profile of task2625 H=128 censored slots."""
from __future__ import annotations

from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.core.identity import position_identity_key
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2397.material import channels as material_channels

RUN = ROOT / "results/dev_aux/task2625/run"
RULES = ROOT / "results/dev_aux/task2534"
OUT = RUN / "unknown-censoring-profile.json"
EXPECTED_GAMES_SHA = "7426c7f8c1d5834a59dbd5992fcae1b19a4e05e6601e8412ccae9de0bc9123e8"
RULE_IDS = (271001, 271002, 271003, 271004)
SEEDS = (1977, 8173, 27182, 31415)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def trace_bytes(name: str) -> bytes:
    """Read the local raw trace or its checked, byte-exact compressed archive."""
    raw_path = RUN / name
    if raw_path.exists():
        return raw_path.read_bytes()
    archive = RUN / f"{name}.gz"
    if archive.exists():
        with gzip.open(archive, "rb") as stream:
            return stream.read()
    raise FileNotFoundError(f"missing frozen trace and archive: {name}")


def feature_key(position) -> tuple:
    c = material_channels(position, 0)
    return tuple((kind, type_id, int(value))
                 for kind in sorted(c) for type_id, value in sorted(c[kind].items()))


def main() -> dict:
    if OUT.exists():
        raise FileExistsError("outcome-censor profile is write-once")
    games_raw = trace_bytes("eval-games.jsonl")
    if sha(games_raw) != EXPECTED_GAMES_SHA:
        raise ValueError("frozen task2625 evaluation games changed")
    games = [json.loads(line) for line in games_raw.splitlines() if line]
    queries = [json.loads(line) for line in trace_bytes("eval-queries.jsonl").decode("utf-8").splitlines() if line]

    # Intentionally project only censoring status, registered slot coordinates,
    # frozen horizon trace metadata, and exact replay state. Never read rewards,
    # actual_outcome values, search scores, or weights.
    by_slot: dict[tuple, list[dict]] = defaultdict(list)
    for q in queries:
        by_slot[tuple(q["slot"])].append(q)
    unknown = [g for g in games if g["ending"] == "HORIZON_UNKNOWN"]
    if len(games) != 1024 or len(unknown) != 44:
        raise ValueError("frozen slot/censor counts differ from the audited panel")

    per_rule = Counter()
    by_seed_color_endpoint = Counter()
    by_root_family = Counter()
    pair_endpoints: dict[tuple, set[str]] = defaultdict(set)
    trace = []
    rule_hashes = {}
    compiled_by_rule = {}
    for rule in RULE_IDS:
        rule_path = RULES / f"rules-{rule}.json"
        raw = rule_path.read_bytes()
        rule_hashes[str(rule)] = sha(raw)
        compiled_by_rule[rule] = compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))

    for game in unknown:
        rule, seed, family, color, endpoint = game["slot"]
        per_rule[rule] += 1
        by_seed_color_endpoint[(rule, seed, color, endpoint)] += 1
        by_root_family[(rule, family)] += 1
        pair_endpoints[(rule, seed, family, color)].add(endpoint)
        qs = by_slot[tuple(game["slot"])]
        if len(qs) != game["queries"]:
            raise ValueError("query count does not match frozen slot receipt")
        rec = deserialize_game_record(json.dumps(game["final_record"]))
        session = GameSession.replay(compiled_by_rule[rule], rec)
        positions = session._search_witnesses
        if len(positions) != len(rec.actions) + 1:
            raise ValueError("replayed position trace length mismatch")
        keys = [position_identity_key(pos, compiled_by_rule[rule]) for pos in positions]
        repeats = Counter(keys)
        feature_keys = [feature_key(pos) for pos in positions]
        same_final_16 = sum(feature_keys[i] == feature_keys[i - 1]
                            for i in range(max(1, len(feature_keys) - 16), len(feature_keys)))
        trace.append({
            "slot": list(game["slot"]),
            "ending": game["ending"],
            "plies": len(rec.actions),
            "logged_queries": len(qs),
            "max_logged_ply": max((int(q["ply"]) for q in qs), default=None),
            "final_16_material_static_transitions": same_final_16,
            "distinct_position_revisits": sum(n - 1 for n in repeats.values() if n > 1),
            "positions_visited_at_least_twice": sum(n > 1 for n in repeats.values()),
            "max_exact_position_visits": max(repeats.values(), default=0),
        })

    by_rule_seed_color_endpoint = [
        {"rule": r, "seed": s, "color": c, "endpoint": e, "unknown": n}
        for (r, s, c, e), n in sorted(by_seed_color_endpoint.items())
    ]
    pairs_with_unknown = Counter(rule for rule, _seed, _family, _color in pair_endpoints)
    pairs_both_unknown = Counter(
        rule for (rule, _seed, _family, _color), endpoints in pair_endpoints.items()
        if len(endpoints) == 2)
    root_families = {
        str(rule): sorted(family for (r, family), count in by_root_family.items() if r == rule)
        for rule in RULE_IDS
    }
    static16 = [row["final_16_material_static_transitions"] for row in trace]
    repeats = [row["distinct_position_revisits"] for row in trace]
    result = {
        "status": "PASS_OUTCOME_LABEL_BLIND_CENSORING_PROFILE",
        "source_sha256": {
            "eval_games_jsonl": EXPECTED_GAMES_SHA,
            "eval_queries_jsonl": sha((RUN / "eval-queries.jsonl").read_bytes()),
            "rules": rule_hashes,
        },
        "policy": "Only ending==HORIZON_UNKNOWN and fixed slot/ply/query metadata were inspected; reward, actual_outcome, search scores and weights were not read. No search or game was run.",
        "unknown_endpoints": len(trace),
        "by_rule": {str(r): per_rule[r] for r in RULE_IDS},
        "by_rule_seed_color_endpoint": by_rule_seed_color_endpoint,
        "paired_strata_with_unknown": {str(r): pairs_with_unknown[r] for r in RULE_IDS},
        "paired_strata_both_endpoints_unknown": {str(r): pairs_both_unknown[r] for r in RULE_IDS},
        "distinct_root_families_with_unknown": {r: len(v) for r, v in root_families.items()},
        "root_families_with_unknown": root_families,
        "trajectory_summary": {
            "plies_min_median_max": [min(x["plies"] for x in trace),
                                     sorted(x["plies"] for x in trace)[len(trace)//2],
                                     max(x["plies"] for x in trace)],
            "at_least_16_final_transitions_without_material_feature_change": sum(x == 16 for x in static16),
            "any_exact_position_revisit": sum(x > 0 for x in repeats),
            "max_exact_position_visits": max(x["max_exact_position_visits"] for x in trace),
            "repeat_count_definition": "Ruleset-aware exact PositionIdentity equality, including side-to-move and all position fields; not a causal explanation of censoring.",
            "material_static_definition": "Equal global board-current/hand-base material channels across the last16 transitions; quiet movement can still be progress.",
        },
        "slots": trace,
        "scope": "Descriptive review of the frozen H=128 panel only. No outcome imputation, fitted stopping rule, cap change, root reuse, or pooling with task2629's distinct H=256 roots.",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "slots" and k != "by_rule_seed_color_endpoint" and k != "root_families_with_unknown"}, indent=2))
    return result


if __name__ == "__main__":
    main()
