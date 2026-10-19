"""Independent accounting/replay audit and conservative paired bounds."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json

from results.dev_aux.task2606.train import compiled, restore

D = Path("results/dev_aux/task2609")
plan = json.loads((D / "eval-plan.json").read_text(encoding="utf-8"))
reg = json.loads((D / "registration.json").read_text(encoding="utf-8"))
manifest = json.loads((D / "root-manifest.json").read_text(encoding="utf-8"))
run = json.loads((D / "eval-result.json").read_text(encoding="utf-8"))
assert run["status"] == "COMPLETE" and run["expected"] == run["actual"] == 1536 and run["missing"] == 0
assert hashlib.sha256((D / "eval-plan.json").read_bytes()).hexdigest() == reg["eval_plan_sha256"]
assert hashlib.sha256((D / "root-manifest.json").read_bytes()).hexdigest() == reg["root_manifest_sha256"]
for path, digest in reg["source_pins"].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path

games = [json.loads(line) for line in (D / "eval-games.jsonl").read_text(encoding="utf-8").splitlines()]
queries = [json.loads(line) for line in (D / "eval-queries.jsonl").read_text(encoding="utf-8").splitlines()]
slots = [tuple(slot) for slot in plan["slots"]]
assert len(games) == len(slots) and len({tuple(g["slot"]) for g in games}) == len(slots)
assert {tuple(g["slot"]) for g in games} == set(slots)
by_slot = defaultdict(list)
for query in queries:
    by_slot[tuple(query["slot"])].append(query)
assert set(by_slot) == set(slots)

compilers = {rule: compiled(rule) for rule in plan["rules"]}
outcomes = {}
for game in games:
    slot = tuple(game["slot"])
    rule, seed, family, color, endpoint, _ = slot
    assert game["initial_record"] == manifest["roots"][f"{rule}:{family}"]
    qs = by_slot[slot]
    assert len(qs) == game["queries"]
    assert sum(q["nodes"] for q in qs) == game["nodes"]
    expected_record = game["initial_record"]
    for query in qs:
        assert query["record_before"] == expected_record
        assert query["actor"] in (0, 1)
        if query["complete"]:
            # Complete search applies exactly one legal action; its recorded
            # post-state becomes the next query's pre-state.
            assert query["record_after"] != query["record_before"]
        else:
            assert query["record_after"] == query["record_before"]
        expected_record = query["record_after"]
    assert expected_record == game["record"]
    replay = restore(rule, compilers[rule], game["record"])
    assert replay.record() == game["record"] and replay.terminal() == game["outcome"]
    assert game["reward"] == (None if game["outcome"] is None else game["outcome"] * (1 if color == 0 else -1))
    outcomes[(rule, seed, family, color, endpoint)] = game["reward"]

assert sum(q["nodes"] for q in queries) == run["nodes"]
assert len(queries) == run["queries"]
assert sum(g["outcome"] is not None for g in games) == run["actual_terminal"]
assert sum(g["outcome"] is None for g in games) == run["unknown"]

labels = ("initial", "TD95", "LocalLambda")
wdl = {label: Counter() for label in labels}
for (*_, label), reward in outcomes.items():
    wdl[label]["UNKNOWN" if reward is None else {-1: "LOSS", 0: "DRAW", 1: "WIN"}[reward]] += 1

def compare(left, right):
    diffs, uncertain = [], 0
    for rule in plan["rules"]:
        for seed in plan["seeds"]:
            for family in manifest["selected_families"][str(rule)]:
                for color in (0, 1):
                    a, b = outcomes[(rule, seed, family, color, left)], outcomes[(rule, seed, family, color, right)]
                    if a is None or b is None:
                        diffs.append((-2, 2)); uncertain += 1
                    else:
                        diffs.append((a - b, a - b))
    lo, hi = sum(x[0] for x in diffs), sum(x[1] for x in diffs)
    n = len(diffs)
    return {"left": left, "right": right, "strata": n, "uncertain_pairs": uncertain,
            "difference_sum_bounds": [lo, hi], "difference_mean_bounds": [lo / n, hi / n]}

comparisons = [compare("TD95", "initial"), compare("LocalLambda", "initial"), compare("LocalLambda", "TD95")]
audit = {
    "status": "PASS", "task": "DEV_AUX2609", "slots": len(games), "unique_slots": len(outcomes),
    "unique_full_start_roots": len(manifest["roots"]), "queries": len(queries),
    "search_nodes": sum(q["nodes"] for q in queries),
    "complete_searches": sum(q["complete"] for q in queries),
    "incomplete_searches": sum(not q["complete"] for q in queries),
    "actual_terminals": sum(g["outcome"] is not None for g in games),
    "unknown_horizons": sum(g["outcome"] is None for g in games),
    "replayed_terminals": len(games), "wdl_by_endpoint": {k: dict(v) for k, v in wdl.items()},
    "paired_reward_bounds": comparisons,
    "scope": "Finite 64-root exact-start-disjoint evaluation of frozen task2606 models against the uniform opponent. Not a descendant-state/history holdout or broad transfer claim.",
}
(D / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
lines = [
    "# task2609 — Exact-start-disjoint finite evaluation",
    "",
    "## Design and provenance",
    "",
    "Evaluation-only follow-up to task2608's preserved pre-first-slot runner failure. The frozen task2606 model result and outcome-blind task2607 selection were reused unchanged. This corrected registration explicitly includes the four-ply prefix omitted from task2608. Each selected root's complete GameSession record (ruleset fingerprint plus four actions) was preflight-replayed before any evaluation record was written.",
    "",
    f"- Registration: `{reg['eval_plan_sha256']}`; root manifest: `{reg['root_manifest_sha256']}`.",
    f"- Slots: {len(games)}/1536; distinct roots: {len(manifest['roots'])}/64; runtime: {run['seconds']:.3f}s; nodes: {run['nodes']:,}; queries: {run['queries']:,}.",
    f"- Actual terminal outcomes: {run['actual_terminal']}; horizon/other UNKNOWN: {run['unknown']}; incomplete searches: {audit['incomplete_searches']}.",
    "- All outcome records and query ledgers reconcile by slot; each final history and claimed terminal was replayed through the Generic rule runtime.",
    "",
    "## Outcomes (learner perspective)",
    "",
    "| Endpoint | Wins | Draws | Losses | UNKNOWN |",
    "|---|---:|---:|---:|---:|",
]
for label in labels:
    c = wdl[label]
    lines.append(f"| {label} | {c['WIN']} | {c['DRAW']} | {c['LOSS']} | {c['UNKNOWN']} |")
lines += ["", "Paired reward differences give every pair containing UNKNOWN the full [-2,+2] range; exact pairs use their observed reward difference.", "", "| Contrast (left − right) | Exact pairs / 512 | UNKNOWN pairs | Mean difference bound |", "|---|---:|---:|---:|"]
for c in comparisons:
    exact = c["strata"] - c["uncertain_pairs"]
    lines.append(f"| {c['left']} − {c['right']} | {exact}/512 | {c['uncertain_pairs']} | [{c['difference_mean_bounds'][0]:.4f}, {c['difference_mean_bounds'][1]:.4f}] |")
lines += [
    "", "## Interpretation and limits", "",
    "This corrects task2608's implementation failure without replacing or deleting its registration and zero-row evidence. It evaluates the already frozen task2606 models on exact-start-history-disjoint roots; no model or parameter selection was performed using these outcomes. UNKNOWN was not converted to a draw.",
    "",
    "The selected roots are disjoint from the 512 possible task2606 training-family start records, but descendants are not proven disjoint and task2606 training trajectories are not an independent generalization guarantee. Therefore this is a finite, fixed-model diagnostic panel, not a fully independent holdout or evidence of broad Generic transfer. The 93 UNKNOWN outcomes widen comparisons; LocalLambda's comparison with TD95 remains unresolved whenever its bound includes zero.",
    "",
    "The runner and audit code are task-specific evidence tools; they do not change engine defaults, UI, or primary checkout.",
]
(D / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
