"""Learning Phase 1.8: AlphaSho positive control tests."""

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.learning.alphasho_bridge import (
    alphasho_available,
    assert_alphasho_unchanged,
    audit_alphasho,
    capture_repo_state,
    human_material_reference,
)
from generic_chess.learning.phase18 import (
    decompose_scale,
    verdict_parity,
    verdict_td_scale,
)
from generic_chess.learning.shogi_rules import (
    build_shogi_ruleset,
    cshogi_available,
    gc_action_to_usi,
    gc_legal_usi_set,
    gc_to_sfen,
    sfen_to_gc_state,
    usi_to_gc_action,
)
from generic_chess.rules.compiler import compile_ruleset


INITIAL_SFEN = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"

requires_cshogi = pytest.mark.skipif(
    not cshogi_available(), reason="cshogi not available in this interpreter"
)
requires_alphasho = pytest.mark.skipif(
    not alphasho_available(), reason="AlphaSho repository not found"
)


def _compiled():
    return compile_ruleset(build_shogi_ruleset())


def test_shogi_ruleset_fingerprint_stable_and_initial_sfen():
    a = _compiled()
    b = _compiled()
    assert a.ruleset_fingerprint == b.ruleset_fingerprint
    state = sfen_to_gc_state(a, INITIAL_SFEN)
    assert gc_to_sfen(state, a) == INITIAL_SFEN


def test_sfen_promoted_piece_parsing():
    compiled = _compiled()
    state = sfen_to_gc_state(compiled, "8k/7+P1/9/9/9/9/9/9/4K4 b - 1")
    piece = state.position.board[7 * 9 + 1]
    assert piece is not None
    assert piece.promoted is True
    assert piece.base_type_id == "P"
    assert piece.current_type_id == "TP"


def test_usi_roundtrip_initial_legal_moves():
    compiled = _compiled()
    state = sfen_to_gc_state(compiled, INITIAL_SFEN)
    usi_set = gc_legal_usi_set(compiled, state)
    assert len(usi_set) == 30
    for usi in sorted(usi_set):
        action = usi_to_gc_action(compiled, state, usi)
        assert gc_action_to_usi(action) == usi


@requires_cshogi
def test_curated_parity_expected_gaps():
    from generic_chess.learning.shogi_rules import (
        compare_sfen_parity,
        curated_parity_cases,
    )

    compiled = _compiled()
    expected_pass = {
        "initial_position",
        "normal_move_7g7f",
        "promotion_zone_pawn",
        "dead_rank_pawn_drop",
        "promoted_piece_present",
        "white_hand_drop",
    }
    for case in curated_parity_cases():
        result = compare_sfen_parity(compiled, case["sfen"])
        if case["id"] in expected_pass:
            assert result["equal"], f"{case['id']} should pass: {result}"
        elif case["id"] == "nifu":
            assert not result["equal"]
            assert "P*5h" in result["extra_in_gc"]
            assert not result["missing_in_gc"]
        elif case["id"] == "uchifuzume":
            assert not result["equal"]
            assert result["extra_in_gc"] == ["P*1b"]
            assert not result["missing_in_gc"]


def test_material_geometry_scale_invariance():
    from generic_chess.learning.phase18 import _stats

    base = {"a": 1.0, "b": 2.0, "c": 4.0}
    scaled = {k: 2.5 * v for k, v in base.items()}
    keys = sorted(base)
    stats = _stats([base[k] for k in keys], [scaled[k] for k in keys])
    assert stats["pearson"] == pytest.approx(1.0)
    assert stats["spearman"] == pytest.approx(1.0)


def test_decompose_scale_pure_scale_and_orthogonal():
    w0 = {"a": 1.0, "b": 2.0, "c": 4.0}
    pure = {k: 1.3 * v for k, v in w0.items()}
    out = decompose_scale(w0, pure)
    assert out["scale_energy_fraction"] == pytest.approx(1.0, abs=1e-6)
    assert out["orthogonal_l2"] == pytest.approx(0.0, abs=1e-6)

    # w1 = w0 + vector orthogonal to w0.
    orth = {"a": -2.0, "b": 1.0, "c": 0.0}  # dot(w0, orth) = -2 + 2 + 0 = 0
    w1 = {k: w0[k] + orth[k] for k in w0}
    out2 = decompose_scale(w0, w1)
    assert out2["scale_energy_fraction"] == pytest.approx(0.0, abs=1e-6)
    assert out2["scale_parallel_l2"] == pytest.approx(0.0, abs=1e-6)

    zero = decompose_scale({"x": 0.0}, {"x": 5.0})
    assert zero["zero_base"] is True
    assert zero["scale_energy_fraction"] == 0.0


@requires_alphasho
def test_human_material_reference_mapping():
    compiled = _compiled()
    ref = human_material_reference(compiled)
    board = ref["board_value_by_type"]
    hand = ref["hand_value_by_base_type"]
    assert "K" not in board  # anchor excluded
    assert board["P"] == 100
    assert board["R"] == 1000
    assert board["TP"] == 520  # promoted pawn = gold value
    assert board["TB"] == 950  # horse
    assert board["TR"] == 1150  # dragon
    assert hand["P"] == 100
    assert hand["G"] == 520
    assert "TP" not in hand  # promoted types never held in hand


@requires_alphasho
def test_alphasho_audit_readonly(monkeypatch):
    # The external checkout is intentionally owned by another Windows
    # identity.  Keep this read-only positive control safe without global Git
    # configuration; production search/rules code remains untouched.
    import generic_chess.learning.alphasho_bridge as bridge

    def safe_git_capture(*args: str) -> str:
        result = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={bridge.ALPHASHO_ROOT}",
                "-C",
                str(bridge.ALPHASHO_ROOT),
                *args,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    monkeypatch.setattr(bridge, "_git_capture", safe_git_capture)
    compiled = _compiled()
    before = capture_repo_state()
    audit = audit_alphasho(compiled)
    assert audit["available"] is True
    assert audit["legacy"]["piece_values"][1] == 100
    assert audit["legacy"]["source_commit"] == "3262cc8"
    unchanged = assert_alphasho_unchanged(before)
    assert unchanged["unchanged"] is True


def test_verdict_parity_and_scale_thresholds():
    curated_ok = {"pass_count": 8, "total": 8}
    curated_bad = {"pass_count": 6, "total": 8}
    assert verdict_parity(curated_ok, None) == "PASS"
    assert verdict_parity(curated_bad, None) == "FAIL"
    large_bad = {"count": 10, "exact_matches": 9}
    assert verdict_parity(curated_ok, large_bad) == "FAIL"
    assert verdict_td_scale({"mean_scale_energy_fraction": 0.8}) == "DOMINANT"
    assert verdict_td_scale({"mean_scale_energy_fraction": 0.5}) == "SUBSTANTIAL"
    assert verdict_td_scale({"mean_scale_energy_fraction": 0.2}) == "MINOR"
