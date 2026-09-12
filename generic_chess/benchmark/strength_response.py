"""Layer-D paired search-budget qualification.

This module is deliberately a small adapter around the existing learning
arena.  It owns the *protocol* for a strength-response measurement, while
``learning.arena`` remains the only match runner and ``learning.openings``
remains the only opening-corpus authority.

The protocol has two immutable phases:

* :func:`prepare_strength_response` freezes all identities and budgets;
* :func:`measure_strength_response` consumes that preparation and records the
  resulting paired observations.

The runner is injectable so protocol tests can use deterministic summaries
without spending real Arena compute.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any, Callable, Mapping, Sequence

from ..core.actions import action_to_dict
from ..learning.arena import ArenaConfig, ArenaSummary, run_arena
from ..learning.openings import ArenaOpeningCorpus
from ..learning.serialization import stable_sha256
from ..learning.statistics import bootstrap_pair_mean_ci


STRENGTH_RESPONSE_SCHEMA = "generic-chess-strength-response-v1"
PREP_SCHEMA = "generic-chess-strength-response-prep-v1"
HORIZON_AWARE_PREP_SCHEMA = "generic-chess-strength-response-horizon-aware-prep-v2"
ACTION_TRACE_SCHEMA = "generic-chess-strength-response-action-trace-v1"
DEFAULT_BUDGETS = (256, 1024, 4096)
DEFAULT_MATCHUPS = ((1024, 256), (4096, 1024), (4096, 256))
STATUS_PASS = "PASS"
STATUS_DEFER = "DEFER"
STATUS_FAIL = "FAIL"


def _as_tuple_ints(values: Sequence[int], *, name: str) -> tuple[int, ...]:
    result = tuple(int(value) for value in values)
    if not result or any(value <= 0 for value in result):
        raise ValueError(f"{name} must contain positive integers")
    if tuple(sorted(set(result))) != result:
        raise ValueError(f"{name} must be strictly increasing")
    return result


def _corpus_identity(opening_corpus: ArenaOpeningCorpus | Any | None) -> tuple[str, tuple[int, ...]]:
    if opening_corpus is None:
        return "", ()
    corpus_id = getattr(opening_corpus, "corpus_id", None)
    if not isinstance(corpus_id, str) or not corpus_id:
        corpus_id = stable_sha256(opening_corpus.to_dict())
    rows = getattr(opening_corpus, "openings", ())
    seeds = tuple(int(getattr(row, "opening_seed")) for row in rows)
    return corpus_id, seeds


@dataclass(frozen=True, slots=True)
class StrengthResponsePrep:
    """Frozen, result-free Layer-D experiment definition."""

    schema: str
    ruleset_fingerprint: str
    candidate_fingerprint: str
    evaluator_identity: str
    budget_ladder: tuple[int, ...]
    max_depth: int
    pair_count: int
    opening_corpus_id: str
    opening_seeds: tuple[int, ...]
    tape_seeds: tuple[int, ...]
    bootstrap_confidence: float
    bootstrap_resamples: int
    bootstrap_seed: int
    classification_rule: str
    experiment_identity: str
    workers: int = 1
    tt_megabytes: int = 8
    opening_corpus_ids: tuple[str, ...] = ()
    # These fields are required by the R5 schema.  They remain optional for
    # the already-published R2 schema so its immutable PREP can still be read.
    max_ply: int | None = None
    child_ceiling_gate_fraction: float | None = None
    horizon_hit_gate_fraction: float | None = None
    action_trace_schema: str | None = None

    def __post_init__(self) -> None:
        if self.schema not in {PREP_SCHEMA, HORIZON_AWARE_PREP_SCHEMA}:
            raise ValueError("unsupported strength-response preparation schema")
        if not self.ruleset_fingerprint or not self.candidate_fingerprint:
            raise ValueError("ruleset and candidate identities are required")
        if not self.evaluator_identity:
            raise ValueError("evaluator_identity is required")
        _as_tuple_ints(self.budget_ladder, name="budget_ladder")
        if len(self.budget_ladder) != 3:
            raise ValueError("Layer-D preparation requires three budgets")
        if self.max_depth <= 0 or self.pair_count <= 0 or self.workers <= 0 or self.tt_megabytes <= 0:
            raise ValueError("max_depth, pair_count, workers, and tt_megabytes must be positive")
        if len(self.opening_seeds) < 3 and len(self.tape_seeds) < 3:
            raise ValueError("at least three independent opening/tape seeds are required")
        if self.opening_corpus_ids and len(self.opening_corpus_ids) < 3:
            raise ValueError("at least three opening corpus identities are required")
        if not 0.0 < self.bootstrap_confidence < 1.0:
            raise ValueError("bootstrap_confidence must be between zero and one")
        if self.bootstrap_resamples <= 0:
            raise ValueError("bootstrap_resamples must be positive")
        if self.schema == HORIZON_AWARE_PREP_SCHEMA:
            if self.max_ply is None or self.max_ply <= 0:
                raise ValueError("horizon-aware PREP requires a positive max_ply")
            for name in ("child_ceiling_gate_fraction", "horizon_hit_gate_fraction"):
                value = getattr(self, name)
                if value is None or not 0.0 <= value <= 1.0:
                    raise ValueError(f"horizon-aware PREP requires {name} in [0, 1]")
            if self.action_trace_schema != ACTION_TRACE_SCHEMA:
                raise ValueError("horizon-aware PREP requires the action-trace schema")

    @property
    def prep_fingerprint(self) -> str:
        return stable_sha256(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        payload = asdict(self)
        payload["budget_ladder"] = list(self.budget_ladder)
        payload["opening_seeds"] = list(self.opening_seeds)
        payload["tape_seeds"] = list(self.tape_seeds)
        payload["opening_corpus_ids"] = list(self.opening_corpus_ids)
        if self.schema == PREP_SCHEMA:
            for key in (
                "max_ply", "child_ceiling_gate_fraction",
                "horizon_hit_gate_fraction", "action_trace_schema",
            ):
                payload.pop(key)
        if include_fingerprint:
            payload["prep_fingerprint"] = self.prep_fingerprint
        return payload


def prepare_strength_response(
    compiled: Any,
    *,
    evaluator_identity: str,
    candidate_fingerprint: str,
    opening_corpus: ArenaOpeningCorpus | Any | None = None,
    opening_corpora: Sequence[ArenaOpeningCorpus | Any] | None = None,
    budget_ladder: Sequence[int] = DEFAULT_BUDGETS,
    max_depth: int = 12,
    pair_count: int = 6,
    tape_seeds: Sequence[int] = (941, 1943, 3947),
    opening_seeds: Sequence[int] | None = None,
    bootstrap_confidence: float = 0.95,
    bootstrap_resamples: int = 10_000,
    bootstrap_seed: int = 271828,
    workers: int = 1,
    tt_megabytes: int = 8,
    schema: str = PREP_SCHEMA,
    max_ply: int | None = None,
    child_ceiling_gate_fraction: float = 0.5,
    horizon_hit_gate_fraction: float = 0.5,
) -> StrengthResponsePrep:
    """Freeze a PREP manifest before any Arena result is observed."""

    budgets = _as_tuple_ints(budget_ladder, name="budget_ladder")
    if len(budgets) != 3:
        raise ValueError("budget_ladder must contain exactly three budgets")
    if tuple(round(budgets[i] / budgets[0], 10) for i in range(3)) != (1.0, 4.0, 16.0):
        raise ValueError("Layer-D budgets must use a 1:4:16 ladder")
    if opening_corpora is not None and opening_corpus is not None:
        raise ValueError("pass opening_corpus or opening_corpora, not both")
    corpora = tuple(opening_corpora or (() if opening_corpus is None else (opening_corpus,)))
    corpus_rows = tuple(_corpus_identity(corpus) for corpus in corpora)
    corpus_id = corpus_rows[0][0] if corpus_rows else ""
    corpus_ids = tuple(row[0] for row in corpus_rows)
    corpus_seeds = tuple(seed for _, seeds in corpus_rows for seed in seeds)
    seeds = tuple(int(value) for value in (opening_seeds if opening_seeds is not None else corpus_seeds))
    tapes = tuple(int(value) for value in tape_seeds)
    if len(seeds) < 3 and len(tapes) < 3:
        raise ValueError("opening_corpus or at least three opening/tape seeds is required")
    if not corpus_ids:
        corpus_ids = tuple(f"tape-{seed}" for seed in tapes)
        corpus_id = corpus_ids[0]
    ruleset_fingerprint = str(getattr(compiled, "ruleset_fingerprint", ""))
    if not ruleset_fingerprint:
        raise ValueError("compiled.ruleset_fingerprint is required")
    identity = {
        "schema": schema,
        "ruleset_fingerprint": ruleset_fingerprint,
        "candidate_fingerprint": str(candidate_fingerprint),
        "evaluator_identity": str(evaluator_identity),
        "budget_ladder": list(budgets),
        "max_depth": int(max_depth),
        "pair_count": int(pair_count),
        "opening_corpus_id": corpus_id,
        "opening_corpus_ids": list(corpus_ids),
        "opening_seeds": list(seeds),
        "tape_seeds": list(tapes),
        "bootstrap_confidence": float(bootstrap_confidence),
        "bootstrap_resamples": int(bootstrap_resamples),
        "bootstrap_seed": int(bootstrap_seed),
        "classification_rule": "positive paired strongest-vs-weakest response; monotone adjacent budgets; no censoring/fallback; otherwise DEFER",
        "workers": int(workers),
        "tt_megabytes": int(tt_megabytes),
    }
    if schema == HORIZON_AWARE_PREP_SCHEMA:
        identity.update({
            "max_ply": None if max_ply is None else int(max_ply),
            "child_ceiling_gate_fraction": float(child_ceiling_gate_fraction),
            "horizon_hit_gate_fraction": float(horizon_hit_gate_fraction),
            "action_trace_schema": ACTION_TRACE_SCHEMA,
            "classification_rule": (
                "positive paired strongest-vs-weakest response; monotone adjacent budgets; "
                "no explicit censoring/fallback; child-only ceiling and strongest-vs-weakest "
                "horizon fractions below their frozen GenericChess-specific empirical gates; "
                "otherwise DEFER"
            ),
        })
    return StrengthResponsePrep(
        **{**identity, "budget_ladder": budgets, "opening_seeds": seeds, "tape_seeds": tapes, "opening_corpus_ids": corpus_ids},
        experiment_identity=f"strength-response-{stable_sha256(identity)}",
    )


def _summary_payload(summary: ArenaSummary | Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a real ArenaSummary or a small synthetic test summary."""

    if isinstance(summary, Mapping):
        payload = dict(summary)
        pair_scores = tuple(float(value) for value in payload.get("pair_scores", ()))
        if not pair_scores and "mean_pair_score" in payload:
            pair_scores = (float(payload["mean_pair_score"]),)
        payload["pair_scores"] = list(pair_scores)
        payload.setdefault("pair_count", len(pair_scores))
        payload.setdefault("mean_pair_score", mean(pair_scores) if pair_scores else 0.0)
        payload.setdefault("bootstrap_low", None)
        payload.setdefault("bootstrap_high", None)
        return payload
    pair_scores = tuple(float(value) for value in summary.pair_scores)
    tapes = []
    for pair in summary.pairs:
        first, second = pair.game_child_owner0, pair.game_child_owner1
        tapes.append({
            "opening_id": pair.opening_id,
            "pair_score": pair.child_pair_score,
            "role_swap": {
                "child_owner_0": first.child_points,
                "child_owner_1": second.child_points,
            },
            "games": [
                _game_payload(first),
                _game_payload(second),
            ],
        })
    flattened_games = [game for tape in tapes for game in tape["games"]]
    return {
        "pair_count": summary.pair_count,
        "pair_scores": list(pair_scores),
        "mean_pair_score": summary.mean_pair_score,
        "bootstrap_low": summary.bootstrap_low,
        "bootstrap_high": summary.bootstrap_high,
        "tapes": tapes,
        # R5 consumes game-level terminal and replay telemetry.  Keep this
        # flattened view alongside the paired representation so a reducer
        # cannot silently mistake a real ArenaSummary for zero games.
        "games": flattened_games,
        "game_wins": summary.game_wins,
        "game_draws": summary.game_draws,
        "game_losses": summary.game_losses,
        "game_score_rate": summary.game_score_rate,
    }


