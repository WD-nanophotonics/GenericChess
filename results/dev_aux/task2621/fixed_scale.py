"""Opt-in fixed-scale Generic adapter; unchanged Model and TDLeafEpisode.

Material features approximate value, while GameSession remains the complete
rule/history authority. The caller declares a board-type unit before outcomes;
the existing generator's P convention is the default, without assuming any
human movement or material value. Non-generator rules may declare another unit.
"""
from __future__ import annotations

import json

from generic_chess.session.serialization import deserialize_game_record, serialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2397.material import channels as material_channels
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2511.generic import ScoringSessionEnv


def compile_channels(compiled, *, unit_type="P"):
    """All non-anchor CURRENT board types and BASE hand types, no fixed width."""
    types = {piece.type_id: piece for piece in compiled.piece_types}
    eligible = sorted(type_id for type_id, piece in types.items() if not piece.is_anchor)
    if unit_type not in eligible:
        raise ValueError("declare an existing non-anchor unit type before this scoped transfer")
    unit = ("board", unit_type)
    return (unit,) + tuple((kind, type_id) for kind in ("board", "hand")
                           for type_id in eligible if (kind, type_id) != unit)


class FixedScaleSessionEnv(ScoringSessionEnv):
    def __init__(self, session, *, unit_type="P"):
        self.unit_type = unit_type
        super().__init__(session, compile_channels(session.compiled, unit_type=unit_type))

    def features(self):
        position = self.session.state.position
        known = self.session.compiled.types_by_id
        observed = {piece.current_type_id for piece in position.board if piece is not None}
        observed.update(base for hand in position.hands for base, count in hand.counts if count)
        if not observed <= set(known):
            raise ValueError("material observation contains a type absent from executable rules")
        quantities = material_channels(position, 0)
        return tuple(quantities[kind].get(type_id, 0) for kind, type_id in self.names)

    def record(self):
        return json.loads(serialize_game_record(self.session.to_record()))

    def replay(self):
        other = GameSession.replay(self.session.compiled,
            deserialize_game_record(json.dumps(self.record())))
        if (other.state != self.session.state or other.result != self.session.result
                or other.to_record() != self.session.to_record()):
            raise ValueError("full Generic state/result/history did not survive replay")
        return type(self)(other, unit_type=self.unit_type)


def unchanged_model(weights):
    """Return the exact Chess model class, fixed coordinate0 and scale10."""
    return Model(weights, fixed=0, scale=10.)


def unchanged_learner():
    return TDLeafEpisode(eta=.05, lam=.95)
