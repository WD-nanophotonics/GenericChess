from pathlib import Path
import json,math
T=Path('results/dev_aux/task2534');O=Path('results/dev_aux/task2536')
def near(x,y):return math.isclose(x,y,rel_tol=1e-7,abs_tol=1e-9)
def run():
 active=[0]*6;first={};terminal=0;queries=0
 for line in(T/'queries.jsonl').open():
  q=json.loads(line)
  if not q['complete']:continue
  queries+=1
  if q['pv_terminal']:terminal+=1;assert q['gradient']==[0.]*6;continue
  w=q['weights'];phi=q['pv_phi'];v=math.tanh(sum(x*y for x,y in zip(w,phi))/10)
  for j,x in enumerate(phi):
   active[j]+=x!=0
   if x and j not in first:
    h=1e-5;plus=list(w);minus=list(w);plus[j]+=h;minus[j]-=h
    numeric=(math.tanh(sum(a*b for a,b in zip(plus,phi))/10)-math.tanh(sum(a*b for a,b in zip(minus,phi))/10))/(2*h);exact=x*(1-v*v)/10;assert near(numeric,exact)
    first[j]=dict(rule=q['generator_seed'],method=q['method'],seed=q['seed'],game=q['game'],ply=q['ply'],phi=phi,weights=w,numerical=numeric,analytic=exact,actual_trainer_gradient=q['gradient'][j])
 result=dict(status='PASS_ACTUAL_PV_PARTIALS_AND_TERMINAL_CONSTANTS',complete_queries=queries,terminal_constants=terminal,ordinary_coordinate_nonzero_counts=active,coordinate_witnesses=first,scope='FirstnonzeroactualordinaryPVforeachcoordinate, nooutcome/fitselection. Finitepartials includeP eveniffixed5mask0; alltrainingcreditmaskcheckedseparately. ActualterminalPVconstantgradients0; earliertracesnotremoved. Notfullfeaturedomain orstrengthproof.')
 (O/'partials.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='coordinate_witnesses'}))
if __name__=='__main__':run()
