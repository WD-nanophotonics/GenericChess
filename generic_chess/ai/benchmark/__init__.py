"""Paired-control search benchmark for SearchTuning ablation (Qt-free)."""

from .profiles import (
    ALL_PROFILES,
    PROFILES,
    BenchmarkProfile,
    all_profiles,
    profile_by_name,
)
from .runner import RunConfig, run_benchmark
from .suite import DEFAULT_SUITE, SuitePosition, build_position

__all__ = [
    "ALL_PROFILES",
    "PROFILES",
    "BenchmarkProfile",
    "all_profiles",
    "profile_by_name",
    "RunConfig",
    "run_benchmark",
    "DEFAULT_SUITE",
    "SuitePosition",
    "build_position",
]
