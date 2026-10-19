"""Freeze task2606's bounded Generic-rule transfer before any training."""
from pathlib import Path
import datetime, hashlib, json, platform, random, re, sys
import chess
from results.dev_aux.task2606.train import compiled, environment, prefix

ROOT = Path.cwd()
OUT = ROOT / "results/dev_aux/task2606"
assert not any((OUT / name).exists() for name in ("plan.json", "eval-plan.json", "root-manifest.json", "registration.json", "started.json", "eval-started.json")), "refusing to overwrite a registered or started task"
RULES = [271001, 271002, 271003, 271004]
SEEDS = [1977, 8173, 27182, 31415]
METHODS = ["TD95", "LocalLambda"]
TRAIN_FAMILY_OFFSET = 990000
TRAIN_MAX_GAMES = 1024
TRAIN_FAMILY_IDS = set(range(TRAIN_FAMILY_OFFSET, TRAIN_FAMILY_OFFSET + TRAIN_MAX_GAMES // 2))
EVAL_FAMILIES = list(range(991000, 991008))

# Reject a reused family ID in any earlier frozen plan/root manifest.
needle = re.compile(r"\b(?:" + "|".join(map(str, sorted(TRAIN_FAMILY_IDS | set(EVAL_FAMILIES)))) + r")\b")
for p in (ROOT / "results/dev_aux").glob("task*/**/*plan*.json"):
    if p.parent == OUT:
        continue
    if needle.search(p.read_text(encoding="utf-8", errors="ignore")):
        raise SystemExit(f"family-ID collision in prior plan: {p}")

rule_paths = {str(Path(f"results/dev_aux/task2525/rules-{seed}.json")).replace("\\", "/"): hashlib.sha256(Path(f"results/dev_aux/task2525/rules-{seed}.json").read_bytes()).hexdigest() for seed in RULES}
root_rows = {}
for gs in RULES:
    cc = compiled(gs)
    for family in EVAL_FAMILIES:
        env = environment(gs, cc)
        prefix(env, gs, family, 4)
        record = env.record()
        assert len(record["actions"]) <= 4
        root_rows[f"{gs}:{family}"] = record
root_manifest = {
    "state": "FROZEN_BEFORE_TRAINING",
    "scope": "32 exact full-history roots from four existing generated Generic rule definitions; roots are evaluation-only, not a novel-rule holdout",
    "rules": RULES,
    "rule_sha256": rule_paths,
    "prefix_plies": 4,
    "families": EVAL_FAMILIES,
    "roots": root_rows,
}
root_bytes = json.dumps(root_manifest, sort_keys=True, separators=(",", ":")).encode()
(OUT / "root-manifest.json").write_bytes(root_bytes)
root_sha = hashlib.sha256(root_bytes).hexdigest()

source_paths = [
    "results/dev_aux/task2606/prepare.py",
    "results/dev_aux/task2606/train.py",
    "results/dev_aux/task2606/evaluate.py",
    "results/dev_aux/task2593/episode.py",
    "results/dev_aux/task2492/learning.py",
    "results/dev_aux/task2492/episode.py",
    "results/dev_aux/task2492/adapters.py",
    "results/dev_aux/task2532/free_model.py",
    "results/dev_aux/task2504/search.py",
    "results/dev_aux/task2392/reader.py",
    "results/dev_aux/task2525/run.py",
    *rule_paths.keys(),
]
pins = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in source_paths}
base_commit = __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], text=True).strip()

