"""Memory + optional disk caches for evaluation profiles."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from collections import OrderedDict
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ...rules.compiled import CompiledRuleSet
from .analyzer import MovementCapabilityProfile, build_movement_capability, movement_signature
from .config import EvaluationConfig, config_hash
from .profile import PieceValueProfile, RuleSetEvaluationProfile, build_ruleset_profile


def default_cache_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "GenericChess" / "cache"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "GenericChess"
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "generic_chess"


class _MemoryCache:
    """Small thread-safe LRU cache used by both profile caches."""

    def __init__(self, max_entries: int) -> None:
        self._max = max_entries
        self._data: OrderedDict[Any, Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any | None:
        with self._lock:
            value = self._data.get(key)
            if value is not None:
                self._data.move_to_end(key)
            return value

    def put(self, key: Any, value: Any) -> None:
        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            while len(self._data) > self._max:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class MovementCapabilityCache:
    """Geometry-level cache keyed by board size + canonical signature + config."""

    def __init__(self, max_entries: int = 512) -> None:
        self._memory = _MemoryCache(max_entries)

    def key(self, n: int, signature: str, config: EvaluationConfig) -> tuple:
        return (n, signature, config.evaluator_version, config_hash(config))

    def get_or_build(
        self,
        n: int,
        atoms,
        config: EvaluationConfig,
    ) -> tuple[MovementCapabilityProfile, bool]:
        signature = movement_signature(atoms)
        key = self.key(n, signature, config)
        cached = self._memory.get(key)
        if cached is not None:
            return cached, True
        profile = build_movement_capability(n, atoms, config)
        self._memory.put(key, profile)
        return profile, False

    def clear(self) -> None:
        self._memory.clear()


class EvaluationProfileCache:
    """RuleSet-level profile cache with memory and optional disk layers."""

    def __init__(
        self,
        *,
        memory_max_entries: int = 64,
        disk_dir: str | Path | None = None,
        use_disk: bool = True,
        capability_cache: MovementCapabilityCache | None = None,
    ) -> None:
        self._memory = _MemoryCache(memory_max_entries)
        self._disk_dir = Path(disk_dir) if disk_dir is not None else None
        self._use_disk = use_disk
        self._lock = threading.Lock()
        self._capability_cache = capability_cache or MovementCapabilityCache()

    def _memory_key(self, compiled: CompiledRuleSet, config: EvaluationConfig) -> tuple:
        return (compiled.ruleset_fingerprint, config.evaluator_version, config_hash(config))

    def _disk_path(self, compiled: CompiledRuleSet, config: EvaluationConfig) -> Path:
        fp = compiled.ruleset_fingerprint[:16]
        return (self._disk_dir or default_cache_dir()) / f"profile-{fp}-{config_hash(config)[:12]}.json"

    def get_or_build(
        self, compiled: CompiledRuleSet, config: EvaluationConfig
    ) -> tuple[RuleSetEvaluationProfile, bool]:
        key = self._memory_key(compiled, config)
        cached = self._memory.get(key)
        if cached is not None:
            return cached, True
        with self._lock:
            cached = self._memory.get(key)
            if cached is not None:
                return cached, True
            disk_profile = self._load_disk(compiled, config)
            if disk_profile is not None:
                self._memory.put(key, disk_profile)
                return disk_profile, True
            profile = build_ruleset_profile(
                compiled, config, capability_cache=self._capability_cache
            )
            self._memory.put(key, profile)
            self._store_disk(profile)
            return profile, False

    def _load_disk(
        self, compiled: CompiledRuleSet, config: EvaluationConfig
    ) -> RuleSetEvaluationProfile | None:
        if not self._use_disk:
            return None
        path = self._disk_path(compiled, config)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if (
            raw.get("schema_version") != 1
            or raw.get("evaluator_version") != config.evaluator_version
            or raw.get("ruleset_fingerprint") != compiled.ruleset_fingerprint
            or raw.get("config_hash") != config_hash(config)
        ):
            return None
        try:
            return _profile_from_dict(raw)
        except (KeyError, TypeError, ValueError):
            return None

    def _store_disk(self, profile: RuleSetEvaluationProfile) -> None:
        if not self._use_disk:
            return
        directory = self._disk_dir or default_cache_dir()
        try:
            directory.mkdir(parents=True, exist_ok=True)
            path = self._disk_path_for(profile)
            fd, tmp = tempfile.mkstemp(dir=str(directory), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(_profile_to_dict(profile), fh, sort_keys=True)
                os.replace(tmp, path)
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
        except OSError:
            pass  # disk cache is best-effort; never fail the search because of it

    def _disk_path_for(self, profile: RuleSetEvaluationProfile) -> Path:
        directory = self._disk_dir or default_cache_dir()
        fp = profile.ruleset_fingerprint[:16]
        return directory / f"profile-{fp}-{profile.config_hash[:12]}.json"

    def clear(self) -> None:
        self._memory.clear()


def _profile_to_dict(profile: RuleSetEvaluationProfile) -> dict[str, Any]:
    return {
        "schema_version": profile.schema_version,
        "evaluator_version": profile.evaluator_version,
        "ruleset_fingerprint": profile.ruleset_fingerprint,
        "config_hash": profile.config_hash,
        "median_non_anchor_value": profile.median_non_anchor_value,
        "board_value_by_type": dict(profile.board_value_by_type),
        "hand_value_by_base_type": dict(profile.hand_value_by_base_type),
        "promotion_gain_by_type": dict(profile.promotion_gain_by_type),
        "piece_profiles": {
            tid: asdict(p) for tid, p in profile.piece_profiles.items()
        },
    }


def _profile_from_dict(raw: dict[str, Any]) -> RuleSetEvaluationProfile:
    profiles = {
        tid: PieceValueProfile(
            type_id=p["type_id"],
            movement_signature=p["movement_signature"],
            raw_capability_score=p["raw_capability_score"],
            normalized_board_value=p["normalized_board_value"],
            normalized_hand_value=p["normalized_hand_value"],
            promotion_option_value=p["promotion_option_value"],
            drop_freedom_ratio=p["drop_freedom_ratio"],
            drop_mobility=p["drop_mobility"],
            is_anchor=p["is_anchor"],
            is_promotable=p["is_promotable"],
        )
        for tid, p in raw["piece_profiles"].items()
    }
    return RuleSetEvaluationProfile(
        ruleset_fingerprint=raw["ruleset_fingerprint"],
        schema_version=raw["schema_version"],
        evaluator_version=raw["evaluator_version"],
        config_hash=raw["config_hash"],
        piece_profiles=profiles,
        median_non_anchor_value=raw["median_non_anchor_value"],
        board_value_by_type=dict(raw["board_value_by_type"]),
        hand_value_by_base_type=dict(raw["hand_value_by_base_type"]),
        promotion_gain_by_type=dict(raw["promotion_gain_by_type"]),
    )
