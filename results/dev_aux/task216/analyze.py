import json,math,statistics,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task216';P=R/'results/dev_aux/task214';C=json.loads((P/'controller.json').read_bytes());D=json.loads((P/'declaration.json').read_bytes());assert C['complete'];by={(c['context']['seed'],c['context']['mode'],c['context']['opponent'],c['context']['root_index'],c['context']['agent_color']):c for c in C['calls'] if c['context']['phase']=='heldout'}
def reference(w):return statistics.mean(abs(math.log(w[k]/208/D['human_reference'][k])) for k in 'NBRQ')
def metrics(rows):
 groups={k:0 for k in ('win','loss','draw','cutoff_unknown')};vals=[]
 for c in rows:
  r=c['result'];s=r['score'];col=r['agent_color'];kind='cutoff_unknown' if not s['terminal'] else 'draw' if s['winner'] is None else 'win' if s['winner']==col else 'loss';groups[kind]+=1;vals.append((0 if s['winner'] is None else (1 if s['winner']==col else -1)) if s['terminal'] else s['quantity_difference']/15)
 return dict(categories=groups,original=statistics.mean(c['result']['reward'] for c in rows),bounded=statistics.mean(vals),quantity=statistics.mean(c['result']['score']['quantity_difference']/15 for c in rows))
results=[];curves=[]
for run in C['runs']:
 seed=run['seed'];mode=run['mode'];held={};pairs=[]
 for opponent in D['opponents_heldout']:
  a=[by[(seed,'shared_initial',opponent,oi,col)] for oi in range(8) for col in (True,False)];b=[by[(seed,mode,opponent,oi,col)] for oi in range(8) for col in (True,False)];ma=metrics(a);mb=metrics(b);held[opponent]=dict(initial=ma,final=mb,paired_delta={k:mb[k]-ma[k] for k in ('original','bounded','quantity')},changed_trajectories=sum(x['result']['actions']!=y['result']['actions'] for x,y in zip(a,b)))
  for oi in range(8):
   for col in (True,False):
    x=by[(seed,'shared_initial',opponent,oi,col)];y=by[(seed,mode,opponent,oi,col)];pairs.append(dict(opponent=opponent,root=oi,color=col,original_delta=y['result']['reward']-x['result']['reward'],terminal=[x['result']['score']['termination'],y['result']['score']['termination']]))
 targets=[r for z in run['rounds'] for r in z['all_transitions']];updates=[u for z in run['rounds'] for u in z['updates']];m=dict(seed=seed,mode=mode,initial_weights=run['initial_weights'],final_weights=run['final_weights'],final_Pnormalized={k:run['final_weights'][k]/208 for k in 'NBRQ'},initial_distance=reference(run['initial_weights']),final_distance=reference(run['final_weights']),log_parameter_change=math.sqrt(sum((a-b)**2 for a,b in zip(run['initial_theta'],run['final_theta']))),actual_updates=len(updates),gradient_nonzero_updates=sum(sum(g*g for g in u['gradient'])>1e-20 for u in updates),targets=dict(actual_terminal=sum(r['target_kind']=='true_terminal' for r in targets),bootstrap=sum(r['target_kind']=='search_bootstrap' for r in targets),forecastmate=sum(bool(r['successor_value'] and r['successor_value']['kind']=='mate') for r in targets),excluded=sum(len(z['excluded']) for z in run['rounds'])),heldout=held,pairs=pairs)
 results.append(m)
 for z in run['rounds']:
  curves.append(dict(seed=seed,mode=mode,round=z['round'],teacher_weights=z['teacher_weights'],student_ratios={k:math.exp(v) for k,v in zip('NBRQ',z['student_after'])},updates=len(z['updates']),sum_individual_loss_reduction=sum(u['loss_before']-u['loss_after'] for u in z['updates']),scope='Individuallosses aredifferentsample/currentweights; sums notsingleheldoutobjective/learningstrength.'))
out=dict(complete=True,results=results,curves=curves,source_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest(),shared_initial='96actualbaselinegames reusedlogically forall9modes, notindependent replicas.',scope='All9freshstart/mode outcomes and8rootclusterheldouts. Humanreference descriptiveonly; targetteacher dependsnonhumaninitialprices andfixedmatureheuristics. Approximatebootstrap notintrinsiccausalprices/exactminimax/TDLeaf/convergenceproof.')
(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(seed=r['seed'],mode=r['mode'],prices=r['final_Pnormalized'],distances=[r['initial_distance'],r['final_distance']],logchange=r['log_parameter_change'],updates=r['actual_updates'],delta={o:r['heldout'][o]['paired_delta'] for o in D['opponents_heldout']}) for r in results],indent=2))
