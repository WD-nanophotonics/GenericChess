"""Write-once preregistration for the task2628 rules15 comparison."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.local_agent.common import read_json
from tools.local_agent.environment import require_identity

RUN = ROOT / "results/dev_aux/task2628/run"
RULES = (15,)
SEEDS = (1977, 8173, 27182, 31415)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canon(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def initial_vector(seed: int, dimension: int) -> list[float]:
    if dimension < 1:
        raise ValueError("fixed-scale model must contain its base coordinate")
    rng = random.Random(seed)
    return [1.0] + [rng.uniform(0.5, 1.5) for _ in range(dimension - 1)]


def main() -> None:
    require_identity()
    if RUN.exists():
        raise FileExistsError("task2628/run already exists; do not replace a registration or execution")
    session = read_json(ROOT / ".local_agent/session.json")
    if session.get("state") != "active" or session.get("thread_id") != "01a15880-7263-7e12-a0e0-e42959c0bfb9":
        raise ValueError("registration requires the active DEV_AUX session bound to this chat")
    pool_path = ROOT / "results/dev_aux/task2627/rule15-successor-root-pools.json"
    audit_path = ROOT / "results/dev_aux/task2627/rule15-successor-pool-audit.json"
    pool_raw, audit_raw = pool_path.read_bytes(), audit_path.read_bytes()
    pool, audit = json.loads(pool_raw), json.loads(audit_raw)
    if pool.get("status") != "OUTCOME_BLIND_MECHANISM_ACTIVE_ROOTS_PREPARED_NOT_REGISTERED":
        raise ValueError("root pool is not a prepared task")
    if audit.get("status") != "PASS_SOURCE_HASH_FULL_HISTORY_REPLAY_MECHANISM_FEATURE_AND_SPLIT_AUDIT":
        raise ValueError("exact-history audit did not pass")
    if audit.get("pool_sha256") != sha(pool_raw):
        raise ValueError("root pool audit pins a different root pool")

    caps = {}
    initial_weights = {}
    for rule in RULES:
        families = [row["family"] for row in pool["evaluation_roots"] if row["rule_index"] == rule]
        if len(families) != 16 or len(set(families)) != 16:
            raise ValueError(f"rule {rule}: evaluation family count invalid")
        ordered = list(families)
        random.Random(977422 + rule).shuffle(ordered)
        for i, family in enumerate(ordered):
            caps[f"{rule}:{family}"] = 20_000 if i < 8 else 40_000

        training_roots = [row for row in pool["training_roots"] if row["rule_index"] == rule]
        if len(training_roots) != 120 or len({len(row["channels"]) for row in training_roots}) != 1:
            raise ValueError(f"rule {rule}: training roots or channel dimensions are inconsistent")
        dimension = len(training_roots[0]["channels"])
        for seed in SEEDS:
            vector = initial_vector(seed, dimension)
            initial_weights[f"{rule}:{seed}"] = vector

    for seed in SEEDS:
        vectors = [initial_weights[f"{rule}:{seed}"] for rule in RULES]
        if any(vector != vectors[0] for vector in vectors[1:]):
            raise ValueError(f"seed {seed}: dynamic channel dimensions differ across rules")

    source_paths = [
        "results/dev_aux/task2627/prepare_rule15_successor_roots.py",
        "results/dev_aux/task2627/audit_rule15_successor_pool.py",
        "results/dev_aux/task2627/rule15-successor-root-pools.json",
        "results/dev_aux/task2627/rule15-successor-pool-audit.json",
        "results/dev_aux/task2628/train.py",
        "results/dev_aux/task2628/evaluate.py",
        "results/dev_aux/task2628/audit_training.py",
        "results/dev_aux/task2628/bind_evaluation.py",
        "results/dev_aux/task2628/audit_evaluation.py",
        "results/dev_aux/task2628/analyze.py",
        "results/dev_aux/task2628/launch_training.py",
        "results/dev_aux/task2628/freeze_study.py",
        "results/dev_aux/task2628/test_design.py",
        "results/dev_aux/task2627/source-inventory-v2.json",
        "results/dev_aux/task2627/successor-cost-bound.json",
        "results/dev_aux/task2621/fixed_scale.py",
        "results/dev_aux/task2492/learning.py",
        "results/dev_aux/task2492/episode.py",
        "results/dev_aux/task2606/train.py",
        "results/dev_aux/task2609/run_eval.py",
        "results/dev_aux/task2609/eval-plan.json",
        "results/dev_aux/task2621/cost_scan.py",
        "results/dev_aux/task2621/audit_cost_scan.py",
        "results/dev_aux/task2621/cost-feasibility.json",
        "results/dev_aux/task2392/reader.py",
        "generic_chess/session/session.py",
        "generic_chess/session/serialization.py",
        "generic_chess/rules/compiler.py",
        "generic_chess/rules/schema.py",
    ] + [f"results/dev_aux/task2433/rules-{rule}.json" for rule in RULES]
    pins = {path: sha((ROOT / path).read_bytes()) for path in source_paths}
    if pins["results/dev_aux/task2433/rules-15.json"] != pool["candidate"]["sha256"]:
        raise ValueError("candidate rule changed since root-pool preparation")

    cost_bound = json.loads((ROOT / "results/dev_aux/task2627/successor-cost-bound.json").read_text(encoding="utf-8"))
    prep_seconds = float(pool["preparation_seconds"])
    audit_allowance = 180
    reserve = 1200
    estimate = float(cost_bound["cost_bound_seconds"]["conservative_total"])
    if estimate > min(cost_bound["cost_bound_seconds"]["all_in_hard_cap"],
                      cost_bound["cost_bound_seconds"]["chat_assessment_threshold"]):
        raise ValueError("source-bound all-in estimate exceeds the existing cap or requires Chat assessment")
    plan = {
        "task": "DEV_AUX2628_RULE15_SAME_FIXED_SCALE_TDLEAF_VS_INITIAL",
        "state": "FROZEN_BEFORE_TRAINING_OR_EVALUATION",
        "question": "On the fixed-scale task2621 learner and this outcome-blind feature-conditioned rules15 panel, does TDLeaf search bootstrapping improve actual terminal W/L/D against the exact random initialization?",
        "scope": "One generated 4x4 semantic-action ruleset; exact full-record exclusion from the enumerated history inventory only; no descendant, transposition, distributional, population or full-Generic independence claim.",
        "pool": {"path": "results/dev_aux/task2627/rule15-successor-root-pools.json", "sha256": sha(pool_raw),
                "audit_path": "results/dev_aux/task2627/rule15-successor-pool-audit.json", "audit_sha256": sha(audit_raw),
                "training_roots_per_rule": 120, "evaluation_roots_per_rule": 16,
                "training_families_shared_across_seeds": True,
                "selection": "Outcome-blind fixed family scan; exact full-history exclusion; eight-ply nonterminal records; require same-owner R in hand and on board plus a promoted P-base/R-current piece so the hand-R unlock action and promotion feature are active; preserve all roots and seeds."},
        "domain": {"rules": list(RULES), "history_authority": "Full GameSession record/replay; promotion, drops, auxiliary state and declaration semantics retained.",
                   "evaluator": "Exact task2492 Model and TDLeafEpisode; dynamic board-CURRENT/hand-BASE channels from task2621; coordinate0=1, scale10; no human material priors."},
        "seeds": list(SEEDS),
        "initialization": {"recipe": "random.Random(seed); [1.0] + uniform(0.5,1.5) per dynamic channel",
                           "seed_specific_vector_with_fixed_base_coordinate": True,
                           "weights_by_rule_seed": initial_weights},
        "training": {"method": "TDLeaf", "foe": "uniform all-ones fixed Model at scale10", "nodes_per_arm_candidate_plus_foe": 250_000,
                     "arms": len(RULES) * len(SEEDS), "roots_per_rule": 120,
                     "total_paid_node_target": len(RULES) * len(SEEDS) * 250_000, "max_episodes_per_arm": 512,
                     "H": 128, "hard_seconds": 1800,
                     "root_order": "Registered 120 roots in order, cycle; learner color alternates by episode index.",
                     "observation": "Only complete candidate-color AlphaBeta D2 search receipts update TDLeaf; only actual scoring rule terminals provide W/L/D; UNKNOWN receives no terminal reward."},
        "search": {"algorithm": "task2492.learning.AlphaBeta", "depth": 2, "quiescence": 0,
                   "nodes_per_query": 2048, "seconds_per_query": 2.0,
                   "ordering_seed_base": 2622_000_000,
                   "cost_accounting": "Charge candidate and foe nodes; preserve incomplete queries and cap-ended episodes."},
        "evaluation": {"endpoints": ["initial", "TDLeaf"], "foe": "uniform all-ones fixed Model at scale10",
                        "slots": len(RULES) * len(SEEDS) * 16 * 2 * 2, "construction": "1 rule x 4 seeds x 16 exact-disjoint roots x 2 learner colors x 2 endpoints",
                       "node_cap_by_rule_family": caps, "paired_cap_assignment": "Per rule exactly eight roots at 20k and eight at 40k combined two-side nodes; fixed seed per rule 977422+rule.",
                        "H": 128, "hard_seconds": 1800, "nodes_per_query": 8192,
                       "outcome": "Actual rule-terminal W/L/D only; RESTART/NO_CONTEST/search cutoff/horizon remain UNKNOWN; never impute draws.",
                        "comparison": "128 paired TDLeaf-minus-initial strata, paired on rule, seed, root family and learner color; retain all missing slots. Exact known differences use observed rewards; each UNKNOWN endpoint independently ranges [-1,+1]. Finite completion bounds, not confidence intervals."},
        "all_in_hard_cap_seconds": 6600,
        "cost_estimate": {"status": "REFRESHED_SOURCE_BOUND_ESTIMATE_BELOW_120_MINUTES",
                          "training_projection_seconds": 1800,
                          "evaluation_projection_seconds": 1800,
                          "root_pool_preparation_observed_seconds": prep_seconds,
                          "preparation_hard_cap_seconds": 180,
                          "independent_audit_allowance_seconds": audit_allowance,
                          "variance_reserve_seconds": reserve,
                          "expected_seconds": estimate,
                          "expected_minutes": estimate / 60.0,
                          "threshold_minutes": 120,
                          "assessment_required_before_launch": estimate >= 7200,
                          "limitation": "Uses the task2627 source-bound conservative all-in projection, including a 1200s variance reserve, plus separate 180s prep and 180s audit allowances. Full 1800s training and evaluation caps remain available; this is a cap bound, not a runtime guarantee.",
                          "cost_bound_source": "results/dev_aux/task2627/successor-cost-bound.json"},
        "source_pins": pins,
        "no_old_caps_changed": True,
        "no_training_or_evaluation_started_at_freeze": True,
        "repair_provenance": {"premise_change": "Separately prepared task2627 successor pool; not a retry/top-up of task2626 exposed roots or task2625 evaluation. Tests one feature-conditioned generated semantic-action rule with unchanged task2621 learner and the independently source-reviewed actual-terminal endpoint/censoring implementation copied into task2628."},
    }
    RUN.mkdir(parents=True, exist_ok=False)
    raw = json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    (RUN / "plan.json").write_bytes(raw)
    registration = {"state": "REGISTERED_BEFORE_TRAINING_OR_EVALUATION",
                    "registered_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "session_id": session["id"], "thread_id": session["thread_id"],
                    "plan_sha256": sha(raw), "root_pools_sha256": sha(pool_raw),
                    "root_pools_audit_sha256": sha(audit_raw), "source_pins": pins,
                    "training_started": False, "evaluation_started": False,
                    "expected_training_arms": len(RULES) * len(SEEDS), "expected_evaluation_slots": len(RULES) * len(SEEDS) * 16 * 2 * 2,
                    "estimated_minutes": estimate / 60.0,
                    "chat_assessment_required": estimate >= 7200}
    reg_raw = json.dumps(registration, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    (RUN / "registration.json").write_bytes(reg_raw)
    print(json.dumps({"status": registration["state"], "plan_sha256": sha(raw),
                      "registration_sha256": sha(reg_raw), "expected_minutes": estimate/60,
                      "chat_assessment_required": estimate >= 7200,
                      "evaluation_slots": len(RULES)*len(SEEDS)*16*2*2}, indent=2))


if __name__ == "__main__":
    main()
