import hashlib
import json
from pathlib import Path

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.first_action_service_pilot import audit_first_action_service
from scripts.freeze_first_action_service_pilot import _project


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "docs/research/data/first_action_service_chess_shogi_preref.json"


def test_prereference_manifest_reproduces_exact_chess_and_shogi_results():
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert frozen["classification"] == "FIRST_ACTION_SERVICE_CHESS_SHOGI_PREREFERENCE"
    assert frozen["human_reference_imported"] is False
    assert frozen["xiangqi_material_reference_imported"] is False
    for relative, expected in frozen["input_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    for name, builder in (("western_chess", build_western_chess_ruleset),
                          ("standard_shogi", build_standard_shogi_ruleset)):
        actual = _project(audit_first_action_service(compile_semantic_ruleset(builder()),
                                                     max_seconds=60))
        assert json.loads(json.dumps(actual)) == frozen["rulesets"][name]
