"""Concrete observed cycle choice that material prices cannot separate at D3."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,ast,functools,array
R=Path.cwd();O=R/'results/dev_aux/task1758';O.mkdir(exist_ok=False);tr=ast.parse((R/'results/dev_aux/task1688/qualify_literal_fixed.py').read_text(encoding='utf-8-sig'));fn=next(x for x in tr.body if isinstance(x,ast.FunctionDef) and x.name=='ref');fn.body[-1]=ast.Return(value=ast.Tuple(elts=[fn.body[-1].value,ast.Call(func=ast.Name(id='check',ctx=ast.Load()),args=[ast.Name(id='d',ctx=ast.Load()),ast.Name(id='c',ctx=ast.Load())],keywords=[])],ctx=ast.Load()));ast.fix_missing_locations(fn);ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'independentactor','exec'),ns);ref=functools.lru_cache(maxsize=100000)(ns['ref'])
wdl=(R/'results/dev_aux/task1741/wdl8.bin').read_bytes();rank=array.array('H');rank.frombytes((R/'results/dev_aux/task1741/rank8.bin').read_bytes())
def normalize(s):
 return tuple(v.swapcase() for v in s[:-1])+(1-s[-1],) if 'r' in s else tuple(s)
def rid(s):return (((s[:-1].index('K')*64+s[:-1].index('k'))*64+s[:-1].index('R'))*2+s[-1])
@functools.lru_cache(maxsize=100000)
def full(s,d,theta,ply):
 ll,ch=ref(s)
 if not ll:return (-32000+ply if s[-1]==0 else 32000-ply) if ch else 0
 if d==0:return theta if 'R' in s else 0
 vv=[full(t,d-1,theta,ply+1) for u,t in ll]
 return (max if s[-1]==0 else min)(vv)
examples=[]
for row in map(json.loads,(R/'results/dev_aux/task1742/records.jsonl').open()):
 if row['conversion']!='ACTUAL_DRAW_DESPITE_RULE_FORCED_WIN':continue
 for step in row['R_side_moves']:
  if step['DTM']<=6 or step['child_DTM']<step['DTM']:continue
  s=normalize(tuple(step['state']));assert s[-1]==0 and wdl[rid(s)]==1;ll=ref(s)[0];greedy=[u for u,t in ll if 'R' in t and wdl[rid(t)]==2 and rank[rid(t)]==rank[rid(s)]-1];assert greedy
  matrix={theta:{u:full(t,2,theta,1) for u,t in ll} for theta in (90,720,1440,4096)}
  best={theta:sorted(u for u,v in vals.items() if v==max(vals.values())) for theta,vals in matrix.items()}
  if not all(step['move'] in b and set(greedy)&set(b) for b in best.values()):continue
  assert all(b==best[90] for b in best.values()) and all(set(v.values())<={0,theta} for theta,v in matrix.items())
  examples.append(dict(source_task=row['source_task'],family=row['family'],price=row['price'],opponent=row['opponent'],state=s,observed_cycling_move=step['move'],DTM=step['DTM'],child_DTM=step['child_DTM'],rank_optimal_actions=greedy,full_D3_best_actions=best[90],full_D3_action_values={str(k):v for k,v in matrix.items()},actual_native_nodes=step['nodes'],actual_native_reported_depth=step['max_reported_depth']))
  break
 if len(examples)>=4:break
assert examples
out=dict(status='PASS_OBSERVED_MATERIAL_INDISTINGUISHABLE_PROGRESS_COUNTEREXAMPLES',examples=examples,actual_native_go=0,proof_scope='InclosedKRK rootRowner atD3, every evaluatednonterminal payoff0orpositiveThetaR andallrootminimaxvalues0orThetaR; exactDTMdescending move andactualcyclingchoice tieforALLtested90/720/1440/4096. Moregenerally anypositiveThetaRbelowmatepriority preservesordinalorder becauseonlyRmaterialexists; otherpiecepricesinactive. NoR-onlyscalar canencodeDTMamongsameinventory. NotproofNativeallbudgets cycle; Nativefixedthresholdsmaybreakties differently. Doesnotimplypiecepricescannotlearn earlierexchangechoices.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(dict(status=out['status'],examples=len(examples),first=examples[0]))

