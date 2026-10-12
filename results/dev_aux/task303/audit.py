import json,time,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task303';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task302/audit.json').read_bytes());P=json.loads((R/'results/dev_aux/task301/declaration.json').read_bytes());T=json.loads((R/'results/dev_aux/task258/tree.json').read_bytes());start=time.monotonic();rows=[]
def score(t,w,scale):
 def val(ld):return ld['terminal']*scale if 'terminal' in ld else sum(w[k]*x for k,x in zip('PNBRQ',ld['vector']))
 return max(min(val(br['terminal']) if 'terminal' in br else max(val(ch['leaf']) for ch in br['children']) for br in a['branches']) for a in t['actions'])
for p in D['details']:
 t=next(z for z in T['roots'] if z['root']==p['root']);w={k:v*1024 for k,v in P['profiles'][p['profile']].items()};base=score(t,w,1024);assert base==p['base_score']*1024
 for a in p['axes']:
  if a['PV_matches_both_exact']:continue
  plus=w.copy();minus=w.copy();plus[a['piece']]+=1;minus[a['piece']]-=1;fp=score(t,plus,1024)-base;fm=base-score(t,minus,1024);assert fp==a['exact_positive_directional'] and fm==a['exact_negative_directional'];rows.append(dict(root=p['root'],profile=p['profile'],piece=a['piece'],PV_branch_slope=a['PV_branch_slope'],right=fp,left=fm,base_score=p['base_score'],base_action=p['base_action'],Native_oneunit_plus=a['oneunit_positive'],Native_oneunit_minus=a['oneunit_negative']))
out=dict(complete=True,independent_scalar_integer_checks=len(rows),epsilon='1/1024',mismatches=rows,seconds=time.monotonic()-start,proof='Allleafbasevaluesareintegers, so anystrict leafgap>=1. Maxdifference inonecoordinateleafslopes onthisChess tree<64. Perturbation1/1024cannotchangeastrictleaforder; onlyties change, so scaledfinite-differenceexactly equalsone-sided directionalderivative. Scalarrecursive max/min usesexactPythonint, noNumPyreduceat. Scale1024appliedterminalalso, analyticalonly, notNativeconfiguredprices.',scope='The12actualPV-branchslopes are not unconditionalroot-directionalderivatives; one-unitNativecounterfactuals allqualified302. Axisleft/rightequalityalone doesnotprove multidifferentiability. NoTD training/rejectionofallTD algorithms orallmateriallearning.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))