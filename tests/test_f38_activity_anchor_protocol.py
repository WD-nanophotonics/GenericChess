import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_h38a_manifest_and_holdout_are_frozen_without_production_change():
    manifest = load("f38_activity_anchor_manifest.json")
    descriptor = load("f38_external_holdout_descriptor.json")
    canonical = json.dumps({k: v for k, v in manifest.items() if k != "manifest_sha256"}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical.encode()).hexdigest() == manifest["manifest_sha256"]
    assert manifest["selected_f37_candidate"] == "R37C"
    assert manifest["no_tuning_from_results"] is True
    assert manifest["external_holdout_not_training_data"] is True
    assert manifest["production_diff_zero"] is True
    assert manifest["holdout_unique_positions"] >= 16
    assert manifest["holdout_descriptor"]["sha256"] == hashlib.sha256((FIXTURES / "f38_external_holdout_descriptor.json").read_bytes()).hexdigest()
    assert manifest["bound_authority_files"]["h38a_protocol_script"]["sha256"] == hashlib.sha256((ROOT / "scripts/audit_f38_activity_anchor_protocol.py").read_bytes()).hexdigest()
    assert descriptor["kind"] == "F38_EXTERNAL_HOLDOUT_DESCRIPTOR"
    assert descriptor["selection_protocol"]["score_or_rank_inspection"] is False
    assert descriptor["selection_protocol"]["alphasho_execution"] is False
    assert len(descriptor["positions"]) == descriptor["holdout_unique_positions"]
    assert len({row["canonical_state_sha256"] for row in descriptor["positions"]}) == descriptor["holdout_unique_positions"]


def test_h38a_selection_rows_are_protocol_bound():
    descriptor = load("f38_external_holdout_descriptor.json")
    for row in descriptor["positions"]:
        assert row["additional_ply"] in range(8, 65)
        assert row["alphasho_played_move"]
        assert row["legality_witness"]["selected_move_in_legal_actions"] is True
        assert row["legality_witness"]["legal"] is True
        assert row["transcript_provenance"]["fixture"] == "tests/fixtures/f30r1_paired_match.json"


def test_h38a_production_scope():
    assert subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0
