import json,sys,time,re,math,collections
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task867';O.mkdir(exist_ok=False);start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,audit as V
rows=[json.loads(l) for l in (R/'results/dev_aux/task866/queries.jsonl').open(encoding='utf-8')];assert len(rows)==224;table={(q['case_index'],q['axis'],q['sign']):q for q in rows};counts=collections.Counter();tests=[]
for q in rows:
 A.validate_search(q);b=A.replay(q['initial_sfen'],q['history']);a=q['leaf_state'].split(' ',4);assert int(a[3])==A.material(b,q['leaf_weights'])*(1 if b.turn==0 else -1);counts['allquery_material_and_PV_validated']+=1
sel=lambda q:next((l for l in reversed(q['lines']) if 'score cp ' in l and 'upperbound' not in l and 'lowerbound' not in l and ' pv ' in l),None)
for ci in range(32):
 for axis in [3,5,6]:
  qq=[table[ci,0,0],table[ci,axis,-1],table[ci,axis,1]];ll=[sel(q) for q in qq];reason=None
  if any(l is None for l in ll):reason='no_unbounded_cp_PV'
  if not reason:
   pv=[l.split(' pv ',1)[1].split() for l in ll];depth=[int(re.search(r'\bdepth (\d+)',l)[1]) for l in ll]
   if pv[0]!=pv[1] or pv[0]!=pv[2]:reason='printedPV_changed'
   elif depth[0]!=depth[1] or depth[0]!=depth[2]:reason='depth_changed'
   elif len({q['bestmove'] for q in qq})!=1:reason='bestmove_changed'
  counts[reason or 'qualified_same_PV_depth_bestmove']+=1;test=dict(case_index=ci,axis=axis,nodes=qq[0]['nodes_limit'],qualification=reason or 'same_PV_depth_bestmove')
  if not reason:
   cps=[int(re.search(r' score cp (-?\d+)',l)[1]) for l in ll];material=[]
   for q in qq:
    b=A.replay(q['initial_sfen'],q['history']);turn=b.turn
    for u in pv[0]:m=A.shogi.Move.from_usi(u);assert m in b.legal_moves;b.push(m)
    raw=A.material(b,q['leaf_weights'])*(1 if turn==0 else -1);material.append(math.trunc(100*raw/90))
   actual=[cps[i]-cps[0] for i in [1,2]];expected=[material[i]-material[0] for i in [1,2]];errors=[a-e for a,e in zip(actual,expected)];wrong=any(abs(e)>1 for e in errors);counts['qualified_wrong_increment_over1cp']+=wrong;test.update(PV=pv[0],depth=depth[0],reported_cp=cps,PV_leaf_cp=material,actual_increments=actual,expected_PV_increments=expected,errors=errors,falsifies_tolerance1cp=wrong)
  tests.append(test)
result=dict(status='ALL96_FINITE_LEAF_GRADIENT_ASSUMPTION_TESTS',counts=dict(counts),tests=tests,actual_new_go_in866=224,new_go=0,seconds=time.perf_counter()-start,scope='All224physicalquerylegal/PV/native+leafreadbacks. Strict3pointPV/depth/bestmove equality andlastunboundedCP; absincrementerror>1cp toleratesUSItruncation. Finiteperturb16 notinfinitesimal; excludedcasesretained. Wrongincrements rejectstableprintedPV sufficientassumption, matchingnotexactgradientcertificate. No learning/pricefitness.')
(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result['status'],counts,round(result['seconds'],3));print('COUNTEREXAMPLE',next((t for t in tests if t.get('falsifies_tolerance1cp')),None))
