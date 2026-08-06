"""Markdown / JSON / CSV report writers for the native-readiness audit."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .audit_schema import write_json


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def render_markdown(summary: dict) -> str:
    lines: list[str] = []
    env = summary.get("environment", {})
    lines.append("# GenericChess Native-Readiness Audit")
    lines.append("")
    lines.append("## 1. 环境")
    lines.append("")
    for key in ("os", "python", "cpu", "logical_cpus", "commit", "debug_build"):
        lines.append(f"* {key}: {_fmt(env.get(key, 'n/a'))}")
    lines.append("")

    suite = summary.get("suite", {})
    lines.append("## 2. Suite")
    lines.append("")
    lines.append(f"* suite version: {suite.get('name', 'n/a')}")
    lines.append(f"* RuleSet 数: {suite.get('ruleset_count', 0)}")
    lines.append(f"* position 数: {suite.get('position_count', 0)}")
    lines.append(f"* 棋盘尺寸: {suite.get('board_sizes', [])}")
    lines.append(f"* movement 分桶: {suite.get('movement_buckets', [])}")
    lines.append(f"* promotion 分桶: {suite.get('promotion_buckets', [])}")
    lines.append(f"* drop 分桶: {suite.get('drop_buckets', [])}")
    lines.append(f"* 已覆盖 categories: {suite.get('categories_covered', [])}")
    lines.append(f"* 未覆盖 categories: {suite.get('categories_missing', [])}")
    lines.append("")

    lines.append("## 3. 总体性能（node budget）")
    lines.append("")
    for budget, block in (summary.get("node_budget") or {}).items():
        agg = block.get("summary", {})
        lines.append(f"### {budget} nodes（fixtures: {block.get('fixtures', 0)}，runs: {agg.get('runs', 0)}）")
        lines.append("")
        lines.append(f"* NPS median/min/max: {agg.get('nodes_per_second', {})}")
        lines.append(f"* completed depth median: {agg.get('completed_depth', {}).get('median')}")
        lines.append(f"* qnode ratio median: {agg.get('qnode_ratio', {}).get('median')}")
        lines.append(f"* TT hit rate median: {agg.get('tt_hit_rate', {}).get('median')}")
        lines.append(f"* fallback runs: {agg.get('fallback_runs', 0)}")
        lines.append(f"* by board size: {agg.get('by_board_size', {})}")
        lines.append(f"* by movement bucket: {agg.get('by_movement_bucket', {})}")
        lines.append("")

    lines.append("## 4. 子系统占比（instrumented）")
    lines.append("")
    instrumented = summary.get("instrumented", [])
    if instrumented:
        shares = summary.get("conclusions", {}).get("instrumented_subsystem_shares", {})
        for name, share in sorted(shares.items()):
            lines.append(f"* {name}: {share:.2%}")
        lines.append("")
        for item in instrumented:
            lines.append(
                f"* {item['fixture_id']}: wall={item['wall_seconds']:.3f}s "
                f"nodes={item['nodes']} qnodes={item['qnodes']}"
            )
    else:
        lines.append("未启用 instrumentation（--instrument）。")
    lines.append("")

    lines.append("## 5. Core 微基准（每调用中位数，秒）")
    lines.append("")
    for item in summary.get("core_profiling", []):
        lines.append(f"### {item['fixture_id']} (legal={item.get('legal_actions')}, pseudo/legal={item.get('pseudo_legal_ratio')})")
        for name, timing in sorted(item.get("functions", {}).items()):
            lines.append(f"* {name}: {_fmt(timing.get('median', 0.0))}s")
        lines.append("")

    lines.append("## 6. Cache")
    lines.append("")
    for item in summary.get("cache", []):
        lines.append(
            f"* {item.get('ruleset_fingerprint')}: cold={item.get('cold_seconds', 0):.3f}s "
            f"warm={item.get('memory_warm_seconds', 0):.3f}s "
            f"disk={item.get('disk_warm_seconds', 0):.3f}s "
            f"serialized={item.get('serialized_bytes', 0)}B"
        )
    lines.append("")

    lines.append("## 7. Profiler")
    lines.append("")
    profiler = summary.get("profiler")
    if profiler:
        for item in profiler.get("cprofile", []):
            lines.append(f"### cProfile {item['fixture_id']}")
            lines.append("```")
            lines.append(item.get("top", ""))
            lines.append("```")
        for item in profiler.get("tracemalloc", []):
            lines.append(
                f"### tracemalloc {item['fixture_id']} peak={item.get('peak_bytes', 0)}"
            )
            for source in item.get("top_sources", []):
                lines.append(
                    f"* {source.get('location')}: {source.get('size_bytes')}B x {source.get('count')}"
                )
    else:
        lines.append("未运行 profiler（--profiler）。")
    lines.append("")

    lines.append("## 8. 结论")
    lines.append("")
    conclusions = summary.get("conclusions", {})
    for key, value in conclusions.items():
        lines.append(f"* {key}: {value}")
    lines.append("")
    lines.append("* 说明：node-budget 结果受单机环境影响；子系统占比用于定位瓶颈，不代表正常运行的绝对 NPS。")
    return "\n".join(lines)


def write_reports(summary: dict, out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "native_readiness_latest.json", summary)
    (out / "native_readiness_latest.md").write_text(
        render_markdown(summary), encoding="utf-8"
    )


def write_csv_detail(summary: dict, path: str | Path) -> None:
    rows: list[dict] = []
    for budget, block in (summary.get("node_budget") or {}).items():
        rows.extend(block.get("results", []))
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=sorted(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def merge_summaries(base: dict, extra: dict) -> dict:
    """Merge a second audit run's blocks into ``base`` (later runs win)."""
    merged = dict(base)
    node_budget = dict(base.get("node_budget") or {})
    for budget, block in (extra.get("node_budget") or {}).items():
        # Base (the richer run) wins for budgets it already contains; extra
        # only fills in missing budget tiers.
        node_budget.setdefault(budget, block)
    merged["node_budget"] = node_budget
    for key in (
        "instrumented",
        "instrumentation_overhead",
        "core_profiling",
        "cache",
        "profiler",
    ):
        if extra.get(key):
            merged[key] = extra[key]
    conclusions = dict(base.get("conclusions") or {})
    if extra.get("conclusions"):
        conclusions = extra["conclusions"]
    merged["conclusions"] = conclusions
    return merged
