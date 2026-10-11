from generic_chess.core.coordinates import square_to_index
from generic_chess.native import semantic as ns

class SnapshotEvaluator:
    """Private mechanical field translation of frozen Evaluator; no C changes."""
    def __init__(self, ev, native):
        self.native=native
        self.cfg=ev._config
        ids=native.type_ids
        self.board_values=tuple(ev._profile.board_value_by_type[t] for t in ids)
        self.hand_values=tuple(ev._profile.hand_value_by_base_type.get(t,0) for t in ids)
        self.anchors=tuple(ev._compiled.types_by_id[t].is_anchor for t in ids)
        self.promotion=[]
        self.steps={}
        for i,t in enumerate(ids):
            gain=ev._profile.promotion_gain_by_type.get(t,0)
            self.promotion.append(tuple(tuple(self._bonus(ev,t,gain,o,j) for j in range(native.board_size**2)) for o in (0,1)))
            if t in ev._anchor_steps:
                self.steps[i]=tuple(tuple(tuple(square_to_index(s,native.board_size) for s in row) for row in owner) for owner in ev._anchor_steps[t])
    @staticmethod
    def _bonus(ev,t,gain,o,j):
        zone=ev._zones.get((t,o))
        if gain<=0 or zone is None:return 0
        w=ev._config.promotion_potential_weight;u=max(1,gain//1000)
        if j in zone:return w*u
        return w*u//2 if any(s in zone for s in ev._compiled.empty_forward_mobility[t][o][j]) else 0
    def evaluate_capsule(self,capsule):
        s=ns.snapshot(self.native,capsule)
        board=s['board'];score=0;anchors=[None,None]
        for j,p in enumerate(board):
            if p is None:continue
            base,current,owner,promoted=map(int,p)
            value=self.board_values[current]
            score+=value if owner==0 else -value
            if self.cfg.promotion_potential_weight and not promoted:
                bonus=self.promotion[base][owner][j]
                score+=bonus if owner==0 else -bonus
            if self.anchors[current] and anchors[owner] is None:anchors[owner]=j
        for owner in (0,1):
            for t,count in enumerate(s['hands'][owner]):
                if count:
                    value=int(count)*self.hand_values[t]
                    score+=value if owner==0 else -value
        if self.cfg.dynamic_mobility_weight or self.cfg.anchor_escape_weight:
            attacks=tuple(ns.attacked_squares(self.native,capsule,o) for o in (0,1))
            score+=self.cfg.dynamic_mobility_weight*(len(attacks[0])-len(attacks[1]))
            w=self.cfg.anchor_escape_weight
            if w:
                esc=[]
                for owner in (0,1):
                    j=anchors[owner]
                    esc.append(0 if j is None else sum(board[t] is None and t not in attacks[1-owner] for t in self.steps[int(board[j][1])][owner][j]))
                score+=w*(esc[0]-esc[1])
                if anchors[0] in attacks[1]:score-=w*10
                if anchors[1] in attacks[0]:score+=w*10
        return score if s['side']==0 else -score
