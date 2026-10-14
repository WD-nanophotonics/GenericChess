from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1525';O.mkdir(exist_ok=False);sel=json.loads((R/'results/dev_aux/task1523/selection.json').read_bytes());plan=json.loads((R/'results/dev_aux/task1521/study.json').read_bytes());gs=[json.loads(x) for x in (R/'results/dev_aux/task1524/choices.jsonl').read_text().splitlines()];old=[json.loads(x) for x in (R/'results/dev_aux/task1506/choices.jsonl').read_text().splitlines()];assert len(gs)==1536 and {x['leafR'] for x in gs}==set(plan['DEV_all_grid']);by={(x['node_budget'],x['leafR'],x['state_id']):x for x in gs};before={(x['node_budget'],x['leafR'],x['state_id']):x for x in old};fam=[f for f in plan['families'] if f['phase']=='DEV'];rows=[]
for budget in plan['nodes']:
 price=next(s['selected'] for s in sel['rows'] if s['budget']==budget)
 for label,p,baseline in [('joint_selected_minus_joint720',price,'joint720'),('joint1728_minus_leaf_only1728',1728,'leaf1728')]:
  fd={}
  for f in fam:
   total=0
   for i in f['state_ids']:
    a=by[budget,p,i];b=by[budget,720,i] if baseline=='joint720' else before[budget,1728,i];total+=a['chosen_WDL']-b['chosen_WDL']
   fd[f['family']]=F(total,2)
  vals=list(map(float,fd.values()));rng=random.Random(2026640500+budget);bs=sorted(sum(rng.choices(vals,k=64))/64 for _ in range(10000));rows.append({'budget':budget,'comparison':label,'candidate':p,'mean':str(sum(fd.values())/64),'bootstrap95_descriptive':[bs[249],bs[9749]],'family_deltas':{f:str(x) for f,x in fd.items()}})
# Uniform720 unchanged-control: exact raw non-time/nps output plusmove andlabels on768TRAIN/384DEV combined.
def stable(lines):
 out=[]
 for line in lines:
  fs=line.split();r=[];i=0
  while i<len(fs):
   if fs[i] in ['time','nps']:i+=2
   else:r.append(fs[i]);i+=1
  out.append(' '.join(r))
 return out
control=0
for newtid,oldtid in [(1522,1504),(1524,1506)]:
 a={(x['node_budget'],x['state_id']):x for x in map(json.loads,(R/f'results/dev_aux/task{newtid}/choices.jsonl').read_text().splitlines()) if x['leafR']==720};b={(x['node_budget'],x['state_id']):x for x in map(json.loads,(R/f'results/dev_aux/task{oldtid}/choices.jsonl').read_text().splitlines()) if x['leafR']==720};assert set(a)==set(b)
 for k in a:assert a[k]['move']==b[k]['move'] and a[k]['chosen_WDL']==b[k]['chosen_WDL'] and stable(a[k]['uci_info'])==stable(b[k]['uci_info']);control+=1
out={'status':'POSTHOC_NATIVE_ALIGNMENT_MECHANISM_PRESERVED_MU','rows':rows,'uniform720_unchanged_exact_controls':control,'actual_DEV_prices':plan['DEV_all_grid'],'scope':'Exposed existingmu mechanism only, not new validation. Coupled nativeR/SEE/order/capture vsleaf-only, allfourDEV prices frozenbeforeTRAIN. Selector DEV_union isunusedinformational, actualplan allgrid owns execution. No futurepricefit usingDEV.'};(O/'result.json').write_text(json.dumps(out,indent=2));print([{k:v for k,v in x.items() if k!='family_deltas'} for x in rows]);print('controls',control)
