from pathlib import Path
import hashlib, json
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict
from generic_chess.rules.compiler import compile_ruleset
from results.dev_aux.task2565 import train as T

D = Path("results/dev_aux/task2595")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canon(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"))

def main():
    design = json.loads((D / "design.json").read_text())
    registration = json.loads((D / "registration.json").read_text())
    rules = json.loads((D / "rules-364005.json").read_text())
    roots = json.loads((D / "root-manifest.json").read_text())
    assert sha(D / "design.json") == registration["design_sha256"]
    assert sha(D / "rules-364005.json") == registration["rule_sha256"]
    assert sha(D / "root-manifest.json") == registration["root_manifest_sha256"]

    try:
        reconstructed = ruleset_from_dict(rules)
        roundtrip = ruleset_to_dict(reconstructed) == rules
        cc = compile_ruleset(reconstructed)
        compile_ok = True
    except Exception as exc:
        roundtrip = False
        compile_ok = False
        cc = None
        compile_error = repr(exc)

    required = {"schema_version", "piece_types", "initial_position",
                "drop_allowed", "promotion_allowed", "promotion_forced",
                "repetition_limit", "max_ply", "stalemate_result",
                "board_size", "metadata"}
    pieces = rules["piece_types"]
    nonanchors = [x for x in pieces if not x.get("is_anchor")]
    anchors = [x for x in pieces if x.get("is_anchor")]
    type_ids = {x["type_id"] for x in pieces}
    promotion = any(x.get("is_promotable") and x.get("promotion_target_ids")
                    and set(x["promotion_target_ids"]) <= type_ids
                    for x in nonanchors)
    drops = rules["drop_allowed"]
    drop_ok = set(drops) == {"A", "P", "X"} and all(
        len(owners) == 2 and all(squares and any(squares) for squares in owners)
        for owners in drops.values())

    start = T.environment(364005, cc) if cc is not None else None
    initial_ok = start is not None and start.terminal() is None and bool(start.actions())
    train_rows, eval_rows = roots["train"], roots["evaluation"]
    train = [canon(x["record"]) for x in train_rows]
    evaluation = [canon(x["record"]) for x in eval_rows]
    common = set(train) & set(evaluation)
    nonterminal = sum(x["terminal"] is None and x["legal_actions"] > 0
                      for x in eval_rows)
    gates = {
        "schema_fields_exact": set(rules) == required,
        "schema_roundtrip": roundtrip,
        "full_compile": compile_ok,
        "nonanchor_types_A_P_X": sorted(x["type_id"] for x in nonanchors) == ["A", "P", "X"],
        "sole_anchor_K": [x["type_id"] for x in anchors] == ["K"],
        "promotion_target": promotion,
        "drop_reachable_A_P_X_each_player": drop_ok,
        "initial_nonterminal_legal": initial_ok,
        "evaluation_histories_unique": len(set(evaluation)) == len(evaluation),
        "no_train_eval_history_overlap": not common,
        "at_least_24_nonterminal_eval_roots": nonterminal >= 24,
    }
    extras = [x for x in registration["failures"]
              if x.get("check") == "train_root_uniqueness"]
    result = {
        "status": "SEED_ADMISSION_FAILED" if not all(gates.values()) else "RULE_ADMITTED",
        "fitness_started": False,
        "registered_result_status": registration["status"],
        "registered_design_sha256_verified": True,
        "registered_rule_sha256_verified": True,
        "registered_root_manifest_sha256_verified": True,
        "registered_gate_results": gates,
        "failed_registered_gates": [k for k, v in gates.items() if not v],
        "extra_script_failure_not_in_design": {
            "check": "train_root_uniqueness",
            "reported_by_registration_script": bool(extras),
            "treatment": "diagnostic only; the human-readable preregistration requires evaluation roots unique and disjoint from TRAIN, but does not require TRAIN roots unique among themselves."
        },
        "counts": {
            "train_roots": len(train_rows),
            "train_unique_histories": len(set(train)),
            "evaluation_roots": len(eval_rows),
            "evaluation_unique_histories": len(set(evaluation)),
            "train_eval_overlap_histories": len(common),
            "evaluation_nonterminal_legal": nonterminal,
            "evaluation_terminal": sum(x["terminal"] is not None for x in eval_rows),
            "train_terminal": sum(x["terminal"] is not None for x in train_rows),
            "train_history_plies": {
                str(n): sum(len(x["record"]["actions"]) == n for x in train_rows)
                for n in sorted({len(x["record"]["actions"]) for x in train_rows})
            },
            "evaluation_history_plies": {
                str(n): sum(len(x["record"]["actions"]) == n for x in eval_rows)
                for n in sorted({len(x["record"]["actions"]) for x in eval_rows})
            }
        },
        "rule_seed": 364005,
        "conclusion": "Seed 364005 is not eligible for learner fitness because registered evaluation-root uniqueness, TRAIN/EVAL disjointness, and nonterminal-count gates fail. Preserve this seed and rule; do not substitute another seed or rerun fitness on these roots.",
    }
    if not compile_ok:
        result["compile_error"] = compile_error
    target = D / "admission-review.json"
    assert not target.exists()
    target.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
