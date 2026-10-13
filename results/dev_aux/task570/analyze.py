import json,time,math,statistics,sys,hashlib
from pathlib import Path
from fractions import Fraction
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task570';start=time.perf_counter();D=R/'results/dev_aux/task564/declaration.json';d=json.loads(D.read_bytes());assert json.loads((R/'results/dev_aux/task568/result.json').read_bytes())['status']=='PASS';assert json.loads((R/'results/dev_aux/task569/result.json').read_bytes())['status']=='PASS';pure=json.loads((R/'results/dev_aux/task560/result.json').read_bytes());old=json.loads((R/'results/dev_aux/task556/result.json').read_bytes());new=json.loads((R/'results/dev_aux/task567/result.json').read_bytes());assert new['status']=='COMPLETE';sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
# Fixed diagnostic beforeitsderivation, afterphysicalstudy endpoints; no adaptivefitness orroot selection.
plan=dict(question='ALL H12mixed/H24pure models ALL same16developmentfamilies: cheaperfeedback vsdescriptive piecevalues, no selectedwinners',cutoffs=[12,24],goals=['mixed','terminal','fast'],family_group='sameindependentseed;bothcolorsmean; leaveonefamily notnewholdout',source_sha256={str(n):hashlib.sha256((R/f'results/dev_aux/task{n}/result.json').read_bytes()).hexdigest() for n in [556,567,568,569]},endpoint_freezes={str(n):json.loads((R/f'results/dev_aux/task{n}/all_endpoints_frozen.json').read_bytes()) for n in [553,564]},scope='Post-execution secondarypaired cutoffdiagnostic not preregisteredindependentvalidation; two trainingroutes differedbothH/objective, unequalcost. No counterfactualtrainingH12inference fromH24prefix. Allsourceagreementdescriptive only afterALL8endpoints/physicaldevfrozen, neverfit/root/H/selector/stop. Original24purevalidation reused, notnewholdout.',at=time.time());(O/'declaration.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
games={};cells=[]
for task,res,route in [(556,old,'pure24'),(567,new,'mixed12')]:
 gs=[json.loads(x) for x in (R/f'results/dev_aux/task{task}/games.jsonl').open()];games[task]=gs
 for row in res['rows']:
  cells.append(dict(route=route,names=row['names'],opponent=row['opponent'],games=[gs[s['line']-1] for s in row['batch']['sources']]))
def prefix(g,H):
 f=g['root'];b=C.Board(f['initial_sfen']);states=[' '.join(b.sfen().split()[:3])];movers=[];gave=[]
 for u in f['history']:
  assert V.terminal(b,states,movers,gave) is None;m=b.move_from_usi(u);assert b.is_legal(m);movers.append(b.turn);b.push(m);gave.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]))
 aa=g['actions'][:H]
 for a in aa:
  assert V.terminal(b,states,movers,gave) is None;assert b.sfen()==a['before_sfen'];m=b.move_from_usi(a['move']);assert b.is_legal(m);movers.append(b.turn);b.push(m);gave.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]));assert b.sfen()==a['after_sfen']
 t=V.terminal(b,states,movers,gave);score,qty=V.literal(b.sfen(),g['weights']);term=Fraction(0) if t is None or t['winner'] is None else Fraction(32 if t['winner']==g['color'] else -32);q=Fraction(qty[g['color']]-qty[1-g['color']],19) if t is None else Fraction(0)
 return dict(root=f['index'],color=g['color'],status='UNFINISHED' if t is None else 'DRAW' if t['winner'] is None else 'WIN' if t['winner']==g['color'] else 'LOSS',mixed=term+q,terminal=term,fast=term+(0 if t is None or t['winner'] is None else (1 if t['winner']==g['color'] else -1)*Fraction(H-len(aa),H)),go=sum(x['ply']<H for x in g['queries']),plies=len(aa))
cache={}
for cell in cells:
 for H in [12,24]:cache[(cell['route'],tuple(cell['names']),cell['opponent'],H)]=[prefix(g,H) for g in cell['games']]
