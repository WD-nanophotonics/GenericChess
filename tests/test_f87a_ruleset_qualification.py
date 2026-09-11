import json
from pathlib import Path

from generic_chess.benchmark.qualification import common_tape_games
from scripts.f87a_ruleset_qualification import (
    BASELINE_SHA,
    EXPECTED_FINGERPRINTS,
    _compiled,
    _controls,
    build_prep,
    run,
)


ROOT = Path(__file__).resolve().parents[1]
def test_f87a_prep_is_frozen_and_has_six_calibration_controls(tmp_path):
    prep_path = tmp_path / "manifest.json"
    build_prep(ROOT, prep_path)
    prep = json.loads(prep_path.read_text(encoding="utf-8"))
    assert prep["status"] == "PREP_FROZEN"
    assert prep["baseline_sha"] == BASELINE_SHA
    assert len(prep["controls"]) == 6
    assert prep["budgets"]["search_nodes"] == 0
    assert prep["budgets"]["heavy_jobs"] == 0
    assert prep["expectations"]["overall_status"] == "DEFER"


def test_f87a_prep_regeneration_is_byte_identical(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    build_prep(ROOT, first)
    build_prep(ROOT, second)
    assert first.read_bytes() == second.read_bytes()


def test_f87a_control_fingerprints_are_authoritative_and_distinct():
    controls = _controls(ROOT)
    compiled = [_compiled(control) for control in controls]
    fingerprints = {item.ruleset_fingerprint for item in compiled}
    assert len(fingerprints) == 6
    actual = {control["name"]: item.ruleset_fingerprint for control, item in zip(controls, compiled)}
    for name, fingerprint in EXPECTED_FINGERPRINTS.items():
        assert actual[name] == fingerprint


def test_f87a_reports_defer_d_and_e_and_do_not_apply_universal_lattice_gate(tmp_path):
    prep_path = tmp_path / "manifest.json"
    result_dir = tmp_path / "results"
    build_prep(ROOT, prep_path)
    run(ROOT, prep_path, result_dir)
    reports = json.loads((result_dir / "reports.json").read_text(encoding="utf-8"))
    assert set(reports) == {
        "F86C legacy V4-3",
        "F86I full-reverse V4-3",
        "F86N-R1 boundary V4-3",
        "F86N-R1 boundary V5-3",
        "Built-in Western Chess",
        "Built-in Standard Shogi",
    }
    for report in reports.values():
        assert report["overall_status"] == "DEFER"
        assert report["layers"]["D"] == "DEFER"
        assert report["layers"]["E"] == "DEFER"
        assert report["raw_diagnostics"]["layer_b"]["universal_lattice_gate"]["status"] == "DEFER"


def test_f87a_bounded_dynamic_replay_is_deterministic_and_censored():
    control = _controls(ROOT)[0]
    dynamic = common_tape_games(_compiled(control), pair_count=2, max_ply=12, seed=8701, tape_length=32)
    replay = common_tape_games(_compiled(control), pair_count=2, max_ply=12, seed=8701, tape_length=32)
    assert dynamic == replay
    assert dynamic["capture_check_density"]["moves"] == sum(row["plies"] for row in dynamic["records"])
    assert all(
        row["terminal_status"] != "draw" or row["completion"] == "TERMINAL"
        for row in dynamic["records"]
    )
    assert all(
        row["terminal_status"] == "CENSORED"
        for row in dynamic["records"]
        if row["completion"] == "CENSORED"
    )


def test_f87a_builtin_semantic_controls_defer_legacy_common_tape(tmp_path):
    prep_path = tmp_path / "manifest.json"
    result_dir = tmp_path / "results"
    build_prep(ROOT, prep_path)
    run(ROOT, prep_path, result_dir)
    reports = json.loads((result_dir / "reports.json").read_text(encoding="utf-8"))
    for name in ("Built-in Western Chess", "Built-in Standard Shogi"):
        report = reports[name]
        assert report["layers"]["A"] == "PASS"
        assert report["layers"]["B"] == "PASS"
        assert report["layers"]["C"] == "DEFER"
        assert report["raw_diagnostics"]["layer_c"]["status"] == "UNMEASURED"
