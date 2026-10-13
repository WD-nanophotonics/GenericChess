import json,time,itertools,math,statistics
from fractions import Fraction
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task578';D=R/'results/dev_aux/task574/declaration.json';d=json.loads(D.read_bytes());r=json.loads((R/'results/dev_aux/task576/result.json').read_bytes());assert json.loads((R/'results/dev_aux/task577/result.json').read_bytes())['status']=='PASS';start=time.perf_counter();plan=dict(question='Do ALLlearnedendpoints keep gains undercommonpopulationopponents?',metrics=['mixed','terminal','fast'],common_opponents='For eachendpoint/itsinitial omitBOTHfrom10; compare SAMEremaining8opponents/10families/bothcolors; no mismatchedselfopponentaverages.',families='Independentrootseed cluster, averagebothcolors/opponents first; ALLleaveone, no cherry-pickedroot orfit.',scope='Postfrozen finitepopulation diagnosis; all9opponentoverallscore isdescriptive, common8 contrasts forfairpairedendpoint comparison. No Elo/learnedprices/globalvalue/source-fitness inference.',frozen_before_derivation=time.time());(O/'declaration.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');mat={m:{} for m in plan['metrics']};cell={m:{} for m in plan['metrics']};outcomes={i:dict(wins=0,losses=0,rule_draw=0,unfinished=0) for i in range(10)}
for x in r['rows']:
 i=x['candidate_profile'];j=x['opponent_profile'];winner=x['termination']['winner'];kind=x['termination']['kind'];sign=0 if winner is None else 1 if winner==x['color'] else -1;t=Fraction(32*sign);mixed=Fraction(x['goal']);assert mixed==t+(Fraction(x['quantity'],19) if kind=='cap24' else 0);fast=t+(Fraction(sign*(24-x['plies']),24) if sign else 0)
 for m,val in [('mixed',mixed),('terminal',t),('fast',fast)]:cell[m][(i,j,x['root_index'],x['color'])]=val;cell[m][(j,i,x['root_index'],1-x['color'])]=-val
 for p,s in [(i,sign),(j,-sign)]:outcomes[p]['wins' if s==1 else 'losses' if s==-1 else 'unfinished' if kind=='cap24' else 'rule_draw']+=1
matrix=[];overall=[];nr=len(d['roots'])
for m in plan['metrics']:
 for i in range(10):
  opponent_means=[];family=[]
  for j in range(10):
   if i==j:continue
   v=[cell[m][(i,j,k,c)] for k in range(nr) for c in [0,1]];mu=sum(v)/len(v);mat[m][i,j]=mu;opponent_means.append(mu);matrix.append(dict(metric=m,profile=i,opponent=j,mean=str(mu),root_family_means=[str(sum(v[2*k:2*k+2])/2) for k in range(nr)]))
  for k in range(nr):family.append(sum(cell[m][i,j,k,c] for j in range(10) if j!=i for c in [0,1])/18)
  overall.append(dict(metric=m,profile=i,names=d['profiles'][i]['names'],mean=str(sum(opponent_means)/9),root_family_means=list(map(str,family)),leave_one_means=[str(sum(v for k,v in enumerate(family) if k!=f)/(nr-1)) for f in range(nr)],outcomes=outcomes[i]))
 assert sum(Fraction(x['mean']) for x in overall if x['metric']==m)==0
contrasts=[]
for p,profile in enumerate(d['profiles']):
 for name in profile['names']:
  if not name.endswith('-endpoint'):continue
  basename=name[:-len('-endpoint')]+'-initial';base=next(i for i,x in enumerate(d['profiles']) if basename in x['names']);opps=[i for i in range(10) if i not in [p,base]];assert len(opps)==8
  for m in plan['metrics']:
   fam=[]
   for k in range(nr):fam.append(sum(cell[m][p,j,k,c]-cell[m][base,j,k,c] for j in opps for c in [0,1])/16)
   contrasts.append(dict(model=name,endpoint_profile=p,initial_profile=base,common_opponents=opps,metric=m,gain=str(sum(fam)/nr),family_gains=list(map(str,fam)),leave_one_gains=[str(sum(v for k,v in enumerate(fam) if k!=f)/(nr-1)) for f in range(nr)],family_positive=sum(v>0 for v in fam),family_negative=sum(v<0 for v in fam)))
# Allclosedmodels source distance isdescriptive AFTERpayoffmatrices derived; never reward/opponent/modelselection.
old=json.loads((R/'results/dev_aux/task570/result.json').read_bytes());ref=json.loads((R/'results/dev_aux/task560/result.json').read_bytes())['source_prior'];axes=list(range(2,8))+list(range(9,15));descriptors=[dict(profile=i,names=p['names'],log_ratio_MSE_to_source=statistics.mean(math.log(p['weights'][a]/ref[a])**2 for a in axes)) for i,p in enumerate(d['profiles'])]
out=dict(status='PASS_ALL_PAYOFFS',logical_games=900,actual_main_games=r['actual_games'],actual_main_go=r['actual_go'],overall=overall,all_pair_matrix=matrix,matched_endpoint_contrasts=contrasts,source_descriptors=descriptors,new_go=0,seconds=time.perf_counter()-start,scope=plan['scope']+' Sourcepriornotindependenthumanconsensus; rootpopulationfreshbutmodel selection/trainingalreadyexposedpriorstudies; no automaticpipelineadoption. Bothendpoints omitted fromcommonopponentdistribution bypredeclaredfaircomparison.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(overall_terminal=[x for x in overall if x['metric']=='terminal'],contrasts_terminal=[x for x in contrasts if x['metric']=='terminal'],contrasts_mixed=[x for x in contrasts if x['metric']=='mixed'])))
