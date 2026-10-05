"""Interface controls, not new Shogi/strength labels or external proof import."""
from types import SimpleNamespace as NS
import pytest
from test_public_goal_intervals import Node,TinyGame,leaf
from scripts.public_goal_intervals import observe

class HintOrderGame(TinyGame):
    def __init__(self,reverse):self.reverse=reverse
    def actions(self,node,checkpoint):
        actions=list(super().actions(node,checkpoint))
        yield from (reversed(actions) if self.reverse else actions)

@pytest.mark.parametrize('attacker',(0,1))
@pytest.mark.parametrize('reverse',(False,True))
def test_one_mate_pv_cannot_close_a_missing_defender(attacker,reverse):
    sign=1 if attacker==0 else -1
    # The source proposes one mate line and pn0, but an additional local reply
    # leads to an ongoing frontier at the same depth. It must stay unknown.
    frontier=Node(attacker)
    defender=Node(1-attacker,(leaf(sign),frontier))
    root=Node(attacker,(defender,))
    source_hint=NS(pn=0,pv=(0,0),claimed_terminal=sign)
    game=HintOrderGame(reverse);game.source_hint=source_hint
    result=observe(root,game,depth=2,max_transitions=8,max_visits=8,clock=lambda:0)
    assert result['interval']==(-1,1) and result['depth_cutoffs']==1
    assert result['transitions']==3 and result['unknown_leaves']==1
    # A complete local adverse terminal refutes that proposed strategy despite
    # the favorable line; changing the source order cannot manufacture a win.
    rejected=Node(attacker,(Node(1-attacker,(leaf(sign),leaf(-sign))),))
    assert observe(rejected,game,depth=2,max_transitions=8,clock=lambda:0)['interval']==(-sign,-sign)