def _game_payload(game: Any) -> dict[str, Any]:
    """Expose a deterministic replay witness without changing Arena behavior."""

    return {
        "pair_index": getattr(game, "pair", None),
        "opening_id": getattr(game, "opening_id", None),
        "opening_position_key": getattr(game, "opening_position_key", None),
        "child_owner": int(game.child_owner),
        "winner": game.winner,
        "termination_status": str(game.result),
        "actual_plies": int(game.plies),
        "actions": [action_to_dict(action) for action in getattr(game, "actions", ())],
        "final_position_key": getattr(game, "final_position_key", None),
        "declaration_id": getattr(game, "declaration_id", None),
        "search_metrics": list(game.search_metrics),
    }


def _bootstrap_difference_ci(left: Sequence[float], right: Sequence[float], *, seed: int, confidence: float, resamples: int) -> tuple[float, float]:
    if len(left) != len(right) or not left:
        return (float("nan"), float("nan"))
    differences = [float(a) - float(b) for a, b in zip(left, right)]
    return bootstrap_pair_mean_ci(
        differences, confidence=confidence, resamples=resamples, seed=seed
    )


def _recursive_flags(value: Any) -> tuple[bool, bool]:
    censored = fallback = False
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {"depth_censored", "budget_censored", "censored"} and bool(item):
                censored = True
            if lowered in {"fallback", "used_fallback", "fallback_count"} and bool(item):
                fallback = True
            child_censored, child_fallback = _recursive_flags(item)
            censored |= child_censored
            fallback |= child_fallback
    elif isinstance(value, (list, tuple)):
        for item in value:
            child_censored, child_fallback = _recursive_flags(item)
            censored |= child_censored
            fallback |= child_fallback
    return censored, fallback


