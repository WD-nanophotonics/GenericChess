import json,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task196';P=R/'results/dev_aux/task187';C=json.loads((P/'controller.json').read_bytes());A=json.loads((R/'results/dev_aux/task190/analysis.json').read_bytes());by={c['context']['name']:c for c in C['calls']};rows=[];conflicts=[]
def part(c):
 s=c['result']['score'];cat='cutoff_unknown' if not s['terminal'] else 'draw' if s['winner'] is None else 'win' if s['winner']==c['context']['agent_color'] else 'loss';return dict(category=cat,net=1 if cat=='win' else -1 if cat=='loss' else 0,cutoff240=16*s['quantity_difference'] if cat=='cutoff_unknown' else 0,bounded240=round(c['result']['bounded_reward']*240))
def summarize(groups):
 out=[]
 for arm,g in enumerate(groups):
  cats={k:sum(c['category']==k for c in g) for k in ('win','loss','draw','cutoff_unknown')};assert sum(cats.values())==len(g);out.append(dict(arm=arm,denominator=len(g),categories=cats,net=sum(c['net'] for c in g),cutoff240=sum(c['cutoff240'] for c in g),bounded240=sum(c['bounded240'] for c in g),cutoff_rate=cats['cutoff_unknown']/len(g)))
 return out
for a in A['rows']:
 gs=[[part(by[f"s{a['seed']}-{a['objective']}-train-g{a['sweep']}-k{'NBRQ'.index(a['coordinate'])}-a{arm}-o{oi}-c{int(col)}"]) for oi in range(8) for col in (True,False)] for arm in range(3)];ss=summarize(gs);lex=[(v['net'],v['cutoff240']) for v in ss];lexset=[i for i,v in enumerate(lex) if v==max(lex)];bounded=[v['bounded240'] for v in ss];bset=[i for i,v in enumerate(bounded) if v==max(bounded)];assert lexset==a['best']['wdl_then_cutoff_quantity'] and bset==a['best']['bounded'];r=dict(seed=a['seed'],objective=a['objective'],sweep=a['sweep'],coordinate=a['coordinate'],selected=a['selected'],arms=ss,lexicographic_best=lexset,bounded_best=bset);rows.append(r)
 if a['objective'].endswith('bounded') and ss[a['selected']]['net']<max(v['net'] for v in ss):
  selected=a['selected'];other=lexset[0];details=[];deletions=[]
  for oi in range(8):
   pp=[g[2*oi:2*oi+2] for g in gs];details.append(dict(root=oi,all_arm_color_records=pp,selected_vs_other_net=sum(v['net'] for v in pp[selected])-sum(v['net'] for v in pp[other]),selected_vs_other_cutoff240=sum(v['cutoff240'] for v in pp[selected])-sum(v['cutoff240'] for v in pp[other])))
   zz=summarize([g[:2*oi]+g[2*oi+2:] for g in gs]);bs=[v['bounded240'] for v in zz];bb=[i for i,v in enumerate(bs) if v==max(bs)];deletions.append(dict(removed_root=oi,denominator=14,bounded_best=bb,any_bounded_best_sacrifices_completednet=any(zz[i]['net']<max(v['net'] for v in zz) for i in bb)))
  conflicts.append(dict(**r,alternative=other,completed_net_sacrificed=ss[other]['net']-ss[selected]['net'],cutoff_gain240=ss[selected]['cutoff240']-ss[other]['cutoff240'],root_details=details,whole_root_deletions=deletions))
out=dict(complete=True,choices=len(rows),strict_conflicts=len(conflicts),conflicts=conflicts,rows=rows,source_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest(),adoption='Dot advice adopted: allfourcategories/fixedallcase denominator/whole-root conflict check; defer newlexlearning. Correction: cutoffquantity/15 SAME in bothobjectivearms. Terminalamplitude andspeed differ jointly.',scope='Completednetby16ply only; cutoffs unknown, nottrue draws/finalWDL.8rootclusters,colorsnotindependent. Exactsavedcandidate diagnostic, notnewpolicy/trajectory/deploymentproof.')
(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(choices=len(rows),conflicts=[dict(seed=c['seed'],coordinate=c['coordinate'],sweep=c['sweep'],sacrifice=c['completed_net_sacrificed'],cutoff_gain240=c['cutoff_gain240'],deletions=c['whole_root_deletions']) for c in conflicts]),indent=2))
