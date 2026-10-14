from pathlib import Path
import json,collections
R=Path.cwd();O=R/'results/dev_aux/task1594';O.mkdir(exist_ok=False);s=list(map(tuple,json.loads((R/'results/dev_aux/task1532/states.json').read_bytes())));oracle=json.loads((R/'results/dev_aux/task1532/values.json').read_bytes())['value'];proof=0
for task,budget in [(1576,64),(1579,4096)]:
 for price in [720,1728]:
  g=json.loads((R/f'results/dev_aux/task{task}/graph_R{price}.json').read_bytes());z=json.loads((R/f'results/dev_aux/task1593/B{budget}_R{price}.json').read_bytes());v=z['value'];rank=z['rank']
  for i,(sid,c) in enumerate(g['keys']):
   adj=g['adj'][i];own=s[sid][6]==c
   if adj:
    ch=[v[j] for j in adj];assert v[i]==(max(ch) if own else min(ch))
    if v[i]:
     exist=(own and v[i]==1) or (not own and v[i]==-1)
     assert any(v[j]==v[i] and rank[j]<rank[i] for j in adj) if exist else all(v[j]==v[i] and rank[j]<rank[i] for j in adj)
    else:assert 0 in ch and (all(x<=0 for x in ch) if own else all(x>=0 for x in ch))
   else:assert v[i]==(oracle[sid]*(1 if own else -1) if g['basis'][i]=='SOLVED_4ACTOR_ACTUAL_POLICY' else g['payoff'][i]) and rank[i]==0
   assert v[i]<=oracle[sid]*(1 if own else -1);proof+=1
out={'status':'PASS_ALL_COMMON_4_BOUNDARY_CONTROL_DECISIVE_RANK_DRAW_SAFETY','states_proved':proof,'new_go':0,'scope':'Parentliteralcontrol/edges/actualchoice proved1580/1582; modifiedboundaryoriginalpriceblindoracle, independentBellman/rank proof no solver import.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
