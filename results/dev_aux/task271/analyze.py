import json,time,hashlib
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task271';X=json.loads((R/'results/dev_aux/task267/result.json').read_bytes());A=json.loads((R/'results/dev_aux/task268/audit.json').read_bytes());assert X['complete'] and A['complete'];start=time.monotonic();out=dict(complete=True,main_H=48,diagnostic_H=[16,32,48],source_sha256=hashlib.sha256((R/'results/dev_aux/task267/result.json').read_bytes()).hexdigest(),new_games=0,groups=[],per_root=[],color_pairs=[],scope='Reuseall128frozen48plytrajectories; mainH48unchanged. H16/32posthocdiagnosticsnotnewchosenprimaryendpoint. NoIIDroot/genericpopulationconfidence; only4old20plyroots. Truepre-Hterminal retained; unknownbyHnotdraw. Actualfinitewin+1/loss-1/else0 definedgoal.')
def stats(rr,H):
 wins=sum(z['termination']=='CHECKMATE' and z['finite_mate_goal']==1 and len(z['actions'])<=H for z in rr);losses=sum(z['termination']=='CHECKMATE' and z['finite_mate_goal']==-1 and len(z['actions'])<=H for z in rr);draws=sum(z['terminal'] and z['actual_terminal_result']==0 and len(z['actions'])<=H for z in rr);n=len(rr);unknown=n-wins-losses-draws;return dict(games=n,H=H,wins=wins,losses=losses,draws=draws,unknown=unknown,finite_net=str(Fraction(wins-losses,n)),censored_final_net_bounds=[str(Fraction(wins-losses-unknown,n)),str(Fraction(wins-losses+unknown,n))])
for n in (1024,16384):
 rr=[z for z in X['calls'] if z['node_limit']==n]
 for H in (16,32,48):
  out['groups'].append(dict(nodes=n,**stats(rr,H)))
  for root in range(4):out['per_root'].append(dict(nodes=n,root=root,**stats([z for z in rr if z['root']==root],H)))
 for op in sorted({z['opponent'] for z in rr}):
  for root in range(4):
   pair=[next(z for z in rr if z['opponent']==op and z['root']==root and z['color']==color) for color in (True,False)];out['color_pairs'].append(dict(nodes=n,opponent=op,root=root,goals=[z['finite_mate_goal'] for z in pair],actual_outcomes=[z['termination'] for z in pair],pair_mean=str(Fraction(sum(z['finite_mate_goal'] for z in pair),2))))
# Perrootallopponents robust direction, dropone root andbothbudgets retained.
out['leave_one_root_out']=[dict(nodes=n,omitted=root,**stats([z for z in X['calls'] if z['node_limit']==n and z['root']!=root],48)) for n in (1024,16384) for root in range(4)];out['seconds']=time.monotonic()-start;(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ('new_games','groups','leave_one_root_out','seconds')},indent=2))