metrics=[];descriptors=list(pure['source_prior_descriptors']);ref=pure['source_prior'];resources=[];components=[];N=32
for task,opp in [(565,'unit'),(566,'random')]:
 ep=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes());res=json.loads((R/f'results/dev_aux/task{task}/result.json').read_bytes());resources.append(dict(route='mixed12',opponent=opp,actual_games=res['actual_games'],actual_go=res['actual_go'],fit_wall_seconds=res['seconds']))
 for e in ep['endpoints']:
  descriptors.append(dict(route='mixed12',training_opponent=opp,family=e['family'],initial=e['initial'],endpoint=e['endpoint'],initial_log_ratio_MSE_to_source_prior=statistics.mean(math.log(e['initial'][a]/ref[a])**2 for a in d['axes']),endpoint_log_ratio_MSE_to_source_prior=statistics.mean(math.log(e['endpoint'][a]/ref[a])**2 for a in d['axes'])))
  us=[u for u in ep['updates'] if u['family']==e['family']];components.append(dict(route='mixed12',training_opponent=opp,family=e['family'],accepted=sum(Fraction(u['accepted_strict_gain'])>0 for u in us),all_three_means_tied=sum(len(set(c['mean_goal'] for c in u['candidates']))==1 for u in us),terminal_only_selected_different=sum(max(range(3),key=lambda j:sum(map(Fraction,[str(Fraction(v) if abs(Fraction(v))==32 else 0) for k,v in zip(u['candidates'][j]['rule_outcomes'],u['candidates'][j]['physical_goals'])])))!=u['selected_index'] for u in us)))
# ALL8models,bothtrainingopponents,bothstarts,bothevalopps,bothH,all3metrics. Reusepureinitialphysicalrecords exactly.
for route,tasks in [('pure24',[(554,'unit'),(555,'random')]),('mixed12',[(565,'unit'),(566,'random')])]:
 for task,opp in tasks:
  ep=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes())
  for e in ep['endpoints']:
   name=opp+'-'+e['family']
   for env in ['unit','random']:
    ai=next(c for c in cells if c['route']=='pure24' and c['opponent']==env and name+'-initial' in c['names']);bi=next(c for c in cells if c['route']==route and c['opponent']==env and name+'-endpoint' in c['names'])
    for H in [12,24]:
     a=cache[('pure24',tuple(ai['names']),env,H)];b=cache[(route,tuple(bi['names']),env,H)];assert len(a)==len(b)==N
     for m in ['mixed','terminal','fast']:
      diff=[y[m]-x[m] for x,y in zip(a,b)];fam=[sum(diff[i:i+2])/2 for i in range(0,N,2)];metrics.append(dict(route=route,training_opponent=opp,start=e['family'],evaluation_opponent=env,cutoff=H,metric=m,initial_mean=str(sum(x[m] for x in a)/N),endpoint_mean=str(sum(x[m] for x in b)/N),gain=str(sum(diff)/N),root_family_gains=list(map(str,fam)),leave_one_family_gains=[str(sum(x for j,x in enumerate(fam) if i!=j)/15) for i in range(16)],initial_wins=sum(x['status']=='WIN' for x in a),endpoint_wins=sum(x['status']=='WIN' for x in b),initial_losses=sum(x['status']=='LOSS' for x in a),endpoint_losses=sum(x['status']=='LOSS' for x in b)))
response=[]
for env in ['unit','random']:
 for H in [12,24]:
  cs=[c for c in cells if c['opponent']==env];vs=[cache[(c['route'],tuple(c['names']),env,H)] for c in cs];terminaldiscriminatory=sum(len({v[i]['terminal'] for v in vs})>1 for i in range(N));mixeddiscriminatory=sum(len({v[i]['mixed'] for v in vs})>1 for i in range(N));response.append(dict(opponent=env,H=H,models=len(cs),terminal_discriminatory_rows=terminaldiscriminatory,mixed_discriminatory_rows=mixeddiscriminatory,go=sum(x['go'] for v in vs for x in v),plies=sum(x['plies'] for v in vs for x in v),wins=sum(x['status']=='WIN' for v in vs for x in v),losses=sum(x['status']=='LOSS' for v in vs for x in v)))
for x in descriptors:x.setdefault('route','pure24')
out=dict(status='PASS_ALL_ROUTES',source_prior_descriptors=descriptors,resources=resources,pure_resources=pure['resources'],components=components,metrics=metrics,feedback_cost_response=response,pure_physical_seconds=old['seconds'],mixed_physical_seconds=new['seconds'],new_go=0,seconds=time.perf_counter()-start,scope=plan['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(descriptors=descriptors,resources=resources,feedback_cost=response,mixed_physical_seconds=new['seconds'])))
