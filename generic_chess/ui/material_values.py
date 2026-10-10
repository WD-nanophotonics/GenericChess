"""UI policy: fixed teaching values for exact built-ins, generic values otherwise.

Pawn units: Chess 1/3/3/5/9 (Irish Chess Union teaching sheet);
Shogi Tanigawa teaching table (koichi.jp/shogi/rule/tips/tips-01.php).
Kings are terminal anchors, excluded from ordinary material arithmetic.
"""
from functools import lru_cache
from statistics import median

from ..ai.evaluation.cache import EvaluationProfileCache
from ..ai.evaluation.config import config_hash
from ..ai.evaluation.profile import PieceValueProfile, RuleSetEvaluationProfile
from ..rules.catalog import build_builtin_ruleset, builtin_ruleset_names
from ..rules.compiler import compile_ruleset_for_execution

PAWN_UNIT = 1000
CHESS_VALUES = {"K": 0, "P": 1, "N": 3, "B": 3, "R": 5, "Q": 9}
SHOGI_VALUES = {"K": 0, "P": 1, "L": 3, "N": 4, "S": 5, "G": 6,
                "B": 8, "R": 10, "TP": 7, "TL": 6, "TN": 6,
                "TS": 6, "TB": 10, "TR": 12}


@lru_cache(maxsize=1)
def builtin_fingerprints():
    return {compile_ruleset_for_execution(build_builtin_ruleset(name)).ruleset_fingerprint: name
            for name in builtin_ruleset_names()}


def human_material_profile(compiled, config):
    """Match full execution identity, never a game label or familiar piece IDs."""
    kind = builtin_fingerprints().get(compiled.ruleset_fingerprint)
    if kind is None:
        return None
    units = CHESS_VALUES if kind == "western_chess" else SHOGI_VALUES
    board = {tid: value * PAWN_UNIT for tid, value in units.items()}
    # Held pieces use their unpromoted type's teaching value; no generic discount.
    hand = dict(board)
    gains = {pt.type_id: max(0, max((board[t] for t in pt.promotion_target_ids), default=0)
                            - board[pt.type_id]) for pt in compiled.piece_types}
    profiles = {pt.type_id: PieceValueProfile(
        type_id=pt.type_id, movement_signature="human-teaching-v1",
        raw_capability_score=0.0, normalized_board_value=board[pt.type_id],
        normalized_hand_value=hand[pt.type_id], promotion_option_value=gains[pt.type_id],
        drop_freedom_ratio=0.0, drop_mobility=0.0,
        is_anchor=pt.is_anchor, is_promotable=pt.is_promotable)
        for pt in compiled.piece_types}
    return RuleSetEvaluationProfile(
        ruleset_fingerprint=compiled.ruleset_fingerprint, schema_version=1,
        evaluator_version="ui-human-teaching-v1", config_hash=config_hash(config),
        piece_profiles=profiles,
        median_non_anchor_value=int(median(v for v in board.values() if v)),
        board_value_by_type=board, hand_value_by_base_type=hand,
        promotion_gain_by_type=gains)


class UIMaterialProfileCache(EvaluationProfileCache):
    """Supply traditional prices through the existing player's profile interface."""
    def get_or_build(self, compiled, config):
        profile = human_material_profile(compiled, config)
        if profile is not None:
            return profile, False
        return super().get_or_build(compiled, config)