def _depth_ceiling_stats(value: Any, max_depth: int, *, engine_role: str | None = None) -> tuple[int, int]:
    total = hits = 0
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() == "completed_depth" and (
                engine_role is None or value.get("engine_role") == engine_role
            ):
                total += 1
                hits += int(item) >= max_depth
            child_total, child_hits = _depth_ceiling_stats(item, max_depth, engine_role=engine_role)
            total += child_total
            hits += child_hits
    elif isinstance(value, (list, tuple)):
        for item in value:
            child_total, child_hits = _depth_ceiling_stats(item, max_depth, engine_role=engine_role)
            total += child_total
            hits += child_hits
    return total, hits


def _recursive_sum(value: Any, keys: set[str]) -> int:
    total = 0
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in keys and isinstance(item, (int, float)):
                total += int(item)
            total += _recursive_sum(item, keys)
    elif isinstance(value, (list, tuple)):
        total = sum(_recursive_sum(item, keys) for item in value)
    return total


def _horizon_and_trace_contract(
    prep: StrengthResponsePrep,
    tape_results: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    """Build R5's replayable game ledger from already-observed Arena data.

    This function is observational: it serializes the actions Arena selected;
    it never supplies an action, touches a transposition table, or alters a
    termination condition.
    """

    rows: list[dict[str, Any]] = []
    horizon_by_tape: dict[str, dict[str, dict[str, int | float]]] = {}
    for tape_id, matchups in tape_results.items():
        horizon_by_tape[tape_id] = {}
        for matchup, summary in matchups.items():
            games = summary.get("games", ())
            hits = 0
            expected_games = 2 * prep.pair_count
            if len(games) != expected_games:
                raise ValueError(
                    f"{tape_id}/{matchup} must contain exactly {expected_games} seat-swapped games"
                )
            seen_pair_owners: set[tuple[int, int]] = set()
            for game_index, game in enumerate(games):
                if not isinstance(game, Mapping):
                    raise ValueError(f"{tape_id}/{matchup} contains a non-mapping game")
                termination = str(game.get("termination_status", game.get("result", "")))
                pair_index = game.get("pair_index", game.get("pair"))
                child_owner = game.get("child_owner")
                required = {
                    "termination_status": termination,
                    "actual_plies": game.get("actual_plies", game.get("plies")),
                    "opening_position_key": game.get("opening_position_key"),
                    "final_position_key": game.get("final_position_key"),
                    "pair_index": pair_index,
                    "child_owner": child_owner,
                }
                if any(value is None or value == "" for value in required.values()):
                    raise ValueError(f"{tape_id}/{matchup} game telemetry is incomplete")
                if child_owner not in (0, 1) or not isinstance(pair_index, int):
                    raise ValueError(f"{tape_id}/{matchup} game pair/owner identity is invalid")
                pair_owner = (pair_index, child_owner)
                if pair_owner in seen_pair_owners:
                    raise ValueError(f"{tape_id}/{matchup} duplicates a seat-swapped game")
                seen_pair_owners.add(pair_owner)
                max_ply_hit = termination == "max_ply"
                hits += int(max_ply_hit)
                actions = [dict(action) for action in game.get("actions", ())]
                budget_roles = {
                    "4x-vs-1x": (prep.budget_ladder[0], prep.budget_ladder[1]),
                    "16x-vs-4x": (prep.budget_ladder[1], prep.budget_ladder[2]),
                    "16x-vs-1x": (prep.budget_ladder[0], prep.budget_ladder[2]),
                }[matchup]
                record = {
                    "schema": ACTION_TRACE_SCHEMA,
                    "tape_id": tape_id,
                    "opening_corpus_id": tape_id,
                    "matchup": matchup,
                    "game_index": game_index,
                    "pair_index": pair_index,
                    "child_owner": child_owner,
                    "budget_roles": {
                        "parent_nodes_per_move": budget_roles[0],
                        "child_nodes_per_move": budget_roles[1],
                    },
                    "termination_status": termination,
                    "max_ply": prep.max_ply,
                    "max_ply_hit": max_ply_hit,
                    "actual_plies": game.get("actual_plies", game.get("plies")),
                    "opening_position_key": game.get("opening_position_key"),
                    "final_position_key": game.get("final_position_key"),
                    "declaration_id": game.get("declaration_id"),
                    "actions": actions,
                }
                record["action_trace_sha256"] = stable_sha256(record)
                rows.append(record)
            expected_pair_owners = {
                (pair_index, child_owner)
                for pair_index in range(prep.pair_count)
                for child_owner in (0, 1)
            }
            if seen_pair_owners != expected_pair_owners:
                raise ValueError(f"{tape_id}/{matchup} lacks a complete seat-swapped pair set")
            total = len(games)
            horizon_by_tape[tape_id][matchup] = {
                "max_ply_hits": hits,
                "games": total,
                "fraction": hits / total if total else 0.0,
            }
    strongest = [
        values["16x-vs-1x"]
        for values in horizon_by_tape.values()
        if "16x-vs-1x" in values
    ]
    strongest_hits = sum(int(row["max_ply_hits"]) for row in strongest)
    strongest_games = sum(int(row["games"]) for row in strongest)
    return {
        "schema": ACTION_TRACE_SCHEMA,
        "required_for_all_games": True,
        "horizon_by_tape": horizon_by_tape,
        "strongest_vs_weakest_pooled_horizon": {
            "max_ply_hits": strongest_hits,
            "games": strongest_games,
            "fraction": strongest_hits / strongest_games if strongest_games else 0.0,
        },
        "action_traces": rows,
    }


def _classify(
    prep: StrengthResponsePrep,
    matchups: Mapping[str, Mapping[str, Any]],
    tape_results: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> tuple[str, tuple[str, ...], dict[str, Any]]:
    low, medium, high = prep.budget_ladder
    ordered = [
        matchups[f"{medium // low}x-vs-1x"],
        matchups[f"{high // low}x-vs-{medium // low}x"],
        matchups[f"{high // low}x-vs-1x"],
    ]
    means = [float(row["mean_pair_score"]) for row in ordered]
    all_payload = list(matchups.values())
    high_rows = [rows["16x-vs-1x"] for rows in tape_results.values()]
    depth_total = sum(_depth_ceiling_stats(row, prep.max_depth, engine_role="child")[0] for row in high_rows)
    depth_hits = sum(_depth_ceiling_stats(row, prep.max_depth, engine_role="child")[1] for row in high_rows)
    parent_depth_total = sum(_depth_ceiling_stats(row, prep.max_depth, engine_role="parent")[0] for row in high_rows)
    parent_depth_hits = sum(_depth_ceiling_stats(row, prep.max_depth, engine_role="parent")[1] for row in high_rows)
    high_budget_ceiling_hit_fraction = (
        depth_hits / depth_total if depth_total else 0.0
    )
    trace_contract = (
        _horizon_and_trace_contract(prep, tape_results)
        if prep.schema == HORIZON_AWARE_PREP_SCHEMA else None
    )
    horizon_fraction = (
        trace_contract["strongest_vs_weakest_pooled_horizon"]["fraction"]
        if trace_contract is not None else 0.0
    )
    explicit_censored = any(_recursive_flags(row)[0] for row in all_payload)
    censored = explicit_censored
    if prep.schema == HORIZON_AWARE_PREP_SCHEMA:
        censored |= high_budget_ceiling_hit_fraction >= prep.child_ceiling_gate_fraction
        censored |= horizon_fraction >= prep.horizon_hit_gate_fraction
    else:
        censored |= high_budget_ceiling_hit_fraction >= 0.5
    fallback = any(_recursive_flags(row)[1] for row in all_payload)
    adjacent = (means[0] - 0.5, means[1] - 0.5)
    strongest_vs_weakest = means[2] - 0.5
    tape_effects = [
        mean(rows["16x-vs-1x"]["pair_scores"]) - 0.5
        for rows in tape_results.values()
    ]
    descriptors = {
        "search_strength_slope": {
            "value": (means[-1] - means[0]) / (prep.budget_ladder[-1] - prep.budget_ladder[0]),
            "provenance": "EMPIRICAL_GATE",
        },
        "strongest_vs_weakest_score": {"value": means[2], "provenance": "EMPIRICAL_GATE"},
        "search_response_monotonicity": {
            "value": bool(adjacent[0] > 0 and adjacent[1] > 0 and strongest_vs_weakest > 0),
            "provenance": "EMPIRICAL_GATE",
        },
        "search_response_uncertainty": {
            "value": {
                "strongest_vs_weakest_ci": ordered[2].get("difference_ci"),
                "tape_effect_count": len(tape_effects),
            },
            "provenance": "EMPIRICAL_GATE",
        },
        "high_budget_ceiling_hit_fraction": {
            "value": high_budget_ceiling_hit_fraction,
            "provenance": "EMPIRICAL_GATE",
        },
        "depth_ceiling_by_role": {
            "value": {
                "child": {"hits": depth_hits, "count": depth_total},
                "parent": {"hits": parent_depth_hits, "count": parent_depth_total},
            },
            "provenance": "GENERICCHESS_SPECIFIC",
        },
        "explicit_censor_flags_present": {
            "value": explicit_censored,
            "provenance": "GENERICCHESS_SPECIFIC",
        },
    }
    if prep.schema == HORIZON_AWARE_PREP_SCHEMA:
        descriptors["strongest_vs_weakest_horizon_hit_fraction"] = {
            "value": horizon_fraction,
            "provenance": "GENERICCHESS_SPECIFIC",
        }
        descriptors["action_trace_contract"] = {
            "value": trace_contract,
            "provenance": "GENERICCHESS_SPECIFIC",
        }
    if censored:
        if explicit_censored:
            return STATUS_DEFER, ("DEPTH_CENSORED",), descriptors
        if horizon_fraction >= (prep.horizon_hit_gate_fraction or 0.5):
            return STATUS_DEFER, ("HORIZON_CENSORED",), descriptors
        return STATUS_DEFER, ("DEPTH_CENSORED",), descriptors
    if fallback:
        return STATUS_DEFER, ("SEARCH_FALLBACK_PRESENT",), descriptors
    if tape_effects and min(tape_effects) <= 0.0 < max(tape_effects):
        return STATUS_DEFER, ("MIXED_TAPE_RESPONSE",), descriptors
    if strongest_vs_weakest < 0.0:
        return STATUS_DEFER, ("SEARCH_RESPONSE_INVERTED",), descriptors
    if not all(effect > 0.0 for effect in adjacent) or strongest_vs_weakest <= 0.0:
        return STATUS_DEFER, ("SEARCH_RESPONSE_NOT_MONOTONE",), descriptors
    if ordered[2].get("difference_ci") and ordered[2]["difference_ci"][0] <= 0.0:
        return STATUS_DEFER, ("SEARCH_RESPONSE_UNCERTAIN",), descriptors
    return STATUS_PASS, (), descriptors


def _validate_checkpoint_invariance(compiled, parent, child, prep: StrengthResponsePrep) -> None:
    parent_id = str(getattr(parent, "checkpoint_id", ""))
    child_id = str(getattr(child, "checkpoint_id", ""))
    if not parent_id or parent_id != child_id:
        raise ValueError("parent and child checkpoint identity must be identical")
    if prep.candidate_fingerprint != parent_id:
        raise ValueError("checkpoint identity does not match PREP candidate fingerprint")
    parent_rules = str(getattr(parent, "ruleset_fingerprint", ""))
    child_rules = str(getattr(child, "ruleset_fingerprint", ""))
    compiled_rules = str(getattr(compiled, "ruleset_fingerprint", ""))
    if not parent_rules or parent_rules != child_rules or parent_rules != compiled_rules:
        raise ValueError("checkpoint ruleset identity does not match PREP/compiled ruleset")
    parent_eval = str(getattr(parent, "evaluator_version", ""))
    child_eval = str(getattr(child, "evaluator_version", ""))
    if not parent_eval or parent_eval != child_eval or parent_eval != prep.evaluator_identity:
        raise ValueError("checkpoint evaluator identity does not match PREP")


def _empty_result(prep: StrengthResponsePrep, reason: str) -> "StrengthResponseResult":
    empty = {key: {"status": "SKIPPED", "pair_scores": [], "pair_count": 0} for key in (
        "4x-vs-1x", "16x-vs-4x", "16x-vs-1x"
    )}
    return StrengthResponseResult(
        schema=STRENGTH_RESPONSE_SCHEMA,
        prep_fingerprint=prep.prep_fingerprint,
        experiment_identity=prep.experiment_identity,
        ruleset_fingerprint=prep.ruleset_fingerprint,
        candidate_fingerprint=prep.candidate_fingerprint,
        evaluator_identity=prep.evaluator_identity,
        budget_ladder=prep.budget_ladder,
        max_depth=prep.max_depth,
        pair_count=prep.pair_count,
        opening_corpus_id=prep.opening_corpus_id,
        opening_corpus_ids=prep.opening_corpus_ids,
        opening_seeds=prep.opening_seeds,
        tape_seeds=prep.tape_seeds,
        matchups=empty,
        tape_results={},
        layer_d_status=STATUS_DEFER,
        reason_codes=(reason,),
        behavior_descriptors={},
        compute_usage={"arena_matchups": 0, "arena_pairs": 0, "arena_games": 0},
    )


def measure_strength_response(
    compiled: Any = None,
    native_rules: Any = None,
    parent: Any = None,
    child: Any = None,
    prep: StrengthResponsePrep | None = None,
    *,
    opening_corpus: ArenaOpeningCorpus | Any | None = None,
    opening_corpora: Sequence[ArenaOpeningCorpus | Any] | None = None,
    arena_runner: Callable[..., Any] | None = None,
    summaries: Mapping[str, ArenaSummary | Mapping[str, Any]] | None = None,
    capture_search_metrics: bool = True,
    base_report: Any | None = None,
) -> "StrengthResponseResult":
    """Measure a frozen preparation, or reduce supplied synthetic summaries.

    ``summaries`` is intentionally a public test seam.  Without it, the
    function invokes the existing paired Arena once for each frozen tape and
    matchup.
    """

    if isinstance(prep, Mapping):
        prep_data = dict(prep)
        supplied_fingerprint = prep_data.pop("prep_fingerprint", None)
        prep = StrengthResponsePrep(
            **{
                **prep_data,
                "budget_ladder": tuple(prep_data["budget_ladder"]),
                "opening_seeds": tuple(prep_data.get("opening_seeds", ())),
                "tape_seeds": tuple(prep_data.get("tape_seeds", ())),
                "opening_corpus_ids": tuple(prep_data.get("opening_corpus_ids", ())),
            }
        )
        if supplied_fingerprint != prep.prep_fingerprint:
            raise ValueError("PREP fingerprint does not match its frozen contents")
    if prep is None:
        raise ValueError("measure_strength_response requires a frozen PREP")
    if base_report is not None and any(
        base_report.layers.get(layer) != STATUS_PASS for layer in ("A", "C")
    ):
        return _empty_result(prep, "PREREQUISITE_A_C_NOT_PASS")
    if opening_corpora is not None and opening_corpus is not None:
        raise ValueError("pass opening_corpus or opening_corpora, not both")
    corpora = tuple(opening_corpora or (() if opening_corpus is None else (opening_corpus,)))
    if corpora and len(corpora) != len(prep.tape_seeds):
        raise ValueError("RESULT must consume one opening corpus per frozen tape seed")
    if corpora:
        actual_ids = tuple(_corpus_identity(corpus)[0] for corpus in corpora)
        if actual_ids != prep.opening_corpus_ids:
            raise ValueError("opening corpus identities do not match PREP")
    if summaries is not None and any(
        key in summaries for key in ("4x-vs-1x", "16x-vs-4x", "16x-vs-1x")
    ):
        summary_by_tape = {prep.opening_corpus_ids[0] if prep.opening_corpus_ids else "tape-0": summaries}
    else:
        summary_by_tape = summaries or {}
    if not summary_by_tape and not corpora:
        raise ValueError("RESULT requires Arena inputs or explicit synthetic summaries")
    if summaries is not None and len(summary_by_tape) != len(prep.tape_seeds):
        raise ValueError("RESULT summaries must contain all frozen tapes")
    if summaries is None and not corpora:
        raise ValueError("real RESULT requires frozen opening corpora")
    if summaries is not None and not corpora and len(summary_by_tape) != len(prep.tape_seeds):
        raise ValueError("synthetic RESULT must contain one summary set per tape")
    if corpora and len(prep.opening_corpus_ids) != len(corpora):
        raise ValueError("PREP does not freeze the supplied corpus identities")
    if parent is not None and child is not None:
        _validate_checkpoint_invariance(compiled, parent, child, prep)
    runner = arena_runner or run_arena
    tape_rows: dict[str, dict[str, dict[str, Any]]] = {}
    corpus_by_id = {
        _corpus_identity(corpus)[0]: corpus for corpus in corpora
    }
    low, medium, high = prep.budget_ladder
    for tape_index, tape_seed in enumerate(prep.tape_seeds):
        tape_id = prep.opening_corpus_ids[tape_index] if prep.opening_corpus_ids else f"tape-{tape_seed}"
        tape_rows[tape_id] = {}
        per_tape = summary_by_tape.get(tape_id, {})
        for strong, weak in ((medium, low), (high, medium), (high, low)):
            key = f"{strong // low}x-vs-{weak // low}x"
            if summaries is not None:
                supplied = per_tape.get(key) or per_tape.get(f"{strong}x-vs-{weak}x")
                if supplied is None:
                    raise ValueError(f"missing RESULT summary for {tape_id}/{key}")
            else:
                corpus = corpus_by_id[tape_id]
                if compiled is not None and hasattr(corpus, "validate"):
                    corpus.validate(compiled)
                config = ArenaConfig(
                    pairs=prep.pair_count,
                    nodes_per_move=strong,
                    parent_nodes_per_move=weak,
                    child_nodes_per_move=strong,
                    max_depth=prep.max_depth,
                    tt_megabytes=prep.tt_megabytes,
                    opening_seed=getattr(corpus, "seed", tape_seed),
                    opening_count=prep.pair_count,
                    workers=prep.workers,
                )
                supplied = runner(
                    compiled, native_rules, parent, child, config, corpus,
                    capture_search_metrics=capture_search_metrics,
                )
            row = _summary_payload(supplied)
            scores = row.get("pair_scores", [])
            if len(scores) != prep.pair_count:
                raise ValueError(f"{tape_id}/{key} must contain exactly pair_count paired scores")
            row["pair_scores"] = [float(score) for score in scores]
            tape_rows[tape_id][key] = row
    result_rows = {}
    for key in ("4x-vs-1x", "16x-vs-4x", "16x-vs-1x"):
        rows = [tape_rows[tape_id][key] for tape_id in tape_rows]
        pooled_scores = [score for row in rows for score in row["pair_scores"]]
        result_rows[key] = {
            "pair_count": len(pooled_scores),
            "pair_scores": pooled_scores,
            "mean_pair_score": mean(pooled_scores),
            "tapes": {tape_id: tape_rows[tape_id][key] for tape_id in tape_rows},
            "search_nodes": sum(int(row.get("search_nodes", 0) or 0) for row in rows),
        }
    for key in ("4x-vs-1x", "16x-vs-4x", "16x-vs-1x"):
        row = result_rows[key]
        row["difference_ci"] = list(_bootstrap_difference_ci(
            row["pair_scores"], [0.5] * (prep.pair_count * len(tape_rows)),
            seed=prep.bootstrap_seed + list(result_rows).index(key),
            confidence=prep.bootstrap_confidence,
            resamples=prep.bootstrap_resamples,
        ))
    layer_d_status, reason_codes, descriptors = _classify(prep, result_rows, tape_rows)
    compute_usage = {
        "arena_matchups": len(result_rows),
        "arena_tapes": len(tape_rows),
        "arena_pairs": prep.pair_count * len(result_rows) * len(tape_rows),
        "arena_games": prep.pair_count * len(result_rows) * len(tape_rows) * 2,
        "training_steps": 0,
        "heavy_jobs": 0,
        "search_nodes": sum(
            int(row.get("search_nodes", 0) or 0)
            + _recursive_sum(row, {"nodes", "searched_nodes"})
            for row in result_rows.values()
        ),
    }
    return StrengthResponseResult(
        schema=STRENGTH_RESPONSE_SCHEMA,
        prep_fingerprint=prep.prep_fingerprint,
        experiment_identity=prep.experiment_identity,
        ruleset_fingerprint=prep.ruleset_fingerprint,
        candidate_fingerprint=prep.candidate_fingerprint,
        evaluator_identity=prep.evaluator_identity,
        budget_ladder=prep.budget_ladder,
        max_depth=prep.max_depth,
        pair_count=prep.pair_count,
        opening_corpus_id=prep.opening_corpus_id,
        opening_corpus_ids=prep.opening_corpus_ids,
        opening_seeds=prep.opening_seeds,
        tape_seeds=prep.tape_seeds,
        matchups=result_rows,
        tape_results=tape_rows,
        layer_d_status=layer_d_status,
        reason_codes=reason_codes,
        behavior_descriptors=descriptors,
        compute_usage=compute_usage,
    )


@dataclass(frozen=True, slots=True)
class StrengthResponseResult:
    schema: str
    prep_fingerprint: str
    experiment_identity: str
    ruleset_fingerprint: str
    candidate_fingerprint: str
    evaluator_identity: str
    budget_ladder: tuple[int, ...]
    max_depth: int
    pair_count: int
    opening_corpus_id: str
    opening_corpus_ids: tuple[str, ...]
    opening_seeds: tuple[int, ...]
    tape_seeds: tuple[int, ...]
    matchups: dict[str, dict[str, Any]]
    tape_results: dict[str, dict[str, dict[str, Any]]]
    layer_d_status: str
    reason_codes: tuple[str, ...]
    behavior_descriptors: dict[str, dict[str, Any]]
    compute_usage: dict[str, Any]

    def __post_init__(self) -> None:
        if self.schema != STRENGTH_RESPONSE_SCHEMA:
            raise ValueError("unsupported strength-response result schema")
        if self.layer_d_status not in {STATUS_PASS, STATUS_FAIL, STATUS_DEFER}:
            raise ValueError("invalid Layer-D status")
        required = {"4x-vs-1x", "16x-vs-4x", "16x-vs-1x"}
        if set(self.matchups) != required:
            raise ValueError("result must contain all three Layer-D matchups")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["budget_ladder"] = list(self.budget_ladder)
        payload["opening_seeds"] = list(self.opening_seeds)
        payload["opening_corpus_ids"] = list(self.opening_corpus_ids)
        payload["tape_seeds"] = list(self.tape_seeds)
        payload["reason_codes"] = list(self.reason_codes)
        return payload


__all__ = [
    "ACTION_TRACE_SCHEMA",
    "DEFAULT_BUDGETS",
    "DEFAULT_MATCHUPS",
    "HORIZON_AWARE_PREP_SCHEMA",
    "PREP_SCHEMA",
    "STRENGTH_RESPONSE_SCHEMA",
    "StrengthResponsePrep",
    "StrengthResponseResult",
    "measure_strength_response",
    "prepare_strength_response",
]
