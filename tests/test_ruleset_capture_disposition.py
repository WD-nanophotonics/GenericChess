import hashlib
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.rules.compiler import _compile_geometry_carrier, compile_semantic_ruleset
from generic_chess.rules.schema import compute_fingerprint, ruleset_from_dict, ruleset_to_dict
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.validation import RuleValidationError
from generic_chess.rules.western_chess import build_western_chess_ruleset
from rule_semantics_ir_fixtures import cannon_ruleset
from test_xiangqi_static_setup_fixture import _build_incomplete_static_xiangqi_setup_fixture


@pytest.mark.parametrize(
    "builder,serialized_sha,fingerprint,ir_sha",
    (
        (
            build_western_chess_ruleset,
            "cc57ed9bc3fc8d4381b2b65f733556f641a91ea0f8a285a785741374d9daf978",
            "7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35",
            "9c56a182d005eb01149b3c6d8211cec5db22350c0f8c87d7a510a1943bbcbf00",
        ),
        (
            build_standard_shogi_ruleset,
            "e00bdd7078e353babe0346b9292543e127b5f4230bf1b703a23b56d679663d13",
            "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635",
            "dba7039afb4c33a7f49028de14e23ec3e9fb3b2c04136ff6c15f2ab76bb179a4",
        ),
        (
            cannon_ruleset,
            "4a0bb3433c5d5825d620500ae5653356ea6a4866a2d4692f3fa64d1d0f905627",
            "816540704484bf2f964e47ce24970687961c4f31f535548408ea15f2a4db2c35",
            "9b35a423f13da6e5583436bcb05cac251bda8768b195a745f28bc5fadf50f5cb",
        ),
    ),
)
def test_default_capture_disposition_preserves_square_hashes(
    builder, serialized_sha, fingerprint, ir_sha
):
    rules = builder()
    assert rules.capture_disposition == "capture_to_hand"
    assert "capture_disposition" not in ruleset_to_dict(rules)
    assert hashlib.sha256(serialize_ruleset(rules).encode()).hexdigest() == serialized_sha
    assert compute_fingerprint(rules) == fingerprint
    assert hashlib.sha256(
        compile_semantic_ruleset(rules).ir.serialized().encode()
    ).hexdigest() == ir_sha


def test_nondefault_capture_disposition_roundtrips_and_invalid_values_fail_closed():
    rules = _build_incomplete_static_xiangqi_setup_fixture()
    assert rules.capture_disposition == "remove_from_game"
    serialized = ruleset_to_dict(rules)
    assert serialized["capture_disposition"] == "remove_from_game"
    restored = ruleset_from_dict(serialized)
    assert restored == rules
    assert restored.capture_disposition == "remove_from_game"
    assert serialize_ruleset(restored) == serialize_ruleset(rules)
    assert compute_fingerprint(restored) != compute_fingerprint(
        replace(restored, capture_disposition="capture_to_hand")
    )

    invalid_data = dict(serialized, capture_disposition="discard_somehow")
    with pytest.raises(RuleValidationError, match="CAPTURE_DISPOSITION_INVALID"):
        ruleset_from_dict(invalid_data)

    invalid_rules = replace(rules, capture_disposition="discard_somehow")
    with pytest.raises(RuleValidationError, match="CAPTURE_DISPOSITION_INVALID"):
        _compile_geometry_carrier(invalid_rules)
