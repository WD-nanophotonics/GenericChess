import json,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task728'
for n in [723]:assert json.loads((R/f'results/dev_aux/task{n}/result.json').read_bytes())['status'].startswith('PASS_ALL_')
rows=[]
for task,label in [(721,'C_richroot_mean12_24')]:
 ep=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes())
 for u in ep['updates']:
  cs=u['candidates'];assert all(len(c['goals'])==64 for c in cs)
  drawmeans=[[sum(F(z) for z in c['goals'][r*32:(r+1)*32])/32 for c in cs] for r in [0,1]]
  both=[sum((drawmeans[r][j] for r in [0,1]))/2 for j in range(7)];assert both==[F(c['mean_goal']) for c in cs];two_best=max(range(7),key=lambda j:both[j]);assert two_best==u['selected_index']
  one=[]
  for r in [0,1]:
   sel=max(range(7),key=lambda j:drawmeans[r][j]);gain=drawmeans[r][sel]-drawmeans[r][0];transfer=drawmeans[1-r][sel]-drawmeans[1-r][0];one.append(dict(draw=r,selected_index=sel,accepted=gain>0,own_gain=str(gain),other_draw_gain=str(transfer),other_draw_negative=transfer<0,other_draw_nonpositive=transfer<=0,agrees_with_two_draws=sel==two_best))
  rows.append(dict(method=label,start=u['start'],iteration=u['iteration'],axis=u['axis'],draw_means=[[str(x) for x in mm] for mm in drawmeans],two_draw_selected=two_best,two_draw_gain=str(both[two_best]-both[0]),two_draw_own_gains=[str(drawmeans[r][two_best]-drawmeans[r][0]) for r in [0,1]],one_draw_choices=one))
summary=[]
for label in ['C_richroot_mean12_24']:
 for start in ['unit','random2514']:
  rr=[r for r in rows if r['method']==label and r['start']==start];oo=[x for r in rr for x in r['one_draw_choices']];accepted=[x for x in oo if x['accepted']];summary.append(dict(method=label,start=start,grids=len(rr),one_draw_orders=len(oo),accepted_one_draw=len(accepted),accepted_other_negative=sum(x['other_draw_negative'] for x in accepted),accepted_other_nonpositive=sum(x['other_draw_nonpositive'] for x in accepted),one_two_disagreements=sum(not x['agrees_with_two_draws'] for x in oo),two_draw_accepted=sum(F(r['two_draw_gain'])>0 for r in rr),two_draw_accepted_has_negative_draw=sum(F(r['two_draw_gain'])>0 and any(F(z)<0 for z in r['two_draw_own_gains']) for r in rr)))
out=dict(status='ALL24_RICH_ROOT_VISITED_GRID_TWO_DRAW_SENSITIVITY_PASS',summary=summary,rows=rows,new_go=0,new_games=0,scope=json.loads((R/'results/dev_aux/task705/declaration.json').read_bytes())['scope']+' AppliedtoNEW717richroots ALL24visitedupdates, originallymemoBackup2. Notoldraw rerun; changedgeometry signal andsameconditionallimits.',source_sha256={str(n):hashlib.sha256((R/f'results/dev_aux/task{n}/endpoints.json').read_bytes()).hexdigest() for n in [721]});(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(summary))
