"""Public session: atomic submissions, immutable views and replayable records."""
from __future__ import annotations
import json
from .engine import ModeEngine
from .model import CatalogEntry, ModeSnapshot, ModeState, ModeResult, ModeAction, PieceView, Resign, action_from_dict, action_to_dict
from .rules import ModeRules, format_score


class ModeSession:
    def __init__(self, rules: ModeRules):
        self._engine = ModeEngine(rules)
        self._states = [self._engine.initial_state]
        self._actions = []
        self._cursor = 0

    @property
    def rules(self) -> ModeRules:
        return self._engine.rules

    @property
    def state(self) -> ModeState:
        return self._states[self._cursor]

    @property
    def result(self) -> ModeResult:
        return self.state.result

    def price(self, type_id: str) -> str:
        return self._engine.price(type_id)

    def legal_actions(self) -> tuple[ModeAction, ...]:
        return self._engine.legal_actions(self.state)

    def _commit(self, action, state):
        # A failed transition never changes cursor/history or drops the redo tail.
        self._states = self._states[:self._cursor + 1] + [state]
        self._actions = self._actions[:self._cursor] + [action]
        self._cursor += 1
        return state

    def submit(self, action: ModeAction | Resign) -> ModeState:
        if isinstance(action, Resign):
            return self.resign()
        return self._commit(action, self._engine.apply_action(self.state, action))

    def resign(self) -> ModeState:
        return self._commit(Resign(), self._engine.resign(self.state))

    def undo(self) -> bool:
        if self._cursor == 0:
            return False
        self._cursor -= 1
        return True

    def redo(self) -> bool:
        if self._cursor >= len(self._actions):
            return False
        self._cursor += 1
        return True

    def to_record(self) -> dict:
        return dict(schema_version=1, rules=self.rules.to_dict(),
                    actions=[action_to_dict(a) for a in self._actions[:self._cursor]])

    @classmethod
    def from_record(cls, record: dict | str) -> ModeSession:
        if isinstance(record, str):
            record = json.loads(record)
        if not isinstance(record, dict) or type(record.get('schema_version')) is not int or record.get('schema_version') != 1:
            raise ValueError('unsupported material record version')
        if not isinstance(record.get('actions'), list):
            raise ValueError('record actions must be a list')
        session = cls(ModeRules.from_dict(record['rules']))
        for raw in record['actions']:
            session.submit(action_from_dict(raw))
        return session

    def snapshot(self) -> ModeSnapshot:
        state = self.state
        board = []
        for p in state.position.board:
            if p is None:
                board.append(None)
                continue
            alive = state.active[p.owner]
            status = 'active' if alive else 'frozen_anchor' if self._engine.types_by_id[p.current_type_id].is_anchor else 'neutral'
            board.append(PieceView(p.current_type_id, p.owner if alive else None, None if alive else p.owner, status))
        catalog = tuple(CatalogEntry(p.type_id, p.name, p.is_anchor,
                                     None if p.is_anchor else self.price(p.type_id)) for p in self.rules.piece_types)
        return ModeSnapshot(self.rules.width, self.rules.height, self.rules.players, state.current_player,
                            state.ply_count, self.rules.purchase_penalty, self.rules.ray_multiplier,
                            tuple(board), tuple(format_score(v, self.rules.score_scale) for v in state.balances),
                            tuple(h.counts for h in state.position.hands), state.active,
                            tuple(self._engine.in_check(state, p) for p in range(self.rules.players)),
                            catalog, state.result, state.eliminations)
