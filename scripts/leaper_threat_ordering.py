"""Research-only parent-target threat-coverage ordering. No product default.

For each opponent actor separately intersect its unconditional Leap destinations
from its current square with SAME actor's reverse destinations attacking our
parent anchor. Union these intersections; IGNORE landing occupancy and opponent
king safety by definition. This is a geometric hint, never a legality proof.
For each ordinary empty-target board move, score the change in our unconditional
union coverage of this FIXED parent target set. Anchor moves keep parent targets.
All TT/capture/promotion/counter/killer positions are protected. Remaining quiet
slots are sorted by descending delta before history, stable baseline on ties.
"""
from collections import Counter
from generic_chess.ai.alphabeta.ordering import MoveOrderer
from scripts.leaper_ordinary_geometry import ordinary_leap_geometry
from generic_chess.core.actions import action_is_board,action_source_square,action_target_square,action_promotion_target_id
from generic_chess.core.coordinates import square_to_index
from generic_chess.core.movement import LeapAtom

class ThreatOrderer(MoveOrderer):
    def __init__(self,compiled=None,stats=None):
        super().__init__(compiled,stats);self.compiled=compiled;self.tables=None;self.attempted=False
        self.default_checkpoint=None;self.iteration_source=lambda:0;self.yield_counts={};self.call_sequence=0
        self.metrics={'calls':0,'reorders':0,'scored_actions':0,'nonzero_actions':0,'fallbacks':0};self.capture=[];self.capture_limit=64;self.dropped=0
    def _tables(self,checkpoint=None):
        if self.attempted:return self.tables
        c=self.compiled
        if c is None:return None
        if checkpoint:checkpoint()
        if c.board_shape.area>64 or any(not isinstance(a,LeapAtom) for t in c.piece_types for a in t.movement_atoms):self.attempted=True;return None
        # Exact executable capture IR geometry, not merely metadata eligibility.
        targets=ordinary_leap_geometry(c,checkpoint)
        if targets is None:self.attempted=True;return None
        def mask(xs):
            m=0
            for i in xs:m|=1<<i
            return m
        forward={k:mask(v) for k,v in targets.items()};reverse={}
        for (owner,tid,src),destinations in targets.items():
            if checkpoint:checkpoint()
            for dst in destinations:reverse[(owner,tid,dst)]=reverse.get((owner,tid,dst),0)|(1<<src)
        # Publish complete structures only; interruption leaves previous state.
        self.tables=(forward,reverse);self.attempted=True;return self.tables
    def feature(self,state,actions,checkpoint=None,*,override_targets=None):
        tables=self._tables(checkpoint)
        if tables is None:return None
        f,r=tables;pos=state.position;n=pos.board_shape.width;side=pos.side_to_move;anchors=[];own=[];threat=0
        for i,p in enumerate(pos.board):
            if checkpoint:checkpoint()
            if p is not None and p.owner==side:
                own.append((i,p));
                if self.compiled.types_by_id[p.current_type_id].is_anchor:anchors.append(i)
        if len(anchors)!=1:return None
        anchor=anchors[0]
        for i,p in enumerate(pos.board):
            if p is not None and p.owner!=side:threat|=f.get((p.owner,p.current_type_id,i),0)&r.get((p.owner,p.current_type_id,anchor),0)
        if override_targets is not None:threat=override_targets
        base=0
        for i,p in own:base|=f.get((side,p.current_type_id,i),0)
        values={}
        for a in actions:
            if checkpoint:checkpoint()
            src=square_to_index(action_source_square(a),pos.board_shape);dst=square_to_index(action_target_square(a),pos.board_shape);mover=pos.board[src];other=0
            for i,p in own:
                if i!=src:other|=f.get((side,p.current_type_id,i),0)
            after=other|f.get((side,mover.current_type_id,dst),0);values[a]=(after&threat).bit_count()-(base&threat).bit_count()
        return {'target_mask':threat,'baseline_coverage':base,'scores':values,'parent_anchor':anchor}
    def order(self,state,actions,evaluator,depth,tt_move,prev_action,tuning,*,checkpoint=None):
        checkpoint=checkpoint or self.default_checkpoint
        baseline=super().order(state,actions,evaluator,depth,tt_move,prev_action,tuning,checkpoint=checkpoint)
        if depth<=0:return baseline
        # Separate policy only; never combine with earlier experimental orderers.
        if tuning.use_quiet_geometric_coverage or tuning.use_relative_history:raise ValueError('isolated one-policy research required')
        side=state.position.side_to_move;n=state.position.board_shape;killers=self._killers.get(depth,[]);counter=self.countermove_for(prev_action) if tuning.use_countermove else None
        slots=[i for i,a in enumerate(baseline) if a!=tt_move and a!=counter and a not in killers and action_is_board(a) and action_promotion_target_id(a) is None and state.position.board[square_to_index(action_target_square(a),n)] is None]
        if len(slots)<2:return baseline
        quiet=[baseline[i] for i in slots];features=self.feature(state,quiet,checkpoint)
        if features is None:self.metrics['fallbacks']+=1;return baseline
        replacement=sorted(quiet,key=lambda a:-features['scores'][a]);ordered=list(baseline)
        for i,a in zip(slots,replacement):ordered[i]=a
        assert Counter(ordered)==Counter(actions)
        self.metrics['calls']+=1;self.metrics['reorders']+=ordered!=baseline;self.metrics['scored_actions']+=len(quiet);self.metrics['nonzero_actions']+=sum(v!=0 for v in features['scores'].values())
        if len(self.capture)<self.capture_limit:self.capture.append({'depth':depth,'before':[str(a) for a in baseline],'after':[str(a) for a in ordered],'scores':{str(a):v for a,v in features['scores'].items()},'target_mask':features['target_mask'],'protected_slots':[i for i in range(len(baseline)) if i not in slots]})
        else:self.dropped+=1
        self.call_sequence+=1
        if ordered!=baseline:
            changed=next(i for i,(a,b) in enumerate(zip(baseline,ordered)) if a!=b)
            iteration=self.iteration_source();counts=self.yield_counts
            return _ObservedActions(ordered,lambda:counts.__setitem__(iteration,counts.get(iteration,0)+1),changed)
        return ordered

class _ObservedActions(list):
    """Record first changed iterator yield, NOT guaranteed recursive child entry."""
    def __init__(self,values,on_changed,changed):super().__init__(values);self.on_changed=on_changed;self.changed=changed;self.recorded=False
    def __iter__(self):
        for i,a in enumerate(super().__iter__()):
            if i==self.changed and not self.recorded:self.recorded=True;self.on_changed()
            yield a
