import json,math,time,hashlib
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task424';O.mkdir(exist_ok=True);prior=json.loads((R/'results/dev_aux/task378/result.json').read_text(encoding='utf-8'))['source_prior_reference'];ref=prior['prices'];axes=[2,3,4,5,6,7,9,10,11,12,13,14];human=[];acceptance=[];training=[];t0=time.perf_counter()
for task in (406,418,419):
 e=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_text(encoding='utf-8'));r=json.loads((R/f'results/dev_aux/task{task}/result.json').read_text(encoding='utf-8'));arm='unitcomparison' if task==406 else r['arm']
 for ep in e['endpoints']:
  metric=lambda w:sum(math.log(w[a]/ref[a])**2 for a in axes)/12
  human.append(dict(task=task,arm=arm,method=ep['method'],family=ep['family'],initial=ep['initial'],endpoint=ep['endpoint'],initial_log_MSE=metric(ep['initial']),endpoint_log_MSE=metric(ep['endpoint']),delta_log_MSE=metric(ep['endpoint'])-metric(ep['initial']),changed_axes=sum(ep['initial'][a]!=ep['endpoint'][a] for a in axes)))
 for u in e['updates']:
  cs=u['candidates'];best=u['selected_index'];base=cs[0];chosen=cs[best];pairs=[Fraction(a)-Fraction(b) for a,b in zip(chosen['goals'],base['goals'])];families=[sum(pairs[i:i+2])/2 for i in range(0,8,2)];loo=[sum(x for j,x in enumerate(families) if i!=j)/3 for i in range(4)]
  # Goal decomposition is exact: rule result +/-32 versus unfinished quantity/19.
  def parts(row):
   rawgames=[json.loads((R/x['file']).read_text(encoding='utf-8').splitlines()[x['line']-1]) for x in row['sources']]
   term=[Fraction(g['goal']) if g['termination']['kind']!='cap24' else Fraction(0) for g in rawgames];qty=[Fraction(g['goal']) if g['termination']['kind']=='cap24' else Fraction(0) for g in rawgames];return sum(term)/8,sum(qty)/8
  if best:
   bt,bq=parts(base);ct,cq=parts(chosen);assert ct-bt+cq-bq==Fraction(u['accepted_strict_gain'])
   acceptance.append(dict(task=task,arm=arm,family=u['family'],iteration=u['iteration'],accepted_gain=u['accepted_strict_gain'],rule_component_delta=str(ct-bt),unfinished_quantity_component_delta=str(cq-bq),root_family_gains=[str(x) for x in families],leave_one_rootfamily_gain=[str(x) for x in loo],changed_axes=u['changed_integer_axes']))
 for ep in e['endpoints']:
  label=ep['method']+'-'+ep['family'];a=next(x for x in r['diagnostics'] if x['phase']=='train_endpoint_diagnostic' and label+'-initial' in x['names']);b=next(x for x in r['diagnostics'] if x['phase']=='train_endpoint_diagnostic' and label+'-endpoint' in x['names']);training.append(dict(task=task,arm=arm,method=ep['method'],family=ep['family'],initial=a['mean_goal'],endpoint=b['mean_goal'],gain=str(Fraction(b['mean_goal'])-Fraction(a['mean_goal'])),initial_wins=a['true_wins'],endpoint_wins=b['true_wins'],initial_losses=a['true_losses'],endpoint_losses=b['true_losses']))
cross=json.loads((R/'results/dev_aux/task425/result.json').read_text(encoding='utf-8'));transfer=[]
for trainarm in ['unit','random']:
 for family in ['unit','random2514']:
  for env in ['unit','random']:
   label=trainarm+'-trained-'+family
   a=sorted([x for x in cross['rows'] if x['arm']==env and label+'-initial' in x['names']],key=lambda x:(x['root_index'],x['color']));b=sorted([x for x in cross['rows'] if x['arm']==env and label+'-endpoint' in x['names']],key=lambda x:(x['root_index'],x['color']));assert len(a)==len(b)==8;pairs=[Fraction(y['goal'])-Fraction(x['goal']) for x,y in zip(a,b)];fm=[sum(pairs[i:i+2])/2 for i in range(0,8,2)]
   transfer.append(dict(train_opponent=trainarm,start=family,development_opponent=env,initial_mean=str(sum(Fraction(x['goal']) for x in a)/8),endpoint_mean=str(sum(Fraction(x['goal']) for x in b)/8),gain=str(sum(pairs)/8),paired_cell_gains=[str(x) for x in pairs],root_family_gains=[str(x) for x in fm],leave_one_family_gain=[str(sum(x for j,x in enumerate(fm) if j!=i)/3) for i in range(4)],initial_wins=sum(x['termination']['winner']==x['color'] for x in a),endpoint_wins=sum(x['termination']['winner']==x['color'] for x in b),initial_losses=sum(x['termination']['winner'] is not None and x['termination']['winner']!=x['color'] for x in a),endpoint_losses=sum(x['termination']['winner'] is not None and x['termination']['winner']!=x['color'] for x in b)))
out=dict(training=training,cross_environment_transfer=transfer,accepted_gain_decomposition=acceptance,source_prior_descriptors=human,source_reference=prior,source_scope='ALL8 frozenendpoints POSTfreeze only; officialsourceApery(WCSC26)prior NOT independenthumanconsensus/holdout, never used forobjective/proposals/directions/horizon/stop/selector',scope='allfrozenresults and4rootfamily diagnostics, no samplingCI oroptimalselector; actualdisplacement notquantization swallowing. Cross declaration425 precededANYdev; trainopponent anddeploymentopponent keptseparate',seconds=time.perf_counter()-t0,new_go=0);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(training=training,transfer=transfer,source_descriptors=human),indent=2))
