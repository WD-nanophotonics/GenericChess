"""Mode-owned economy/turns; legacy kernels own movement and attack geometry."""
from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
import json
from types import MappingProxyType

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.attacks import anchor_square, is_square_attacked
from generic_chess.core.coordinates import Square, index_to_square, square_to_index
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.movement import LeapAtom, RayAtom, atom_targets
from generic_chess.core.movegen import _piece_actions, _drop_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from .model import BuyPiece, BuyAndDrop, Elimination, ModePosition, ModeResult, ModeState
from .rules import ModeRules, format_score, price_units


class ModeEngine:
    """Small geometry context compatible with the existing pseudo-move kernels.

    The old 2-player transition/terminal engine is deliberately not called:
    capture currency, buy turns and four-player elimination belong to this mode.
    """
    def __init__(self, rules: ModeRules):
        self.rules = rules
        self.board_size = rules.shape  # Legacy indexing helpers accept BoardShape.
        self.types_by_id = MappingProxyType({p.type_id: p for p in rules.piece_types})
        self.ruleset_fingerprint = sha256(json.dumps(rules.to_dict(), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.prices = MappingProxyType({p.type_id: price_units(p, rules) for p in rules.piece_types})
        self.purchasable = tuple(p.type_id for p in rules.piece_types if not p.is_anchor)
        leap_tables, ray_tables = {}, {}
        for p in rules.piece_types:
            leaps, rays = [], []
            for seat in range(rules.players):
                turns = 2 * seat if rules.players == 2 else (-seat) % 4
                atoms = []
                for a in p.movement_atoms:
                    x, y = a.offset if isinstance(a, LeapAtom) else a.direction
                    for _ in range(turns):
                        x, y = -y, x
                    atoms.append(LeapAtom((x, y)) if isinstance(a, LeapAtom) else RayAtom((x, y), a.max_steps))
                ll, rr = [], []
                for i in range(rules.shape.area):
                    source = index_to_square(i, rules.shape)
                    ll.append(tuple(atom_targets(rules.shape, 0, source, a) if isinstance(a, LeapAtom) else () for a in atoms))
                    rr.append(tuple(atom_targets(rules.shape, 0, source, a) if isinstance(a, RayAtom) else () for a in atoms))
                leaps.append(tuple(ll)); rays.append(tuple(rr))
            leap_tables[p.type_id] = tuple(leaps); ray_tables[p.type_id] = tuple(rays)
        self.leap_targets = MappingProxyType(leap_tables)
        self.ray_paths = MappingProxyType(ray_tables)
        self.drop_allowed = MappingProxyType({tid: tuple((True,) * rules.shape.area for _ in range(rules.players)) for tid in self.purchasable})
        board = [None] * rules.shape.area
        for seat in range(rules.players):
            for placement in rules.formation:
                x, y = placement.square.file, placement.square.rank
                if rules.players == 2 and seat == 1:
                    x, y = rules.width - 1 - x, rules.height - 1 - y
                elif rules.players == 4:
                    for _ in range(seat):  # clockwise: south, west, north, east
                        x, y = y, rules.width - 1 - x
                i = square_to_index(Square(x, y), rules.shape)
                if board[i] is not None:
                    raise ValueError('rotated starting formations overlap')
                board[i] = Piece(seat, placement.type_id, placement.type_id)
        pos = ModePosition(tuple(board), tuple(Hands.empty() for _ in range(rules.players)), rules.starting_player, self.ruleset_fingerprint)
        initial = ModeState(pos, (0,) * rules.players, (True,) * rules.players)
        if any(self.in_check(initial, p) for p in range(rules.players)):
            raise ValueError('initial formation places an anchor in check')
        if rules.players == 4 and any(not self.legal_actions(replace(initial, position=replace(pos, side_to_move=p))) for p in range(4)):
            raise ValueError('four-player formation must give every player a legal opening action')
        self.material_ceiling = sum(self.prices[p.current_type_id] for p in board if p is not None)
        self.initial_state = self.settle(initial)

    def price(self, type_id: str) -> str:
        if type_id not in self.purchasable:
            raise ValueError('anchor or unknown type is not purchasable')
        return format_score(self.prices[type_id], self.rules.score_scale)

    def in_check(self, state: ModeState, player: int) -> bool:
        if not state.active[player]:
            return False
        sq = anchor_square(state.position, player, self)
        if sq is None:
            raise ValueError('active player has no anchor')
        return any(state.active[other] and other != player
                   and is_square_attacked(state.position, sq, other, self)
                   for other in range(self.rules.players))

    def materialize(self, state, action):
        """Apply one already-generated action without turn/terminal adjudication."""
        side = state.current_player
        board = list(state.position.board)
        hands = list(state.position.hands)
        balances = list(state.balances)
        if isinstance(action, BoardMove):
            source = square_to_index(action.from_square, self.board_size)
            target = square_to_index(action.to_square, self.board_size)
            captured = board[target]
            if captured is not None:
                balances[side] += self.prices[captured.current_type_id]
            board[target], board[source] = board[source], None
        elif isinstance(action, DropMove):
            hands[side] = hands[side].remove(action.base_type_id)
            board[square_to_index(action.to_square, self.board_size)] = Piece(side, action.base_type_id, action.base_type_id)
        elif isinstance(action, BuyPiece):
            balances[side] -= self.prices[action.type_id]
            hands[side] = hands[side].add(action.type_id)
        elif isinstance(action, BuyAndDrop):
            balances[side] -= self.prices[action.type_id]
            board[square_to_index(action.to_square, self.board_size)] = Piece(side, action.type_id, action.type_id)
        else:
            raise IllegalActionError('unsupported material action')
        return replace(state, position=replace(state.position, board=tuple(board), hands=tuple(hands)), balances=tuple(balances))

    def legal_actions(self, state):
        if state.result.terminal:
            return ()
        side = state.current_player
        if not state.active[side]:
            return ()
        actions = []
        # These are the existing Core movement and unrestricted drop kernels.
        for action in _piece_actions(state.position, self) + _drop_actions(state.position, self):
            if not self.in_check(self.materialize(state, action), side):
                actions.append(action)
        checked = self.in_check(state, side)
        empty = tuple(index_to_square(i, self.board_size) for i, p in enumerate(state.position.board) if p is None)
        for tid in self.purchasable:
            if self.prices[tid] > state.balances[side]:
                continue
            if not checked:
                actions.append(BuyPiece(tid))
            if not self.rules.purchase_penalty:
                for target in empty:
                    action = BuyAndDrop(tid, target)
                    if not self.in_check(self.materialize(state, action), side):
                        actions.append(action)
        # Repeated atoms must not create duplicate legal choices.
        return tuple(dict.fromkeys(actions))

    def advance(self, state):
        side = state.current_player
        for step in range(1, self.rules.players + 1):
            candidate = (side + step) % self.rules.players
            if state.active[candidate]:
                return replace(state, position=replace(state.position, side_to_move=candidate))
        raise ValueError('no surviving player')

    def eliminate(self, state, player, reason):
        active = list(state.active); active[player] = False
        balances = list(state.balances); balances[player] = 0
        hands = list(state.position.hands); hands[player] = Hands.empty()
        return replace(state, active=tuple(active), balances=tuple(balances),
                       position=replace(state.position, hands=tuple(hands)),
                       eliminations=state.eliminations + (Elimination(player, reason, state.ply_count),))

    def identity(self, state):
        # Wallets, hands and active seats are legality-relevant, even on an
        # unchanged board after a purchase. Elimination history is monotone.
        value = (tuple(None if p is None else (p.owner, p.current_type_id) for p in state.position.board),
                 tuple(h.counts for h in state.position.hands), state.balances, state.active, state.current_player)
        return json.dumps(value, separators=(',', ':'))

    def settle(self, state):
        """Only the player whose turn begins can be mated/stalemated."""
        while True:
            survivors = tuple(i for i, alive in enumerate(state.active) if alive)
            if len(survivors) == 1:
                return replace(state, result=ModeResult('win', survivors[0], 'last_player'))
            if self.legal_actions(state):
                break
            checked = self.in_check(state, state.current_player)
            reason = 'checkmate' if checked else 'stalemate'
            if self.rules.players == 2:
                result = ModeResult('win', 1 - state.current_player, reason) if checked else ModeResult('draw', reason=reason, drawn_players=survivors)
                return replace(state, result=result)
            state = self.advance(self.eliminate(state, state.current_player, reason))
        key = self.identity(state)
        counts = dict(state.repetition_counts); counts[key] = counts.get(key, 0) + 1
        state = replace(state, repetition_counts=tuple(sorted(counts.items())))
        reason = 'repetition' if counts[key] >= self.rules.repetition_limit else 'ply_limit' if state.ply_count >= self.rules.max_ply else None
        if reason:
            return replace(state, result=ModeResult('draw', reason=reason, drawn_players=survivors))
        return state

    def after_legal(self, state, action):
        changed = replace(self.materialize(state, action), ply_count=state.ply_count + 1)
        return self.settle(self.advance(changed))

    def apply_action(self, state, action):
        if not isinstance(action, (BoardMove, DropMove, BuyPiece, BuyAndDrop)):
            raise IllegalActionError('unsupported material action')
        coordinates = ([action.from_square, action.to_square] if isinstance(action, BoardMove)
                       else [action.to_square] if isinstance(action, (DropMove, BuyAndDrop)) else [])
        if any(not isinstance(q, Square) or type(q.file) is not int or type(q.rank) is not int for q in coordinates):
            raise IllegalActionError('coordinates must be integer squares')
        tid = action.base_type_id if isinstance(action, DropMove) else action.type_id if isinstance(action, (BuyPiece, BuyAndDrop)) else None
        if tid is not None and (not isinstance(tid, str) or not tid):
            raise IllegalActionError('piece type must be a nonempty string')
        if action not in self.legal_actions(state):
            raise IllegalActionError('action is not legal in the current material state')
        return self.after_legal(state, action)

    def resign(self, state):
        if state.result.terminal:
            raise IllegalActionError('game is already finished')
        side = state.current_player
        changed = replace(state, ply_count=state.ply_count + 1)
        if self.rules.players == 2:
            return replace(changed, result=ModeResult('win', 1 - side, 'resignation'))
        changed = self.eliminate(changed, side, 'resignation')
        return self.settle(self.advance(changed))

    def material_value(self, state, player):
        value = state.balances[player]
        value += sum(self.prices[tid] * count for tid, count in state.position.hands[player].counts)
        value += sum(self.prices[p.current_type_id] for p in state.position.board if p is not None and p.owner == player and state.active[player])
        return value