arms = [[gs, seed, method] for gs in RULES for seed in SEEDS for method in METHODS]
plan = {
    "state": "REGISTERED_BEFORE_TRAIN_AND_EVALUATION",
    "task": "DEV_AUX2606",
    "session_id": json.loads(Path(".local_agent/session.json").read_text())["id"],
    "question": "Does the local-terminal-target TD(lambda) update transfer better than frozen TD(lambda=.95) from the same initialization on a finite family of complete Generic-rule games?",
    "changed_premise": "Standard-Chess task2594 passed its finite panel. This is a scoped Generic transfer with a fixed uniform opponent; task2606's inherited runner was audited and repaired so both arms now learn only on their assigned color.",
    "candidate": "OutcomeGatedTDLeafEpisode(eta=.05, base_lambda=.95): lambda_i=1 only when the next complete fixed-depth root target has pv_terminal=true; otherwise .95. Known final W/L/D uses the existing episode end update. UNKNOWN censors the final outcome residual; incomplete root searches are not observed.",
    "baseline": "TDLeafEpisode(eta=.05, lambda=.95), same observation/update timing, initial vector, assigned color, root-family recipe, depth and paid-node cap.",
    "domain": "Generic complete GameSession semantics through RecordedSessionEnv; four existing rule definitions only, no novel-rule or all-domain claim.",
    "rules": RULES,
    "seeds": SEEDS,
    "methods": METHODS,
    "arms_order": arms,
    "dimension": 6,
    "initialization": "For each seed, [1.0] + five Uniform(.5,1.5) weights from Python random.Random(seed); same exact vector reused across rule definitions and both methods. This fixes one scale coordinate and is not a human price prior.",
    "foe": [1.0] * 6,
    "nodes_per_arm": 312500,
    "target_training_nodes": 10000000,
    "cap_seconds": 5400,
    "max_games": TRAIN_MAX_GAMES,
    "depth": 2,
    "nodes_per_query": 8192,
    "seconds_per_query": 2,
    "H": 128,
    "prefix_plies": 4,
    "training_family_offset": TRAIN_FAMILY_OFFSET,
    "training_family_recipe": "family=990000+index//2; learner color alternates by index; same family/prefix recipe per (rule, seed, method) index.",
    "snapshot_nodes": [78125, 156250, 234375],
    "eta": 0.05,
    "lambda": 0.95,
    "ordering_seed_offset": 972606000,
    "root_manifest_sha256": root_sha,
    "pins": pins,
    "pins": pins,
    "source_base_commit": base_commit,
    "runtime": {"python": platform.python_version(), "python_chess": chess.__version__, "platform": platform.platform()},
    "scope": "32 training arms (4 rules x 4 seeds x 2 methods), each 312500 candidate-paid nodes; equal candidate search nodes only. Fixed six-weight uniform foe. No search prover, qsearch, SEE/material ordering, result-based arm/seed/root selection, or cap extension. Root search returns completed full-window depth-2 minimax values; incomplete searches are excluded; unknown game outcomes remain censored.",
}
eval_slots = [[gs, seed, fam, color, endpoint, "uniform"] for gs in RULES for seed in SEEDS for fam in EVAL_FAMILIES for color in (0, 1) for endpoint in ("initial", "TD95", "LocalLambda")]
eval_plan = {
    "state": "REGISTERED_BEFORE_TRAIN_AND_EVALUATION",
    "task": "DEV_AUX2606",
    "domain": "generic",
    "rules": RULES,
    "seeds": SEEDS,
    "endpoints": ["initial", "TD95", "LocalLambda"],
    "foes": {"uniform": [1.0] * 6},
    "slots": eval_slots,
    "root_manifest_sha256": root_sha,
    "pins": pins,
    "prefix_plies": 4,
    "depth": 2,
    "H": 128,
    "nodes_per_query": 8192,
    "seconds_per_query": 2,
    "ordering_seed_offset": 972606000,
    "cap_seconds": 720,
    "scope": "768 paid slots = 4 rules x 4 parameter seeds x 8 shared full-history roots x 2 candidate colors x 3 endpoints. Same root/seed/color opponent conditions for all endpoints. Finite panel only; UNKNOWN or missing slots are never scored as draws.",
}

def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

dump("plan.json", plan)
dump("eval-plan.json", eval_plan)
registration = {
    "state": "REGISTERED_BEFORE_RUN",
    "registered_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "task": "DEV_AUX2606",
    "source_base_commit": base_commit,
    "train_plan_sha256": hashlib.sha256((OUT / "plan.json").read_bytes()).hexdigest(),
    "eval_plan_sha256": hashlib.sha256((OUT / "eval-plan.json").read_bytes()).hexdigest(),
    "root_manifest_sha256": hashlib.sha256((OUT / "root-manifest.json").read_bytes()).hexdigest(),
    "source_pins": pins,
    "arms": len(arms),
    "training_node_target": 10_000_000,
    "training_wall_cap_seconds": 5400,
    "evaluation_slots": len(eval_slots),
    "evaluation_wall_cap_seconds": 720,
    "expected_duration_minutes": 58,
    "hard_cap_total_seconds": 6120,
    "cost_basis": "Prior Generic run: 7.2M nodes / 2219.8s and 512 deployment slots / 672146 nodes / 199.1s. Linear node-cost projection for 10M training nodes plus 768 slots is about 57.5 minutes; combined hard wall caps are 102 minutes before small setup/audit overhead, so estimated total remains <120 minutes. Preserve partial/censored results if either cap is reached.",
}
dump("registration.json", registration)
print(json.dumps({"registered": True, "arms": len(arms), "train_nodes": plan["target_training_nodes"], "eval_slots": len(eval_slots), "root_sha256": root_sha, "plan_sha256": registration["train_plan_sha256"], "expected_minutes": registration["expected_duration_minutes"], "hard_cap_minutes": registration["hard_cap_total_seconds"] / 60}))