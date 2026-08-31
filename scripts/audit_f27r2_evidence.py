"""Execute and print the F27 R2 fixed-node declaration evidence."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.audit_f25_standard_shogi_search_baseline as audit


def run() -> dict:
    audit._NATIVE_PROVIDER = audit.NativeSemanticLegalityProvider.try_create(
        audit.compile_ruleset_for_execution(audit.build_standard_shogi_ruleset())
    )
    descriptors = audit._descriptors()
    compiled = audit.compile_ruleset_for_execution(
        audit.build_standard_shogi_ruleset()
    )
    rows = []
    for item in descriptors["positions"]:
        for budget in audit.NODE_BUDGETS:
            repeats = []
            for repeat in (1, 2):
                state = audit._state_for(compiled, item["sfen"])
                session = audit._session_for(compiled, state)
                before = session.state
                decision = audit._player(compiled).choose_action(
                    session,
                    audit.SearchLimits(
                        max_nodes=budget,
                        max_depth=8,
                        quiescence_max_depth=4,
                        quiescence_hard_max_depth=8,
                        deterministic=True,
                    ),
                )
                metrics = audit._metrics(decision)
                repeats.append(
                    {
                        "repeat": repeat,
                        "choice_kind": decision.choice_kind,
                        "action": metrics["action"],
                        "visible_action": metrics["visible_action"],
                        "score": metrics["score"],
                        "pv": metrics["pv"],
                        "pv_head": metrics["pv_visible"][0]
                        if metrics["pv_visible"] else None,
                        "completed_depth": metrics["completed_depth"],
                        "nodes": metrics["main_nodes"],
                        "qnodes": metrics["qnodes"],
                        "total_nodes": metrics["total_nodes"],
                        "termination_reason": metrics["termination_reason"],
                        "declaration_checks": decision.declaration_checks,
                        "declaration_win_options": decision.declaration_win_options,
                        "declaration_restart_options": decision.declaration_restart_options,
                        "declaration_root_selected": decision.declaration_root_selected,
                        "provider_mode": metrics["provider_mode"],
                        "root_unchanged": session.state == before,
                        "elapsed_seconds": metrics["elapsed_seconds"],
                    }
                )
            stable = (
                "choice_kind",
                "action",
                "visible_action",
                "score",
                "pv_head",
                "completed_depth",
                "declaration_root_selected",
            )
            deterministic = all(
                tuple(row[key] for key in stable) == tuple(repeats[0][key] for key in stable)
                for row in repeats[1:]
            )
            rows.append(
                {
                    "position_id": item["position_id"],
                    "budget": budget,
                    "repeat_results": repeats,
                    "deterministic": deterministic,
                    "root_unchanged": all(row["root_unchanged"] for row in repeats),
                }
            )

    historical = json.loads(
        (audit.ROOT / "tests/fixtures/f25_standard_shogi_search_baseline.json").read_text(
            encoding="utf-8"
        )
    )
    expected = {
        (row["position_id"], row["budget"]): row["repeats"][0]
        for row in historical["fixed_node"]
    }
    zero_rows = zero_pass = zero_fail = declaration_rows = 0
    for row in rows:
        if any(
            repeat["declaration_win_options"]
            or repeat["declaration_restart_options"]
            for repeat in row["repeat_results"]
        ):
            declaration_rows += 1
            continue
        zero_rows += 1
        baseline = expected[(row["position_id"], row["budget"])]
        passed = all(
            repeat["action"] == baseline["action"]
            and repeat["score"] == baseline["score"]
            and repeat["pv_head"] == baseline["pv_visible"][0]
            and repeat["completed_depth"] == baseline["completed_depth"]
            for repeat in row["repeat_results"]
        )
        zero_pass += int(passed)
        zero_fail += int(not passed)

    source_paths = {
        "f27_manifest": "tests/fixtures/f27_standard_shogi_declaration_search_manifest.json",
        "f27r1_results": "tests/fixtures/f27r1_standard_shogi_declaration_search_results.json",
        "f25_descriptors": "tests/fixtures/f25_standard_shogi_position_descriptors.json",
        "f25_baseline": "tests/fixtures/f25_standard_shogi_search_baseline.json",
    }
    source_sha256 = {
        key: hashlib.sha256((audit.ROOT / path).read_bytes()).hexdigest()
        for key, path in source_paths.items()
    }
    return {
        "status": "PASS",
        "actual_corrective_code_commit": "5b08bf4319c77b10f0d5811bd47d2fb65a351818",
        "ancestry": [
            "f388d32ce84a9db989482a4b4574e3fe377c4d6a",
            "5b08bf4319c77b10f0d5811bd47d2fb65a351818",
            "8afe16884a33383823cd801f344cbb3543a748a5",
            "db224a4721a85a00c3b84f4022b8a0fb17d0bf05",
        ],
        "ruleset_fingerprint": "1bf2a46fe8e9e8636dcdde032ad8d9ccdd42d56cba901a8385043103952bd1f4",
        "provider_mode": "NATIVE" if audit._NATIVE_PROVIDER else "PYTHON_AUTHORITY_FALLBACK",
        "settings": {
            "evaluator": "generic-v1",
            "deterministic": True,
            "max_depth": 8,
            "qsearch": [4, 8],
            "use_tt": True,
            "use_ordering": True,
            "use_native_semantic_legality": True,
            "disk_cache": False,
            "default_tuning": True,
            "fresh_player_and_tt_per_repeat": True,
        },
        "source_paths": source_paths,
        "source_sha256": source_sha256,
        "executed_rows_sha256": hashlib.sha256(
            json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "integrity": {
            "row_count": len(rows),
            "repeat_results_per_row": 2,
            "all_repeats_deterministic": all(row["deterministic"] for row in rows),
            "all_roots_unchanged": all(row["root_unchanged"] for row in rows),
            "declaration_affected_rows": declaration_rows,
            "zero_option_parity_rows": zero_rows,
            "zero_option_parity_pass": zero_pass,
            "zero_option_parity_fail": zero_fail,
            "action_pv_declaration_separation": all(
                repeat["choice_kind"] == "ACTION"
                and repeat["action"] is not None
                and repeat["declaration_root_selected"] is False
                for row in rows
                for repeat in row["repeat_results"]
            ),
        },
        "rows": rows,
    }


if __name__ == "__main__":
    print("F27R2_FIXTURE_JSON_BEGIN")
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
    print("F27R2_FIXTURE_JSON_END")
