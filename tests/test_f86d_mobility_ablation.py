"""F86D monotone-mobility ablation artifact contracts."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86d_mobility_ablation"

LEGACY_FINGERPRINTS = {
    "V4-2": "1b8547501a45ebc1344f7134319ed215de09a51dfb001270dc127e77528698ac",
    "V4-3": "7e2ff9e15c2a0d1be5faa8c6697f22e488976a2d2ae9f077b85c6e71f95ff400",
    "V4-4": "864e9aaf0f36b0a94024454a357e6787b3edd9cfd81898d1bea76dfc591b08d0",
    "V4-5": "9a5f3de7a492fa4fa01ca1b4c2e7a11b24403cde87b79761b26e212d13221f24",
    "V5-2": "ddacec0f6b6fbffeb9135fbbbb658093d92ce0e5bce28665a87022b702d815d6",
    "V5-3": "d6e47a6fe19ab20538a1ec9539597b5765d0211cb608b15c262613a86e635297",
    "V5-4": "580475d4c25b8d5bb9d796902d383ac673bd00c3565e4609d07443bcc338ad04",
    "V5-5": "c3fa844c61ea944f9fd11560f00878337389f427a59d84958c312e38d5494d31",
}

PROFILES = {
    "A_FULL_ANCHOR",
    "B_BIDIRECTIONAL_ORDINARY",
    "C_FULL_ANCHOR_PLUS_BIDIRECTIONAL",
}


def _load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_f86d_static_diagnostics_cover_frozen_population_and_owners():
    payload = _load("static_diagnostics.json")
    rows = payload["rows"]
    assert len(rows) == 32
    assert {row["profile"] for row in rows} == {"LEGACY", *PROFILES}

    legacy = {row["sample_id"]: row for row in rows if row["profile"] == "LEGACY"}
    assert {sample_id: row["ruleset_fingerprint"] for sample_id, row in legacy.items()} == LEGACY_FINGERPRINTS
    assert all(row["diagnostics"]["monotone_mobility_dag"] for row in legacy.values())
    assert all(not row["diagnostics"]["has_backward_atom"] for row in legacy.values())
    assert all(row["diagnostics"]["ordinary_mean_reversibility"] == 0.0 for row in legacy.values())
    assert all(row["diagnostics"]["ordinary_nontrivial_scc_fraction"] == 0.0 for row in legacy.values())
    for row in rows:
        type_metrics = row["diagnostics"]["type_metrics"]
        assert type_metrics
        assert all({owner["owner"] for owner in metric["owner_metrics"]} == {0, 1} for metric in type_metrics)


def test_f86d_counterfactual_rulesets_are_exactly_scoped():
    payload = _load("counterfactual_rulesets.json")
    rows = payload["rows"]
    assert len(rows) == 24
    assert {row["profile"] for row in rows} == PROFILES
    assert len({(row["sample_id"], row["profile"]) for row in rows}) == 24
    assert all(row["ruleset"]["metadata"]["f86d_profile"] == row["profile"] for row in rows)
    assert all(len(row["ruleset_fingerprint"]) == 64 for row in rows)


def test_f86d_results_account_for_bounded_counterfactual_work():
    payload = _load("results.json")
    assert payload["played_game_count"] == 12
    assert len(payload["quality_games"]) == 12
    assert {row["profile"] for row in payload["quality_games"]} == PROFILES
    assert all(sum(row["profile"] == profile for row in payload["quality_games"]) == 4 for profile in PROFILES)
    assert payload["tactical_probe_position_count"] == 6
    assert payload["tactical_probe_nodes"] <= 6 * 256
    assert payload["default_generator_changed"] is False
    assert payload["f85_actual_compute"] == 0
    assert payload["stalemate_improvements_vs_legacy"] == {
        "A_FULL_ANCHOR": 1.0,
        "B_BIDIRECTIONAL_ORDINARY": 0.75,
        "C_FULL_ANCHOR_PLUS_BIDIRECTIONAL": 0.75,
    }
    assert payload["routing"] == "ANCHOR_MOBILITY_PRIMARY_CAUSE"
