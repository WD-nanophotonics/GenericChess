"""Paired-control search benchmark for SearchTuning ablation (Qt-free)."""

from .audit_report import merge_summaries, render_markdown, write_reports
from .audit_schema import SuiteManifest, manifest_from_json, validate_manifest
from .correctness_corpus import build_corpus, write_corpus
from .native_readiness import AuditConfig, run_audit, write_full_suite_manifest
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
    "AuditConfig",
    "run_audit",
    "write_full_suite_manifest",
    "SuiteManifest",
    "validate_manifest",
    "manifest_from_json",
    "write_reports",
    "render_markdown",
    "merge_summaries",
    "build_corpus",
    "write_corpus",
]
