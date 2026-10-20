"""Freeze one evaluation-only, fresh-root H=256 task2629 registration."""
from __future__ import annotations

import datetime
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2629/run"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    if RUN.exists():
        raise FileExistsError("task2629 registration is write-once")
    session = json.loads((ROOT / ".local_agent/session.json").read_text(encoding="utf-8"))
    if session.get("state") != "active" or session.get("thread_id") != "01a15880-7263-7e12-a0e0-e42959c0bfb9":
        raise ValueError("registration requires this active DEV_AUX session")
    pool_path = ROOT / "results/dev_aux/task2629/fresh-evaluation-roots.json"
    audit_path = ROOT / "results/dev_aux/task2629/fresh-evaluation-root-audit.json"
    pool_raw, audit_raw = pool_path.read_bytes(), audit_path.read_bytes()
    pool, audit = json.loads(pool_raw), json.loads(audit_raw)
    if pool.get("status") != "FRESH_OUTCOME_BLIND_EVALUATION_ROOTS_PREPARED_NOT_REGISTERED":
        raise ValueError("fresh root pool is not prospective")
    if audit.get("status") != "PASS_FRESH_EVALUATION_POOL_EXACT_HISTORY_AND_REPLAY_AUDIT":
        raise ValueError("independent fresh root audit did not pass")
    if audit.get("pool_sha256") != sha(pool_raw) or audit.get("exact_prior_intersections") != 0:
        raise ValueError("root audit does not bind the exact fresh pool")

    prior_run = ROOT / "results/dev_aux/task2628/run"
    training = json.loads((prior_run / "training-result.json").read_text(encoding="utf-8"))
    training_audit = json.loads((prior_run / "training-audit.json").read_text(encoding="utf-8"))
    prior_evaluation_audit = json.loads((prior_run / "evaluation-audit.json").read_text(encoding="utf-8"))
    prior_analysis = json.loads((prior_run / "corrected-analysis.json").read_text(encoding="utf-8"))
    if (training.get("status") != "COMPLETE"
            or training_audit.get("status") != "PASS_FULL_HISTORY_ACTUAL_TERMINAL_NODE_CAP_AND_TD_UPDATE_REPLAY"
            or prior_evaluation_audit.get("status") != "PASS_REGISTERED_SLOT_ACTUAL_TERMINAL_HISTORY_AND_CAP_AUDIT"
            or prior_analysis.get("status") != "PASS_PLAN_DERIVED_FINITE_ACTUAL_TERMINAL_COMPLETION_BOUNDS"):
        raise ValueError("reused model source does not have complete independent training/evaluation evidence")
    training_path = prior_run / "training-result.json"
    training_raw = training_path.read_bytes()
    if sha(training_raw) != training_audit.get("training_result_sha256"):
        raise ValueError("reused model result differs from its audit")
    if len(training.get("arms", [])) != 4:
        raise ValueError("unexpected frozen model arm set")

    caps = {}
    for row in pool["evaluation_roots"]:
        rule, family = row["rule_index"], row["family"]
        caps[f"{rule}:{family}"] = 20_000
    ordered = list(caps)
    random.Random(977422 + 15).shuffle(ordered)
    for index, key in enumerate(ordered):
        if index >= 8:
            caps[key] = 40_000

    source_paths = [
        "results/dev_aux/task2629/prepare_fresh_eval_roots.py",
        "results/dev_aux/task2629/audit_fresh_eval_roots.py",
        "results/dev_aux/task2629/freeze_study.py",
        "results/dev_aux/task2629/evaluate.py",
        "results/dev_aux/task2629/audit_evaluation.py",
        "results/dev_aux/task2629/analyze.py",
        "results/dev_aux/task2629/analyze_corrected.py",
        "results/dev_aux/task2629/launch_evaluation.py",
        "results/dev_aux/task2629/test_design.py",
        "results/dev_aux/task2629/fresh-evaluation-roots.json",
        "results/dev_aux/task2629/fresh-evaluation-root-audit.json",
        "results/dev_aux/task2627/source-inventory-v2.json",
        "results/dev_aux/task2627/rule15-successor-root-pools.json",
        "results/dev_aux/task2628/run/training-result.json",
        "results/dev_aux/task2628/run/training-audit.json",
        "results/dev_aux/task2628/run/evaluation-audit.json",
        "results/dev_aux/task2628/run/corrected-analysis.json",
        "results/dev_aux/task2628/run/plan.json",
        "results/dev_aux/task2628/feature_exposure.py",
        "results/dev_aux/task2621/fixed_scale.py",
        "results/dev_aux/task2492/learning.py",
        "results/dev_aux/task2492/episode.py",
        "results/dev_aux/task2511/generic.py",
        "results/dev_aux/task2392/reader.py",
        "generic_chess/session/session.py",
        "generic_chess/session/serialization.py",
        "generic_chess/rules/compiler.py",
        "generic_chess/rules/schema.py",
        "results/dev_aux/task2433/rules-15.json",
    ]
    pins = {path: sha((ROOT / path).read_bytes()) for path in source_paths}
    if pins["results/dev_aux/task2629/fresh-evaluation-roots.json"] != audit["pool_sha256"]:
        raise ValueError("fresh root pool changed after audit")

    seeds = [arm["seed"] for arm in training["arms"]]
    if seeds != [1977, 8173, 27182, 31415]:
        raise ValueError("reused model seed set invalid")
    initial_weights = {f"15:{arm['seed']}": arm["initial_weights"] for arm in training["arms"]}
    plan = {
        "task": "DEV_AUX2629_RULE15_FRESH_ROOT_EVALUATION_H256",
        "state": "FROZEN_BEFORE_EVALUATION",
        "question": "On a new exact-record-disjoint outcome-blind rules15 panel, does the already-frozen task2628 TDLeaf model differ from its exact initialization under actual terminal W/L/D when horizon is doubled without changing per-family node caps?",
        "scope": "Evaluation-only replication on one generated 4x4 semantic-action ruleset. Exact full-record exclusion from the pinned history inventory, prior task2627 roots and all task2628 trajectories only; no descendant/transposition/distributional/population/full-Generic claim.",
        "model_reuse": {"training_result_path": "results/dev_aux/task2628/run/training-result.json",
                        "training_result_sha256": sha(training_raw),
                        "training_audit_sha256": sha((prior_run / "training-audit.json").read_bytes()),
                        "original_plan_sha256": json.loads((prior_run / "registration.json").read_text())["plan_sha256"],
                        "retrain": False, "weights_mutated": False},
        "pool": {"path": "results/dev_aux/task2629/fresh-evaluation-roots.json",
                 "sha256": sha(pool_raw), "audit_path": "results/dev_aux/task2629/fresh-evaluation-root-audit.json",
                 "audit_sha256": sha(audit_raw), "evaluation_roots": 16,
                 "generator_seed": pool["selection"]["generator_seed"],
                 "family_range": pool["selection"]["family_range"],
                 "selection": "Outcome-blind eight-ply full histories; exact-record exclusions cover the prior inventory, task2627 pool, and every task2628 train/eval query/episode history; require same-owner R hand+board and promoted P-base/R-current."},
        "domain": {"rules": [15], "history_authority": "Complete GameSession; promotions, drops, auxiliary state and declaration semantics retained.",
                   "evaluator": "Exact task2492 Model and task2621 fixed-scale channels; coordinate0=1, scale10; no human priors."},
        "seeds": seeds,
        "search": {"algorithm": "task2492.learning.AlphaBeta", "depth": 2,
                   "quiescence": 0, "nodes_per_query": 8192,
                   "seconds_per_query": 2.0, "ordering_seed_base": 2622_000_000},
        "initialization": {"weights_by_rule_seed": initial_weights},
        "evaluation": {"endpoints": ["initial", "TDLeaf"], "slots": 256,
                       "construction": "1 rule x 4 frozen model seeds x 16 fresh roots x 2 learner colors x 2 frozen endpoints",
                       "H": 256, "hard_seconds": 1800,
                       "node_cap_by_rule_family": caps,
                       "paired_cap_assignment": "Eight roots at 20k and eight at 40k combined two-side nodes; fixed seed 977437.",
                       "foe": "uniform all-ones fixed Model at scale10",
                       "outcome": "Actual rule-terminal W/L/D only. Horizon, resource and non-scoring endpoints remain UNKNOWN; no draw imputation.",
                       "comparison": "128 paired fresh-root strata; UNKNOWN endpoints independently range over [-1,+1]. Finite completion bounds, not confidence intervals."},
        "cost": {"root_preparation_hard_seconds": 180, "root_audit_hard_seconds": 180,
                 "evaluation_hard_seconds": 1800, "evaluation_audit_hard_seconds": 180,
                 "variance_reserve_seconds": 1200, "conservative_all_in_bound_seconds": 3540,
                 "all_in_hard_cap_seconds": 6600, "chat_assessment_threshold_seconds": 7200,
                 "assessment_required_before_launch": False,
                 "basis": "Task2627 measured prep/audit 31.225/23.008s; task2628 evaluation 243.784s at H128. This plan budgets hard caps plus a 1200s reserve; H256 actual runtime is not guaranteed."},
        "no_frozen_caps_changed": True,
        "separate_registration_not_top_up": True,
        "analysis_rule": "Report task2629 independently; do not combine with task2628 after observing task2628 results.",
        "source_pins": pins,
    }
    RUN.mkdir(parents=True, exist_ok=False)
    plan_raw = json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False).encode() + b"\n"
    (RUN / "plan.json").write_bytes(plan_raw)
    reg = {"state": "REGISTERED_BEFORE_EVALUATION", "registered_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "session_id": session["id"], "thread_id": session["thread_id"], "plan_sha256": sha(plan_raw),
           "root_pools_sha256": sha(pool_raw), "root_pools_audit_sha256": sha(audit_raw),
           "source_pins": pins, "training_started": False, "training_result_reused": True,
           "evaluation_started": False, "expected_evaluation_slots": 256,
           "conservative_all_in_bound_seconds": 3540, "chat_assessment_required": False}
    reg_raw = json.dumps(reg, indent=2, sort_keys=True, ensure_ascii=False).encode() + b"\n"
    (RUN / "registration.json").write_bytes(reg_raw)
    eval_bind = {"state": "EVALUATION_BOUND_BEFORE_FIRST_SLOT",
                 "bound_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 "plan_sha256": sha(plan_raw), "training_result_sha256": sha(training_raw),
                 "root_pools_sha256": sha(pool_raw), "expected_slots": 256,
                 "model_source_task": 2628, "evaluation_started": False}
    (RUN / "evaluation-registration.json").write_text(json.dumps(eval_bind, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": reg["state"], "plan_sha256": sha(plan_raw),
                      "registration_sha256": sha(reg_raw), "slots": 256,
                      "H": 256, "all_in_bound_seconds": 3540,
                      "assessment_required": False}, indent=2))


if __name__ == "__main__":
    main()
