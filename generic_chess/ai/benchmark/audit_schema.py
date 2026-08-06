"""Versioned dataclasses and JSON validation for the native-readiness audit."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class RuleSetFixtureSpec:
    fixture_id: str
    generator_mode: str  # "generator" | "handbuilt"
    board_size: int
    ruleset_seed: int
    generator_options: Mapping[str, Any] = field(default_factory=dict)
    movement_buckets: tuple[str, ...] = ()
    promotion_buckets: tuple[str, ...] = ()
    drop_buckets: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PositionFixtureSpec:
    fixture_id: str
    ruleset_fixture_id: str
    action_prefix: tuple[dict, ...]
    expected_categories: tuple[str, ...]
    playout_seed: int


@dataclass(frozen=True, slots=True)
class SuiteManifest:
    schema_version: int
    suite_version: str
    generator_version: str
    commit: str
    rulesets: tuple[RuleSetFixtureSpec, ...]
    positions: tuple[PositionFixtureSpec, ...]


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"invalid audit manifest: {message}")


def validate_manifest(raw: Mapping[str, Any]) -> None:
    _check(raw.get("schema_version") == 1, "schema_version must be 1")
    _check(isinstance(raw.get("suite_version"), str) and raw["suite_version"], "suite_version required")
    _check(isinstance(raw.get("generator_version"), str), "generator_version required")
    rulesets = raw.get("rulesets")
    positions = raw.get("positions")
    _check(isinstance(rulesets, list) and rulesets, "rulesets required")
    _check(isinstance(positions, list) and positions, "positions required")
    ids = [r["fixture_id"] for r in rulesets]
    _check(len(ids) == len(set(ids)), "ruleset fixture ids must be unique")
    ruleset_ids = set(ids)
    pos_ids = [p["fixture_id"] for p in positions]
    _check(len(pos_ids) == len(set(pos_ids)), "position fixture ids must be unique")
    for pos in positions:
        _check(pos["ruleset_fixture_id"] in ruleset_ids, "position references unknown ruleset")
        _check(isinstance(pos["action_prefix"], list), "action_prefix must be a list")
        _check(isinstance(pos["expected_categories"], list), "expected_categories must be a list")


def manifest_to_json(manifest: SuiteManifest) -> str:
    return json.dumps(asdict(manifest), sort_keys=True, ensure_ascii=True)


def manifest_from_dict(raw: Mapping[str, Any]) -> SuiteManifest:
    validate_manifest(raw)
    return SuiteManifest(
        schema_version=int(raw["schema_version"]),
        suite_version=str(raw["suite_version"]),
        generator_version=str(raw["generator_version"]),
        commit=str(raw.get("commit", "")),
        rulesets=tuple(
            RuleSetFixtureSpec(
                fixture_id=str(r["fixture_id"]),
                generator_mode=str(r["generator_mode"]),
                board_size=int(r["board_size"]),
                ruleset_seed=int(r["ruleset_seed"]),
                generator_options=dict(r.get("generator_options", {})),
                movement_buckets=tuple(r.get("movement_buckets", ())),
                promotion_buckets=tuple(r.get("promotion_buckets", ())),
                drop_buckets=tuple(r.get("drop_buckets", ())),
            )
            for r in raw["rulesets"]
        ),
        positions=tuple(
            PositionFixtureSpec(
                fixture_id=str(p["fixture_id"]),
                ruleset_fixture_id=str(p["ruleset_fixture_id"]),
                action_prefix=tuple(dict(a) for a in p["action_prefix"]),
                expected_categories=tuple(str(c) for c in p["expected_categories"]),
                playout_seed=int(p.get("playout_seed", 0)),
            )
            for p in raw["positions"]
        ),
    )


def manifest_from_json(text: str) -> SuiteManifest:
    return manifest_from_dict(json.loads(text))


def write_json(path: str | Path, data: Any) -> None:
    Path(path).write_text(json.dumps(data, sort_keys=True, ensure_ascii=True), encoding="utf-8")


def medians_min_max(values: list[float]) -> dict[str, float]:
    """Median/min/max of a numeric sample (stable sort)."""
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return {"median": 0.0, "min": 0.0, "max": 0.0, "count": 0}
    mid = n // 2
    median = ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
    return {
        "median": median,
        "min": ordered[0],
        "max": ordered[-1],
        "count": n,
    }
