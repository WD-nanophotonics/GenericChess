from pathlib import Path
import datetime, hashlib, json, random, sys

from generic_chess.generation.config import GeneratorConfig, GenerationError
from generic_chess.generation.generator import generate_game
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict
from generic_chess.rules.compiler import compile_ruleset
from results.dev_aux.task2565 import train as T
from results.dev_aux.task2392.reader import SharedDeleteStopReader

ROOT = Path("results/dev_aux/task2595")
RULE_SEED = 364005
TRAIN_START, TRAIN_COUNT = 500000, 8192
EVAL_START, EVAL_COUNT = 510000, 32
CODE = [
    "results/dev_aux/task2595/register.py",
    "results/dev_aux/task2595/design.json",
    "results/dev_aux/task2593/episode.py",
    "results/dev_aux/task2565/train.py",
    "results/dev_aux/task2492/learning.py",
    "results/dev_aux/task2492/episode.py",
    "results/dev_aux/task2532/free_model.py",
    "results/dev_aux/task2504/search.py",
    "results/dev_aux/task2392/reader.py",
    "generic_chess/generation/config.py",
    "generic_chess/generation/generator.py",
    "generic_chess/rules/schema.py",
    "generic_chess/rules/compiler.py",
    "generic_chess/session/session.py",
    "generic_chess/session/serialization.py",
    "results/dev_aux/task2525/run.py",
]

def digest(data):
    return hashlib.sha256(data).hexdigest()

def put_new(path, data):
    assert not path.exists(), f"refusing overwrite: {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

def family_root(cc, family, stop):
    stop()
    env = T.environment(RULE_SEED, cc)
    T.prefix(env, RULE_SEED, family, 4)
    record = env.record()
    return dict(family=family, record=record, terminal=env.terminal(),
                legal_actions=len(env.actions()))

