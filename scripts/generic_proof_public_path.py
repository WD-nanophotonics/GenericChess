"""Opt-in immutable public-rule path for proof research.

Full GameState/history replay permits no-progress rules unsupported by mutable
runtime. One public apply_action is atomic; time/cancellation checked around it.
No cached halfmove inference, history reset, tablebase or price information.
"""
from dataclasses import replace
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action


class PublicProofPath:
    def __init__(self,state,compiled):
        self.state=self.root=state;self.compiled=compiled;self.stack=[]
        self.pushes=self.pops=self.peak_depth=0

    @classmethod
    def from_state(cls,state,compiled):return cls(state,compiled)

    @property
    def position(self):return self.state.position

    @property
    def terminal_status(self):return self.state.terminal_status

    @terminal_status.setter
    def terminal_status(self,value):self.state=replace(self.state,terminal_status=value)

    @property
    def depth(self):return len(self.stack)

    def legal_actions(self,checkpoint=None):
        return legal_actions(self.state,self.compiled,checkpoint=checkpoint)

    def push(self,action,checkpoint=None):
        if checkpoint:checkpoint()
        child=apply_action(self.state,action,self.compiled)
        # If this poll raises, there has been no path mutation to unwind.
        if checkpoint:checkpoint()
        self.stack.append(self.state);self.state=child;self.pushes+=1
        self.peak_depth=max(self.peak_depth,self.depth)
        return self.state

    def pop(self):
        if not self.stack:raise ValueError("empty public proof path")
        self.state=self.stack.pop();self.pops+=1
        return self.state

    def assert_balanced(self):
        assert not self.stack and self.pushes==self.pops
        restored=replace(self.state,terminal_status=self.root.terminal_status)
        assert restored==self.root and repr(restored)==repr(self.root)
