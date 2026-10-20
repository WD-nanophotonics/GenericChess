"""Independent exact-slot, legality, terminal, and node-cap evaluation audit."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.generic_session_win_proof import SessionChoice
from results.dev_aux.task2511.generic import NonScoringTerminal
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

RUN = ROOT / "results/dev_aux/task2622/run"
RULES = (271001, 271002, 271003, 271004)
SEEDS = (1977, 8173, 27182, 31415)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def rows(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def audit() -> dict:
    out = RUN / "evaluation-audit.json"
    if out.exists():
        raise FileExistsError("evaluation audit is write-once")
    plan_raw, reg_raw = (RUN / "plan.json").read_bytes(), (RUN / "registration.json").read_bytes()
    plan, reg = json.loads(plan_raw), json.loads(reg_raw)
    eval_reg = json.loads((RUN / "evaluation-registration.json").read_text(encoding="utf-8"))
    result = json.loads((RUN / "eval-result.json").read_text(encoding="utf-8"))
    if result["status"] != "COMPLETE" or result["missing"] != 0 or result["completed_slots"] != 1024:
        raise ValueError("evaluation is partial or missing registered slots")
    if sha(plan_raw) != reg["plan_sha256"] or eval_reg["plan_sha256"] != reg["plan_sha256"]:
        raise ValueError("plan/evaluation binding mismatch")
    training_raw = (RUN / "training-result.json").read_bytes()
    if sha(training_raw) != eval_reg["training_result_sha256"]:
        raise ValueError("evaluation model binding mismatch")
    for path, expected in reg["source_pins"].items():
        if sha((ROOT / path).read_bytes()) != expected:
            raise ValueError(f"source pin mismatch: {path}")
    pool = json.loads((ROOT / "results/dev_aux/task2622/root-pools-v2.json").read_text(encoding="utf-8"))
    roots = {(r["rule"], r["family"]): r for r in pool["evaluation_roots"]}
    compiled = {rule: compile_ruleset_for_execution(ruleset_from_dict(json.loads(
        (ROOT / f"results/dev_aux/task2525/rules-{rule}.json").read_text(encoding="utf-8")))) for rule in RULES}
    games = {}
    for game in rows(RUN / "eval-games.jsonl"):
        slot = tuple(game["slot"])
        if slot in games:
            raise ValueError("duplicate evaluation slot")
        games[slot] = game
    expected = {(rule, seed, root["family"], color, endpoint)
                for rule in RULES for seed in SEEDS
                for root in pool["evaluation_roots"] if root["rule"] == rule
                for color in (0, 1) for endpoint in ("initial", "TDLeaf")}
    if set(games) != expected:
        raise ValueError("evaluation slot set differs from registration")
    queries = defaultdict(list)
    for query in rows(RUN / "eval-queries.jsonl"):
        queries[tuple(query["slot"])].append(query)
    if set(queries) != expected:
        raise ValueError("query slot set differs from complete evaluation")

    wdl = Counter()
    node_total = query_total = 0
    for slot in sorted(expected):
        rule, _seed, family, color, _endpoint = slot
        game = games[slot]
        root = roots[(rule, family)]
        if game["initial_record"] != root["record"]:
            raise ValueError("slot root differs from registered full history")
        env = FixedScaleSessionEnv(GameSession.replay(compiled[rule],
            deserialize_game_record(json.dumps(root["record"]))))
        if env.record() != root["record"]:
            raise ValueError("evaluation root replay mismatch")
        expected_record = root["record"]
        qs = queries[slot]
        if len(qs) != game["queries"]:
            raise ValueError("query count differs from game receipt")
        for q in qs:
            if q["record_before"] != expected_record or q["actor"] != env.player():
                raise ValueError("query actor/full-history prefix mismatch")
            if type(q["nodes"]) is not int or q["nodes"] < 0 or q["nodes"] > q["requested_nodes"]:
                raise ValueError("query exceeded requested node allowance")
            if q["complete"]:
                record_after = deserialize_game_record(json.dumps(q["record_after"]))
                if len(record_after.actions) != len(env.session.to_record().actions) + 1:
                    raise ValueError("complete search did not append one legal action")
                env.push(SessionChoice("ACTION", action=record_after.actions[-1]))
            if env.record() != q["record_after"]:
                raise ValueError("query action/full-history replay mismatch")
            expected_record = q["record_after"]
            node_total += q["nodes"]
            query_total += 1
        if game["final_record"] != env.record() or game["nodes"] != sum(q["nodes"] for q in qs):
            raise ValueError("game record/node sum mismatch")
        cap = plan["evaluation"]["node_cap_by_rule_family"][f"{rule}:{family}"]
        if game["node_cap"] != cap or game["nodes"] > cap:
            raise ValueError("slot combined two-side node cap mismatch")
        try:
            actual = env.terminal()
        except NonScoringTerminal:
            actual = None
        if actual != game["actual_outcome"]:
            raise ValueError("actual W/L/D versus UNKNOWN mismatch")
        reward = None if actual is None else actual * (1 if color == 0 else -1)
        if reward != game["reward"]:
            raise ValueError("learner-relative reward mismatch")
        wdl[(game["slot"][4], "UNKNOWN" if reward is None else {-1:"LOSS",0:"DRAW",1:"WIN"}[reward])] += 1

    if node_total != result["nodes"] or query_total != result["queries"]:
        raise ValueError("evaluation result totals mismatch")
    audited = {"status": "PASS_1024_SLOT_ACTUAL_TERMINAL_HISTORY_AND_CAP_AUDIT",
               "slots": len(expected), "queries": query_total, "nodes": node_total,
               "actual_terminal": sum(v for (e, state), v in wdl.items() if state != "UNKNOWN"),
               "UNKNOWN": sum(v for (e, state), v in wdl.items() if state == "UNKNOWN"),
               "WDL_by_endpoint": {e: {state: wdl[(e, state)] for state in ("WIN", "DRAW", "LOSS", "UNKNOWN")} for e in ("initial", "TDLeaf")},
               "evaluation_result_sha256": sha((RUN / "eval-result.json").read_bytes()),
               "scope": "Finite registered panel; complete GameSession history and rule terminals replayed. No population or broader Generic claim."}
    out.write_text(json.dumps(audited, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audited, indent=2, sort_keys=True))
    return audited


if __name__ == "__main__":
    audit()