def main():
    assert not (ROOT / "registration.json").exists(), "already registered"
    design_bytes = (ROOT / "design.json").read_bytes()
    design = json.loads(design_bytes)
    assert design["status"] == "FROZEN_BEFORE_RULE_GENERATION"
    assert design["rule"]["generator_seed"] == RULE_SEED
    session = json.loads(Path(".local_agent/session.json").read_text())
    assert session["state"] == "active"
    stop = SharedDeleteStopReader(Path.cwd())
    stop()

    config = GeneratorConfig(seed=RULE_SEED, **design["rule"]["config"])
    generated = None
    failure = None
    try:
        generated = generate_game(config)
    except GenerationError as exc:
        failure = dict(kind="GenerationError", message=str(exc))
    if generated is None:
        registration = dict(
            status="SEED_GENERATION_FAILED", seed=RULE_SEED,
            session_id=session["id"], registered_at=datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
            design_sha256=digest(design_bytes), config=design["rule"]["config"],
            failure=failure, no_substitute_seed=True)
        put_new(ROOT / "registration.json",
                json.dumps(registration, indent=2).encode())
        print(json.dumps(registration, indent=2))
        return 0

    rules = ruleset_to_dict(generated.ruleset)
    rule_bytes = json.dumps(rules, sort_keys=True, separators=(",", ":")).encode()
    put_new(ROOT / f"rules-{RULE_SEED}.json", rule_bytes)
    required = {"schema_version", "piece_types", "initial_position",
                "drop_allowed", "promotion_allowed", "promotion_forced",
                "repetition_limit", "max_ply", "stalemate_result",
                "board_size", "metadata"}
    failures = []
    if set(rules) != required:
        failures.append(dict(check="full_schema_fields", got=sorted(rules)))
    try:
        reconstructed = ruleset_from_dict(rules)
        if ruleset_to_dict(reconstructed) != rules:
            failures.append(dict(check="schema_roundtrip"))
        cc = compile_ruleset(reconstructed)
    except Exception as exc:
        cc = None
        failures.append(dict(check="full_compile", error=repr(exc)))
    pieces = rules.get("piece_types", [])
    anchors = [p for p in pieces if p.get("is_anchor")]
    nonanchors = [p for p in pieces if not p.get("is_anchor")]
    if sorted(p.get("type_id") for p in nonanchors) != ["A", "P", "X"]:
        failures.append(dict(check="nonanchor_ids",
                             got=sorted(p.get("type_id") for p in nonanchors)))
    if [p.get("type_id") for p in anchors] != ["K"]:
        failures.append(dict(check="anchor_id",
                             got=[p.get("type_id") for p in anchors]))
    ids = {p.get("type_id") for p in pieces}
    if not any(p.get("is_promotable") and p.get("promotion_target_ids")
               and set(p["promotion_target_ids"]) <= ids for p in nonanchors):
        failures.append(dict(check="promotion_target"))
    drops = rules.get("drop_allowed", {})
    if set(drops) != {"A", "P", "X"}:
        failures.append(dict(check="drop_type_ids", got=sorted(drops)))
    else:
        for type_id, owners in drops.items():
            if (len(owners) != 2 or any(not squares or not any(squares)
                                        for squares in owners)):
                failures.append(dict(check="drop_reachable_each_player",
                                     type_id=type_id))
    if not isinstance(rules.get("repetition_limit"), int) or rules["repetition_limit"] < 2:
        failures.append(dict(check="repetition_limit"))
    if not isinstance(rules.get("max_ply"), int) or rules["max_ply"] < 1:
        failures.append(dict(check="max_ply"))
    if rules.get("stalemate_result") not in {"draw", "loss"}:
        failures.append(dict(check="stalemate_result"))

    roots = dict(train=[], evaluation=[])
    if cc is not None:
        start_env = T.environment(RULE_SEED, cc)
        if start_env.terminal() is not None or not start_env.actions():
            failures.append(dict(check="initial_nonterminal_legal"))
        for family in range(TRAIN_START, TRAIN_START + TRAIN_COUNT):
            roots["train"].append(family_root(cc, family, stop))
        for family in range(EVAL_START, EVAL_START + EVAL_COUNT):
            roots["evaluation"].append(family_root(cc, family, stop))

        train_records = [json.dumps(x["record"], sort_keys=True)
                         for x in roots["train"]]
        eval_records = [json.dumps(x["record"], sort_keys=True)
                        for x in roots["evaluation"]]
        overlap = set(train_records) & set(eval_records)
        if len(set(train_records)) != len(train_records):
            failures.append(dict(check="train_root_uniqueness",
                                 unique=len(set(train_records)),
                                 total=len(train_records)))
        if len(set(eval_records)) != len(eval_records):
            failures.append(dict(check="eval_root_uniqueness",
                                 unique=len(set(eval_records)),
                                 total=len(eval_records)))
        if overlap:
            failures.append(dict(check="train_eval_overlap", count=len(overlap)))
        usable = sum(r["terminal"] is None and r["legal_actions"] > 0
                     for r in roots["evaluation"])
        if usable < 24:
            failures.append(dict(check="nonterminal_eval_roots",
                                 usable=usable, required=24))
    status = "RULE_ADMITTED" if not failures else "SEED_ADMISSION_FAILED"
    root_bytes = json.dumps(roots, sort_keys=True, separators=(",", ":")).encode()
    if cc is not None:
        put_new(ROOT / "root-manifest.json", root_bytes)
    pins = {name: digest(Path(name).read_bytes()) for name in CODE}
    registration = dict(
        status=status, seed=RULE_SEED,
        session_id=session["id"],
        registered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        design_sha256=digest(design_bytes), rule_sha256=digest(rule_bytes),
        root_manifest_sha256=digest(root_bytes) if cc is not None else None,
        config=design["rule"]["config"], source_pins=pins,
        train_family_start=TRAIN_START, train_family_count=TRAIN_COUNT,
        eval_family_start=EVAL_START, eval_family_count=EVAL_COUNT,
        train_unique_roots=(len(set(json.dumps(x["record"], sort_keys=True)
                                    for x in roots["train"]))
                            if cc is not None else None),
        eval_unique_roots=(len(set(json.dumps(x["record"], sort_keys=True)
                                   for x in roots["evaluation"]))
                           if cc is not None else None),
        eval_nonterminal_roots=(sum(r["terminal"] is None and
                                    r["legal_actions"] > 0
                                    for r in roots["evaluation"])
                                if cc is not None else None),
        failures=failures, no_substitute_seed=True,
        fitness_started=False)
    put_new(ROOT / "registration.json",
            json.dumps(registration, indent=2).encode())
    print(json.dumps(registration, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
