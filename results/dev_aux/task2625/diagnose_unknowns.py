"""Explain registered-panel UNKNOWN endings without relabeling outcomes."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent / "run"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict:
    audit_path = RUN / "evaluation-audit.json"
    games_path = RUN / "eval-games.jsonl"
    out = RUN / "unknown-diagnostic.json"
    if out.exists():
        raise FileExistsError("UNKNOWN diagnostic is write-once")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS_1024_SLOT_ACTUAL_TERMINAL_HISTORY_AND_CAP_AUDIT":
        raise ValueError("requires complete independent terminal/cap audit")
    games = [json.loads(line) for line in games_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(games) != 1024:
        raise ValueError("unexpected registered slot count")
    by_rule: dict[str, list[dict]] = {}
    for game in games:
        by_rule.setdefault(str(game["slot"][0]), []).append(game)
    strata = {}
    for rule, rows in sorted(by_rule.items()):
        outcome = Counter(str(row["actual_outcome"]) for row in rows)
        ending = Counter(row["ending"] for row in rows)
        unknowns = [row for row in rows if row["actual_outcome"] is None]
        unknown_ending = Counter(row["ending"] for row in unknowns)
        cap_hits = sum(row["nodes"] == row["node_cap"] for row in rows)
        if any(row["ending"] != "HORIZON_UNKNOWN" for row in unknowns):
            raise ValueError(f"unexpected UNKNOWN reason in rule {rule}")
        if cap_hits:
            raise ValueError(f"node cap hit in rule {rule}; investigate censoring")
        strata[rule] = {"slots": len(rows), "actual_outcomes": dict(outcome),
                        "endings": dict(ending), "unknown_endings": dict(unknown_ending),
                        "node_cap_hits": cap_hits,
                        "unknown_fraction": len(unknowns) / len(rows)}
    result = {"status": "PASS_UNKNOWN_CENSORING_REASON_AUDIT",
              "evaluation_audit_sha256": sha(audit_path),
              "evaluation_games_sha256": sha(games_path),
              "by_rule": strata,
              "interpretation": "All UNKNOWN slots in this panel are nonterminal H=128 horizon censoring; no rule family hit its node cap. UNKNOWN remains censored, never a draw."}
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    run()
