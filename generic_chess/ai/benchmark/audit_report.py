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
    lines.append(f"* manifest RuleSet 数: {suite.get('full_suite', {}).get('ruleset_count', suite.get('ruleset_count', 0))}")
    lines.append(f"* manifest position 数: {suite.get('full_suite', {}).get('position_count', suite.get('position_count', 0))}")
    lines.append(f"* executed RuleSet 数: {suite.get('executed_ruleset_count', suite.get('ruleset_count', 0))}")
    lines.append(f"* executed position 数: {suite.get('executed_position_count', suite.get('position_count', 0))}")
    lines.append(f"* requested budget tiers: {summary.get('requested_budget_tiers', [])}")
    lines.append(f"* completed budget tiers: {summary.get('completed_budget_tiers', [])}")
    lines.append(f"* skipped/timeout/failed runs: {summary.get('skipped_runs', 0)}/{summary.get('timeout_runs', 0)}/{summary.get('failed_runs', 0)}")
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
        lines.append(f"* total_nps median/min/max: {agg.get('total_nps', {})}")
        lines.append(f"* main_nps median: {agg.get('main_nps', {}).get('median')}")
        lines.append(f"* q_nps median: {agg.get('q_nps', {}).get('median')}")
        lines.append(f"* completed depth median: {agg.get('completed_depth', {}).get('median')}")
        lines.append(f"* qnode ratio median: {agg.get('qnode_ratio', {}).get('median')}")
        lines.append(f"* qnode share median: {agg.get('qnode_share', {}).get('median')}")
        lines.append(f"* TT hit rate median: {agg.get('tt_hit_rate', {}).get('median')}")
        lines.append(f"* fallback runs: {agg.get('fallback_runs', 0)}")
        lines.append(f"* by board size: {agg.get('by_board_size', {})}")
        lines.append(f"* by board size (total_nps): {agg.get('by_board_size_total_nps', {})}")
        lines.append(f"* by movement bucket: {agg.get('by_movement_bucket', {})}")
        lines.append(f"* by movement bucket (total_nps): {agg.get('by_movement_bucket_total_nps', {})}")
        lines.append("")

    lines.append("## 4. 子系统占比（instrumented）")
    lines.append("")
    instrumented = summary.get("instrumented", [])
    if instrumented:
        phase = summary.get("conclusions", {}).get("phase_inclusive_shares", {})
        lines.append("Phase inclusive shares（quiescence 为整棵 qsearch 调用树）:")
        for name, share in sorted(phase.items()):
            lines.append(f"* {name}: {share:.2%}")
        shares = summary.get("conclusions", {}).get("instrumented_subsystem_shares", {})
        lines.append("Direct-measured subsystem shares（仅 main search 中被包裹的函数调用）:")
        for name, share in sorted(shares.items()):
            lines.append(f"* {name}: {share:.2%}")
        lines.append("")
        for item in instrumented:
            lines.append(
                f"* {item['fixture_id']}: wall={item['wall_seconds']:.3f}s "
                f"nodes={item['nodes']} qnodes={item['qnodes']} "
                f"phase={item['phase_inclusive_seconds']}"
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
    lines.append("## 9. 定向 fixture 覆盖")
    lines.append("")
    targeted = summary.get("targeted_fixtures", [])
    for item in targeted:
        lines.append(f"* {item['fixture_id']}: {item['categories']}")
    uncovered = summary.get("targeted_categories_uncovered", [])
    lines.append(f"* 仍缺失类别: {uncovered}")
    lines.append("")

    before_after = summary.get("before_after", {})
    if before_after.get("fixtures"):
        lines.append("## 10. qsearch 修改前后（同一命令，10k nodes, 1 warm-up + 3 repeats）")
        lines.append("")
        lines.append("| fixture | baseline wall (s) | after wall (s) | wall ratio | baseline nodes | after nodes |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for row in before_after["fixtures"]:
            lines.append(
                f"| {row['fixture_id']} | {row['baseline_wall_seconds']} | "
                f"{row['after_wall_seconds']} | {row['wall_ratio']} | "
                f"{row['baseline_total_nodes']} | {row['after_total_nodes']} |"
            )
        lines.append("")

    lazy_ab = summary.get("lazy_successor_experiment", {})
    if lazy_ab.get("rows"):
        lines.append("## 11. Lazy successor 实验（eager vs lazy, 10k nodes）")
        lines.append("")
        lines.append("| fixture | action/depth equal | eager total_nps | lazy total_nps | lazy materialized |")
        lines.append("| --- | --- | ---: | ---: | ---: |")
        for row in lazy_ab["rows"]:
            lines.append(
                f"| {row['fixture_id']} | {row['best_action_equal'] and row['depth_equal']} | "
                f"{row['eager']['total_nps']} | {row['lazy']['total_nps']} | "
                f"{row['lazy_materialized']} |"
            )
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
    requested = list(base.get("requested_budget_tiers") or [])
    for tier in extra.get("requested_budget_tiers") or []:
        if tier not in requested:
            requested.append(tier)
    merged["requested_budget_tiers"] = requested
    completed = list(base.get("completed_budget_tiers") or [])
    for tier in extra.get("completed_budget_tiers") or []:
        if tier not in completed:
            completed.append(tier)
    merged["completed_budget_tiers"] = completed
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
