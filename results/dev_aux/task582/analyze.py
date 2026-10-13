import json,time,math,re
from fractions import Fraction
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task582';d=json.loads((R/'results/dev_aux/task580/declaration.json').read_bytes());r=json.loads((R/'results/dev_aux/task580/result.json').read_bytes());assert json.loads((R/'results/dev_aux/task581/result.json').read_bytes())['status']=='PASS';start=time.perf_counter();gs=[json.loads(x) for x in (R/'results/dev_aux/task580/games.jsonl').open()];rows=[];symmetry=[]
def values(pi,opp,m):
 gg=[g for g in gs if g['profile']==pi and g['opponent']==opp];assert len(gg)==20;return [Fraction(g['goal']) if m=='mixed' else Fraction(0 if g['termination']['winner'] is None else 32 if g['termination']['winner']==g['color'] else -32) for g in gg]
for opp in d['opponents']:
 for a in d['axes']:
  minus=next(i for i,p in enumerate(d['profiles']) if p['axis']==a and p['sign']==-1);plus=next(i for i,p in enumerate(d['profiles']) if p['axis']==a and p['sign']==1)
  for m in ['mixed','terminal']:
   vv=[values(i,opp,m) for i in [0,minus,plus]];mu=[sum(v)/20 for v in vv];choice=max(range(3),key=lambda i:mu[i]);fam=[[sum(v[2*k:2*k+2])/2 for k in range(10)] for v in vv];loo=[]
   for k in range(10):
    ms=[(sum(v)-fam[i][k]*2)/18 for i,v in enumerate(vv)];b=max(range(3),key=lambda i:ms[i]);loo.append(dict(omitted_family=k,chosen=['base','minus','plus'][b],gain=str(ms[b]-ms[0])))
   group=[g for g in gs if g['opponent']==opp and g['profile']==minus];pg=[g for g in gs if g['opponent']==opp and g['profile']==plus];base=[g for g in gs if g['opponent']==opp and g['profile']==0]
   rows.append(dict(opponent=opp,axis=a,metric=m,means=dict(zip(['base','minus','plus'],map(str,mu))),selected_local=['base','minus','plus'][choice],strict_gain=str(mu[choice]-mu[0]),all_means_tied=len(set(mu))==1,cells_differ=sum(vv[1][i]!=vv[2][i] for i in range(20)),terminal_labels_differ=sum(group[i]['termination']!=pg[i]['termination'] for i in range(20)),trajectory_differ=sum(group[i]['actions']!=pg[i]['actions'] for i in range(20)),plus_base_same_paths=sum(pg[i]['actions']==base[i]['actions'] for i in range(20)),minus_base_same_paths=sum(group[i]['actions']==base[i]['actions'] for i in range(20)),leave_one=loo))
# Equal-priceunit controls bothcolors have sameactualpath and oppositequantitygoals, notunmeasuredselfmatches.
for k in range(10):
 pair=[g for g in gs if g['profile']==0 and g['opponent']=='unit' and g['root']['index']==k];assert len(pair)==2 and pair[0]['actions']==pair[1]['actions'] and pair[0]['termination']==pair[1]['termination'] and Fraction(pair[0]['goal'])==-Fraction(pair[1]['goal']);symmetry.append(dict(root=k,actual_path_equal=True,goals=[g['goal'] for g in pair]))
summary=[]
for opp in d['opponents']:
 for m in ['mixed','terminal']:
  rr=[x for x in rows if x['opponent']==opp and x['metric']==m];summary.append(dict(opponent=opp,metric=m,axes=12,axes_all_means_tied=sum(x['all_means_tied'] for x in rr),axes_cells_differ=sum(x['cells_differ']>0 for x in rr),axes_strict_improvement=sum(Fraction(x['strict_gain'])>0 for x in rr),axes_nonbase_same_strict_choice_all_omissions=sum(x['selected_local']!='base' and all(v['chosen']==x['selected_local'] and Fraction(v['gain'])>0 for v in x['leave_one']) for x in rr)))
out=dict(status='PASS_ALL_LOCAL_RESPONSES',actual_games=1000,actual_go=r['actual_go'],summary=summary,rows=rows,equal_price_symmetry=symmetry,actual_rule_terminations=sum(g['termination']['kind']!='cap12' for g in gs),new_go=0,seconds=time.perf_counter()-start,scope='ALLaxis +/-25price actualexposedrootcell/trajectory/mean/leave-one responses; no globalflatness/priceidentifiability/modeltraining/rank-fitting inference. Localmixed gradients arequantityproxy effects ifterminal0. Baselineunit equal-price symmetry independentlycheckedactualpaths; sourcevalues notused.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ['rows','equal_price_symmetry']}));print(json.dumps([x for x in rows if x['metric']=='mixed']))
