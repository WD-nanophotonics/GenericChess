"""Finite arithmetic falsifiers; no product/Core/Player imports."""
import json
from pathlib import Path

def minimax(t,depth,b):
    if depth==0:return t+b
    return max(-minimax(c,depth-1,b) for c in t)

# Every leaf is ordinary static evaluation from its own side to move.
tree2=[[4,7],[10,12],[2,3]]
tree1=[-9,-3]
rows=[]
for b in range(-3,4):
    t=minimax(tree2,2,b)
    a=minimax(tree1,1,b)
    assert t==10+b and a==9-b
    # Same-depth action rankings stay fixed under the common shift.
    assert max(range(3),key=lambda i:-minimax(tree2[i],1,b))==1
    assert max(range(2),key=lambda i:-(tree1[i]+b))==0
    rows.append(dict(bias=b,tt_depth2=t,excluded_depth1=a,zero_margin_trigger=a<t))
assert rows[3]['zero_margin_trigger'] is True
assert rows[2]['zero_margin_trigger'] is False
# Equal parity does preserve a common shift for these uniform all-static trees.
for b in range(-3,4):
    assert minimax(tree2,2,b)-minimax(tree2,2,0)==b
    assert minimax(tree1,1,b)-minimax(tree1,1,0)==-b
# A fixed terminal outcome does not receive heuristic bias.
# Uniform nominal depth therefore alone is not sufficient with mixed exits.
mixed=[dict(bias=b,terminal=0,heuristic=1-b,chosen='heuristic' if 1-b>0 else 'terminal') for b in range(-3,4)]
assert mixed[3]['chosen']!=mixed[5]['chosen']
print(json.dumps({'cross_depth':rows,'mixed_terminal':mixed,'conclusion':'zero margin alone does not ensure bias invariance;toy arithmetic only'},indent=2))
