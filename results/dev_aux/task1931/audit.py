"""All closed-study profiles, fixed-opponent factorial contrasts, and local stability."""
from pathlib import Path
from collections import Counter,defaultdict
from itertools import product
import json,random,time
from results.dev_aux.task1928.audit import audit
O=Path('results/dev_aux/task1931')
def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(x) for x in Path(p).read_text().splitlines()]
def profile(folder):
 p=Path(folder);games=lines(p/'games.jsonl');moves=lines(p/'moves.jsonl');events=lines(p/'run/transport.jsonl');steps=[m for m in moves if m['source']=='EXTERNAL_SEARCH'];profiles=[e for e in events if e['event']=='PROFILE'];clears=[e for e in events if e['event']=='CLEAR'];choices=[e for e in events if e['event']=='CHOICE'];intent=[e for e in events if e['event']=='INTENT'];assert len(steps)==len(profiles)==len(clears)==len(choices)==len(intent)
 for step,pr,cl,ch,ins in zip(steps,profiles,clears,choices,intent):
  g=games[step['slot']];r=g['R'] if step['side']==g['candidate_side'] else 720;n=g['N'] if step['side']==g['candidate_side'] else 720;expected=f'info string DEV_AUX leafRNBP {r} {n} {n} {n} nativeP {n} nativeR {r} nativeN {n} nativeB {n} captureP {n} captureR {r} captureN {n} captureB {n}';assert expected in pr['ack'] and pr['values']==cl['values']==ch['R']==ins['R']==[r,n,n,n] and 'readyok' in cl['raw']
 opts={e['name']:e['value'] for e in events if e['event']=='OPTION'};assert opts['Threads']==1 and opts['Hash']==16 and opts['Use NNUE']=='false'
 return dict(status='PASS_ALL_PROFILES_CLEAR_AND_NATIVE_BINDINGS',queries=len(steps),options_checked=['Threads1','Hash16','NNUEfalse'])
def stats(deltas,bounds=None):
 rng=random.Random(20261016631931);boot=sorted(sum(rng.choices(deltas,k=16))/16 for _ in range(20000));nz=[d for d in deltas if d];obs=abs(sum(nz));sign=sum(abs(sum(a*b for a,b in zip(s,nz)))>=obs for s in product((-1,1),repeat=len(nz)))/(2**len(nz));out=dict(mean=sum(deltas)/16,family_deltas=deltas,family95=[boot[500],boot[19499]],nonzero_families=len(nz),independent_symmetric_effect_sign_sensitivity=sign)
 if bounds is not None:out['unknown_ultimate_extreme_bounds']=[sum(b[k] for b in bounds)/32 for k in (0,1)]
 return out
def bound(g,coefficient):
 if g['outcome']=='UNKNOWN':return (-abs(coefficient),abs(coefficient))
 return (coefficient*g['finite_event_score'],)*2

def run():
 beg=time.perf_counter();reports={str(t):audit(f'results/dev_aux/task{t}') for t in (1920,1925,1926,1929)};profiles={str(t):profile(f'results/dev_aux/task{t}') for t in (1920,1925,1926,1929)}
 on=lines('results/dev_aux/task1925/games.jsonl');off=lines('results/dev_aux/task1926/games.jsonl');idx={(g['opponent_nodes'],g['family'],g['candidate_side'],g['ratio'],flag):g for flag,gs in [(True,on),(False,off)] for g in gs};assert len(idx)==256
 assert read('results/dev_aux/task1920/selection-before-dev.json')['selected']==3.;factorial=[]
 for opp in (64,512):
  cells=[]
  for proof in (False,True):
   for ratio in (1.,3.):
    gs=[idx[opp,f,s,ratio,proof] for f in range(16) for s in (0,1)];cells.append(dict(proof=proof,ratio=ratio,outcomes=dict(Counter(g['outcome'] for g in gs)),net=sum(g['finite_event_score'] for g in gs),seconds=sum(g['seconds'] for g in gs)))
  effects={}
  contrasts={'price_with_proof':[(3.,True,1),(1.,True,-1)],'price_without_proof':[(3.,False,1),(1.,False,-1)],'proof_at_baseline':[(1.,True,1),(1.,False,-1)],'proof_at_learned':[(3.,True,1),(3.,False,-1)],'interaction':[(3.,True,1),(1.,True,-1),(3.,False,-1),(1.,False,1)]}
  for name,terms in contrasts.items():
   deltas=[];bounds=[];roles=Counter()
   for family in range(16):
    ds=[]
    for side in (0,1):
     value=sum(coef*idx[opp,family,side,ratio,proof]['finite_event_score'] for ratio,proof,coef in terms);ds.append(value);roles[side]+=value;parts=[bound(idx[opp,family,side,ratio,proof],coef) for ratio,proof,coef in terms];bounds.append(tuple(sum(b[k] for b in parts) for k in (0,1)))
    deltas.append(sum(ds)/2)
   effects[name]={**stats(deltas,bounds), 'role_means':{s:v/16 for s,v in roles.items()}}
  factorial.append(dict(opponent_nodes=opp,cells=cells,effects=effects))
 local=lines('results/dev_aux/task1929/games.jsonl');li={(g['family'],g['candidate_side'],g['ratio']):g for g in local};localcells=[];localeffects=[]
 for ratio in (2.85,3.,3.15):
  gs=[g for g in local if g['ratio']==ratio];assert len(gs)==32;localcells.append(dict(ratio=ratio,outcomes=dict(Counter(g['outcome'] for g in gs)),net=sum(g['finite_event_score'] for g in gs),seconds=sum(g['seconds'] for g in gs)))
  if ratio==3.:continue
  ds=[];bounds=[]
  for family in range(16):
   values=[]
   for side in (0,1):
    a,b=li[family,side,3.],li[family,side,ratio];values.append(b['finite_event_score']-a['finite_event_score']);lo=bound(a,-1);hi=bound(b,1);bounds.append((lo[0]+hi[0],lo[1]+hi[1]))
   ds.append(sum(values)/2)
  localeffects.append(dict(perturbation=ratio,minus_center=stats(ds,bounds)))
 out=dict(status='PASS_ALL_CLOSED_PROFILE_AND_FACTORIAL_AUDITS',reports=reports,profiles=profiles,factorial=factorial,local_robustness=dict(cells=localcells,effects=localeffects,scope='ALL16EXPOSEDTRAINfamilies, +/-5percentfixedfromTRAINselected3. No newpriceorDEVselection/freshvalidation.'),total_actual_policy_games=22+sum(r['games'] for r in reports.values()),total_moves=816+sum(r['moves'] for r in reports.values()),total_native_bindings=746+sum(r['actual_native'] for r in reports.values()),total_proof_games=8+sum(r['proof_games'] for r in reports.values()),seconds=time.perf_counter()-beg,scope='Fixedopponentseparatelyforeachν; ONLYcandidateproofstrategychangedON/OFF, same normal4096/.1s andouter2.75s caps, actualcostdiffers. Baseline/learnedprices samefixedproofarm withinB-D. All16CONFIRMfamilies sharedacrossopponents/roles/methods, NOTindependentgamecountor32clusters. CIsunadjusteddescriptive/smalln, signnullsymmetriconly. UNKNOWN0finiteeventneverdraw/infiniteWDL. No labels/humansfitted.')
 with (O/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps({k:out[k] for k in ['status','total_actual_policy_games','total_moves','total_native_bindings','total_proof_games','seconds']}));print(json.dumps(dict(factorial=factorial,local=out['local_robustness'])))
if __name__=='__main__':run()
