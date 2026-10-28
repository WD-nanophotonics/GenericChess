"""AUX reader of the newly published transient-import returns.

Independent of the producer/its verifier: current Core literal replay only.
Never imports producer capsules, Player, Native DLL or search execution.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import compute_fingerprint, ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value
from scripts.verify_published_boolean_returns import diagnostic_action, EXCLUDED_TIMING_FIELDS

SOURCE = "76da1ff8d92f8c8756a5cb264e411dca522c37d6"
TIMING_FIELDS = EXCLUDED_TIMING_FIELDS - {"evaluation_profile_cache_hit"}


def work_signature(decision):
    # Unlike a duration, cache admission is a non-timing work/state flag.
    return {key: value for key, value in decision.items() if key not in TIMING_FIELDS}


def load(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith(".gz") else raw)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_returns(folder, inputs, output):
    manifest = load(folder / "manifest.json")
    checks = []
    for entry in manifest["files"]:
        raw = (folder / entry["path"]).read_bytes()
        assert digest(raw) == entry["compressed_sha256"], entry["path"]
        assert digest(gzip.decompress(raw)) == entry["public_decompressed_sha256"], entry["path"]
        checks.append(entry["path"])
    frozen = load(folder / "cost/frozen.json.gz")
    assert digest(inputs.read_bytes()) == frozen["input_sha256"] == frozen["plan"]["input_sha256"]
    assert frozen["binary"]["sha256"] == frozen["plan"]["binary_sha256"]
    supplement = load(folder / "source-byte-supplement.json.gz")["files"]
    source_hashes = []
    for name, text in frozen["sources"].items():
        exact = supplement[name]["original_utf8"]
        assert digest(exact.encode()) == frozen["source_hashes"][name] == supplement[name]["sha256"]
        assert exact.replace("\r\n", "\n") == text
        source_hashes.append(dict(path=name, sha256=frozen["source_hashes"][name],
                                  has_crlf="\r\n" in exact))
    slots = load(folder / "cost/slots.json.gz")
    assert len(slots) == len(frozen["slots"]) == 96
    for index, (old, final) in enumerate(zip(frozen["slots"], slots)):
        for key in ("slot", "case_id", "depth", "on"):
            assert old[key] == final[key], (index, key)
        assert old["slot"] == index
    roots, bound_roots = {}, []
    rows = [row for row in load(inputs)["rows"] if row["prefix_length"] == 2]
    assert [row["id"] for row in rows] == frozen["case_ids"] and len(rows) == 12
    for row in rows:
        rule = ruleset_from_dict(row["RuleSet"])
        assert compute_fingerprint(rule) == row["fingerprint"]
        compiled = compile_legacy_ruleset_for_semantic_execution(rule)
        record = deserialize_game_record(json.dumps(row["record"]))
        session = GameSession.replay(compiled, record)
        assert record_value(session.state) == row["root"]
        assert session.state.ply_count == 2 and session.result.status.value == "ongoing"
        expected = {diagnostic_action(a, row["fingerprint"]) for a in row["legal_actions"]}
        assert expected == set(session.legal_actions())
        roots[row["id"]] = compiled, record
        bound_roots.append(dict(case=row["id"], history=len(session.state.history),
                                fingerprint=row["fingerprint"], legal_actions=len(expected)))
    returned, endings, pv_plies = [], Counter(), 0
    observed = sorted(p.name for p in (folder / "cost").glob("return-*.json.gz"))
    assert observed == [f"return-{i:03d}.json.gz" for i in range(48)]
    for index in range(48):
        raw = load(folder / f"cost/return-{index:03d}.json.gz")
        slot = slots[index]
        assert raw["status"] == slot["status"] == "RETURNED"
        for key in ("slot", "case_id", "depth", "on"):
            assert raw[key] == slot[key]
        assert raw["slot"] == index and raw["depth"] == 6
        assert raw["transient_imports_active"] is raw["on"]
        d = raw["decision"]
        assert d == slot["decision"]
        assert slot["complete"] == (d["completed_depth"] == 6)
        assert d["runtime_depth_balanced"] and d["runtime_pushes"] == d["runtime_pops"]
        assert d["native_legality_fallbacks"] == d["native_legality_operational_failures"] == 0
        assert raw["Native_delta"]["availability"].get("declines", 0) == 0
        for key in ("outer_seconds", "cpu_seconds", "constructor_seconds"):
            assert type(raw[key]) in (int, float) and math.isfinite(raw[key]) and raw[key] >= 0
        assert raw["outer_seconds"] >= raw["constructor_seconds"]
        for key in ("outer_seconds", "cpu_seconds"):
            assert slot[key] == raw[key]
        compiled, record = roots[raw["case_id"]]
        session = GameSession.replay(compiled, record)
        chosen = diagnostic_action(d["action"], record.ruleset_fingerprint)
        assert chosen in session.legal_actions()
        pv = [diagnostic_action(a, record.ruleset_fingerprint) for a in d["principal_variation"]]
        assert pv and pv[0] == chosen
        for action in pv:
            assert session.result.status.value == "ongoing"
            session.submit(action)
            pv_plies += 1
        endings[session.result.status.value] += 1
        returned.append(dict(slot=index, case=raw["case_id"], on=raw["on"],
                             completed_depth=d["completed_depth"], reason=d["termination_reason"],
                             result_source=d["result_source"], pv_plies=len(pv),
                             pv_end=session.result.status.value, wall=raw["outer_seconds"],
                             cpu=raw["cpu_seconds"], saved_signature=work_signature(d)))
    for slot in slots[48:]:
        assert slot["status"] == "NOT_RUN" and slot["depth"] == 8
    groups = []
    for index in range(0, 48, 4):
        group = returned[index:index + 4]
        eligible = all(row["completed_depth"] == 6 for row in group)
        parity = len({json.dumps(row["saved_signature"], sort_keys=True) for row in group}) == 1
        if eligible:
            assert parity
        groups.append(dict(case=group[0]["case"], eligible=eligible, saved_parity=parity,
            on_wall=sum(row["wall"] for row in group if row["on"]),
            off_wall=sum(row["wall"] for row in group if not row["on"]),
            on_cpu=sum(row["cpu"] for row in group if row["on"]),
            off_cpu=sum(row["cpu"] for row in group if not row["on"])))
    eligible = [group for group in groups if group["eligible"]]
    wall_ratio = sum(g["on_wall"] for g in eligible) / sum(g["off_wall"] for g in eligible)
    cpu_ratio = sum(g["on_cpu"] for g in eligible) / sum(g["off_cpu"] for g in eligible)
    median = statistics.median(g["on_wall"] / g["off_wall"] for g in eligible)
    summary = load(folder / "cost/summary.json.gz")
    assert len(eligible) == summary["6"]["eligible_root_groups"] == 11
    assert wall_ratio == summary["6"]["wall_ratio"] and cpu_ratio == summary["6"]["cpu_ratio"]
    assert pv_plies == 287
    gate = len(eligible) >= 10 and wall_ratio <= .95 and median <= .95
    assert not gate
    result = dict(source_commit=SOURCE, status="PASS", archive_files=len(checks),
        publication_compressed_and_decompressed_hashes_checked=checks,
        frozen_slot_identities=96, source_hashes=source_hashes, roots=bound_roots,
        returns=returned, groups=groups, PV_plies=pv_plies, PV_endings=dict(endings),
        eligible_groups=len(eligible), wall_ratio=wall_ratio, cpu_ratio=cpu_ratio,
        root_median_wall_ratio=median, frozen_D8_gate=gate, D8_NOT_RUN=48,
        signature_excludes=sorted(TIMING_FIELDS), cache_hit_flag_retained=True,
        script_sha256=digest(Path(__file__).read_bytes()),
        limits=["No new Player/search/game/solver/build or timing replay.",
                "The saved work and provider flags are claims, not all-iteration execution traces.",
                "Current Core root/PV replay is independent; historical DLL/build execution is not observed.",
                "Both arms use the same private new binary and adapter, not an old-production comparison.",
                "No isolated SHA-only gain, fused-kernel saving, strength or heldout rule-class result."])
    output.mkdir(parents=True, exist_ok=False)
    (output / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in
                     {"returns", "groups", "roots", "source_hashes", "publication_compressed_and_decompressed_hashes_checked"}}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    read_returns(args.folder, args.inputs, args.output)
