from pathlib import Path
import json,time,importlib.util,collections,random,hashlib
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1563';O.mkdir(exist_ok=False);plan={'scope':'Exposed64family full6actor3x4 samefixedprices, exactfinite-horizon lexical negamax with materialleaf, no alpha pruning/no positional/native heuristics/no history draw shortcut; not productgenericsearch/fullWDL','depths':[1,3,5],'prices':[720,1728],'max_seconds':180,'max_nodes':2000000,'win_score':100000,'no_price_fit':True};(O/'plan.json').write_text(json.dumps(plan,indent=2));sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1531/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);G=R/'results/dev_aux/task1532';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};truth=json.loads((G/'values.json').read_bytes())['value'];study=json.loads((R/'results/dev_aux/task1535/study.json').read_bytes());start=time.monotonic();counts=collections.Counter();rows=[];error=None
# Fresh exact memo per root; no selective transposition/native score assumed exactWDL.
def search(s,d,price,memo):
 counts['calls']+=1
 if time.monotonic()-start>plan['max_seconds'] or counts['nodes']>=plan['max_nodes']:raise TimeoutError('declared finite search cap')
 key=(s,d)
 if key in memo:counts['memo_hits']+=1;return memo[key]
 counts['nodes']+=1;ll=T.moves(s);counts['legal_generations']+=1
 if not ll:z=-plan['win_score'] if T.attacked(s,s[3*s[6]],1-s[6]) else 0
 elif d==0:
  z=price*((s[1]!=12)-(s[4]!=12))+720*((s[2]!=12)-(s[5]!=12));z*=1 if s[6]==0 else -1;counts['material_leaves']+=1
 else:z=max(-search(t,d-1,price,memo) for u,t in ll)
 memo[key]=z;return z
with (O/'calls.jsonl').open('w') as f:
 try:
  for depth in plan['depths']:
   for price in plan['prices']:
    for fam in study['families']:
     for sid in fam['state_ids']:
      before=counts.copy();memo={};ll=T.moves(states[sid]);scores=[(-search(t,depth-1,price,memo),u,t) for u,t in ll];best=max(x[0] for x in scores);score,move,t=next(x for x in scores if x[0]==best);child=ix[t];row={'family':fam['family'],'state_id':sid,'depth':depth,'R':price,'N':720,'move':move,'finite_score':score,'child_id':child,'chosen_WDL':-truth[child],'work':dict(counts-before)};f.write(json.dumps(row)+'\n');f.flush();rows.append(row)
    print('FINITE',depth,price,len(rows),'nodes',counts['nodes'],'seconds',round(time.monotonic()-start,2),flush=True)
 except BaseException as ex:error=type(ex).__name__+':'+str(ex)
res={'status':'COMPLETE_FINITE_MATERIAL_SEARCH' if error is None else 'PARTIAL_FIXED_CAP_PRESERVED','error':error,'completed_calls':len(rows),'expected_calls':768,'counts':dict(counts),'seconds':time.monotonic()-start,'new_native_go':0,'scope':plan['scope'],'positive_scale_invariance_proof':'All material leaf magnitudes<=2R+2N, including maximumdeclaredscale2 gives9792<100000. Scalingbothweights bypositivea leavesorder betweenfinitecp leaves, draw0 andterminal+-100000 unchanged. Max/negation preserve monotonepiecewiseordering; lex ties unchanged. Hence exactfinite choices dependonratio inthisdeclaredsolver, unlike observedmature leaf-only scale changes; notallnative mechanism attributable.'};(O/'result.json').write_text(json.dumps(res,indent=2));print(res)
