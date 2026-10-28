"""Research-only sufficient geometric king-escape witness for admission diagnosis.

Not a move generator/pruner, game certificate or product path. A returned target
is a CURRENT position's empty-square king escape, under a strict compiled plain
Leap footprint; UNKNOWN otherwise. It cannot rule out other piece defenses and
never labels uncertified positions checkmate. Full history clocks are separate.
"""
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
from generic_chess.core.movement import LeapAtom
from scripts.leaper_ordinary_geometry import ordinary_leap_geometry

class EmptyRoyalEscape:
    def __init__(self,compiled):
        self.c=compiled;self.allowed=_plain_leaper_hash_patterns(compiled) is not None and all(isinstance(a,LeapAtom) for t in compiled.piece_types for a in t.movement_atoms)
        self.targets=ordinary_leap_geometry(compiled) if self.allowed else None
    def witness(self,position):
        if self.targets is None or position.ruleset_fingerprint!=self.c.ruleset_fingerprint or position.aux_state or any(h.counts for h in position.hands):return None
        side=position.side_to_move;anchors=[[],[]]
        for i,p in enumerate(position.board):
            if p is not None and self.c.types_by_id[p.current_type_id].is_anchor:anchors[p.owner].append(i)
        if any(len(x)!=1 for x in anchors):return None
        src=anchors[side][0];king=position.board[src]
        candidates=self.targets.get((side,king.current_type_id,src),())
        for dst in sorted(candidates):
            if position.board[dst] is not None:continue
            # For pure Leap, removing our source cannot expose an intermediate
            # ray. No enemy actor is removed by this empty-square king move.
            attacked=False
            for j,p in enumerate(position.board):
                if p is not None and p.owner!=side and dst in self.targets.get((p.owner,p.current_type_id,j),()):attacked=True;break
            if not attacked:return {'source':src,'target':dst,'scope':'empty-square position-only geometric escape;fullCore/history still authority'}
        return None
