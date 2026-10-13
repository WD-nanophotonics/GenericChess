import json,sys,time,collections
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task506';O.mkdir(exist_ok=True);tasks=[int(x) for x in sys.argv[1:]] or [496,497];t0=time.perf_counter();allrows=[];summaries=[]
for task in tasks:
 folder=R/f'results/dev_aux/task{task}';meta=[]
 for line in (folder/'games.jsonl').open(encoding='utf-8'):
  g=json.loads(line);term=g['termination'];terminal=Fraction(0) if term['winner'] is None else Fraction(32 if term['winner']==g['color'] else -32);qty=Fraction(g['raw_quantity'],19) if term['kind']=='cap24' else Fraction(0);speed=Fraction(0) if term['winner'] is None else (1 if term['winner']==g['color'] else -1)*(32+Fraction(24-len(g['actions']),24));assert terminal+qty==Fraction(g['goal'])
  meta.append(dict(weights=g['weights'],root=g['root'],color=g['color'],goal=g['goal'],terminal=str(terminal),quantity=str(qty),fast_terminal=str(speed),plies=len(g['actions']),actual_training=g.get('training_goal',g['goal']),training_objective=g.get('training_objective','mixed')))
 e=json.loads((folder/'endpoints.json').read_text(encoding='utf-8'))
 for u in e['updates']:
  candidates=[]
  for row in u['candidates']:
   gs=[meta[ref['line']-1] for ref in row['sources']];assert all(ref['file']==f'results/dev_aux/task{task}/games.jsonl' for ref in row['sources']);assert len(gs) in (6,8,32) and all(g['weights']==row['weights'] for g in gs);means={name:sum(Fraction(g[name]) for g in gs)/len(gs) for name in ['goal','terminal','quantity','fast_terminal','actual_training']};assert means['goal']==means['terminal']+means['quantity'] and means['actual_training']==Fraction(row['mean_goal']);candidates.append(dict(weights=row['weights'],means={k:str(v) for k,v in means.items()},cells=gs))
  decisions={}
  for metric in ['goal','terminal','quantity','fast_terminal','actual_training']:
   scores=[Fraction(x['means'][metric]) for x in candidates];best=max(range(3),key=lambda j:scores[j]);decisions[metric]=dict(selected_index=best,gain=str(scores[best]-scores[0]))
  assert decisions['actual_training']['selected_index']==u['selected_index'];mix=decisions['goal']['selected_index'];pure=decisions['terminal']['selected_index']
  category='both_keepbase' if mix==pure==0 else 'mixed_accepts_pure_keepsbase' if mix!=0 and pure==0 else 'same_nonbase_proposal' if mix==pure else 'different_proposal'
  allrows.append(dict(task=task,arm=e['arm'],family=u['family'],iteration=u['iteration'],actual_selected=u['selected_index'],category=category,decisions=decisions,candidates=candidates,scope='one actualround only; DO NOTchain counterfactual decisions orclaim anunexecutedtraining path'))
 for family in {u['family'] for u in e['updates']}:
  rows=[r for r in allrows if r['task']==task and r['family']==family];summaries.append(dict(task=task,arm=e['arm'],family=family,categories=dict(collections.Counter(r['category'] for r in rows)),actual_accepted=sum(r['actual_selected']!=0 for r in rows),mixed_pure_local_choices_differ=sum(r['decisions']['goal']['selected_index']!=r['decisions']['terminal']['selected_index'] for r in rows),pure_fast_local_choices_differ=sum(r['decisions']['terminal']['selected_index']!=r['decisions']['fast_terminal']['selected_index'] for r in rows)))
out=dict(status='PASS_DERIVATION',tasks=tasks,actual_rounds=len(allrows),summaries=sorted(summaries,key=lambda r:(r['task'],r['family'])),rows=allrows,new_go=0,seconds=time.perf_counter()-t0,scope='ALLactualbase/plus/minus candidate scorecomponents/exactstrictgain/basefirsttie localreplay, perroot/color tuples. Quant dependency notproofharm; nonquantity supportsnotprice recovery. Changedlocalcounterfactual choice cannotdefine laterunexecutedcandidates. Budgets/objectives on differentcohorts notunique mechanism attribution.');(O/('result_'+('_'.join(map(str,tasks)))+'.json')).write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k!='rows'})
