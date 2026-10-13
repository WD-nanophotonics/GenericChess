import json,sys,time,hashlib,collections
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task542';O.mkdir(exist_ok=True);tasks=list(map(int,sys.argv[1:]));assert tasks;outputs=[]
for task in tasks:
 dest=O/f'result_{task}.json';assert not dest.exists();f=R/f'results/dev_aux/task{task}/games.jsonl';epfile=f.parent/'endpoints.json';ep=json.loads(epfile.read_bytes());assert ep['frozen_before_development'];metadata=[];t0=time.perf_counter()
 for line in f.open(encoding='utf-8'):
  g=json.loads(line);term=g['termination'];true=0 if term['winner'] is None else 32 if term['winner']==g['color'] else -32;outcome='UNFINISHED' if term['kind']=='cap24' else 'DRAW' if term['winner'] is None else 'WIN' if true>0 else 'LOSS';signature=dict(root=g['root'],actions=[(a['actor'],a['move'],a['after_sfen'].split()[:3]) for a in g['actions']],final=g['final_sfen'].split()[:3],termination=term)
  metadata.append(dict(root=g['root']['seed'],color=g['color'],weights=g['weights'],terminal=true,true_outcome=outcome,quantity=g['raw_quantity'] if outcome=='UNFINISHED' else None,path_sha256=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()))
 rows=[]
 for u in ep['updates']:
  candidates=[]
  for row in u['candidates']:
   cells=[metadata[x['line']-1] for x in row['sources']];assert all(x['file']==f.relative_to(R).as_posix() for x in row['sources']);assert sum(Fraction(g['terminal']) for g in cells)/len(cells)==Fraction(row['mean_goal']);candidates.append(cells)
  assert all([(g['root'],g['color']) for g in candidates[0]]==[(g['root'],g['color']) for g in col] for col in candidates)
  means=[sum(Fraction(g['terminal']) for g in col)/len(col) for col in candidates];base=candidates[0];comparisons=[]
  for ci,col in enumerate(candidates[1:],1):
   changed=[i for i,(a,b) in enumerate(zip(base,col)) if a['path_sha256']!=b['path_sha256']];terminal_changed=[i for i,(a,b) in enumerate(zip(base,col)) if a['terminal']!=b['terminal']];outcomes_changed=[i for i,(a,b) in enumerate(zip(base,col)) if a['true_outcome']!=b['true_outcome']]
   comparisons.append(dict(candidate_index=ci,changed_trajectory_cells=changed,changed_terminal_score_cells=terminal_changed,changed_true_outcome_category_cells=outcomes_changed,mean_terminal_delta=str(means[ci]-means[0]),terminal_tied_despite_paths=bool(changed) and means[ci]==means[0],mean_cancellation_despite_terminal_cell_change=bool(terminal_changed) and means[ci]==means[0]))
  best=max(range(3),key=lambda i:means[i]);assert best==u['selected_index'];rows.append(dict(family=u['family'],iteration=u['iteration'],candidate_means=list(map(str,means)),all_three_mean_tied=len(set(means))==1,actual_selected=u['selected_index'],comparisons=comparisons,scope='Actualobservedbase/plus/minus only, no fullneighborhood/globalflatness/counterfactualfuturetraining chain'))
 summaries=[]
 for family in sorted({u['family'] for u in rows}):
  rs=[u for u in rows if u['family']==family];cs=[c for u in rs for c in u['comparisons']];summaries.append(dict(family=family,rounds=len(rs),all_three_mean_tied_rounds=sum(u['all_three_mean_tied'] for u in rs),accepted=sum(u['actual_selected']!=0 for u in rs),trajectory_changes_with_mean_tie=sum(c['terminal_tied_despite_paths'] for c in cs),aggregate_cancellation_pairs=sum(c['mean_cancellation_despite_terminal_cell_change'] for c in cs),terminal_changed_pairs=sum(bool(c['changed_terminal_score_cells']) for c in cs)))
 out=dict(status='PASS_ACTUAL_LOCAL_RESPONSE',task=task,arm=ep['arm'],source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),actual_games=len(metadata),actual_rounds=len(rows),summaries=summaries,rows=rows,new_go=0,seconds=time.perf_counter()-t0,scope='Phaseclosedtraining actualcandidate responses, allroot/colorcells; true terminalcategories separateDRAW/UNFINISHED. Mean ties may hide changedfeedback; discreteobservedprices/selecteddirections not parameteridentificationor globallyflatfitness. No reference/validation/modelchoice beforeallproducerfreeze.')
 dest.write_text(json.dumps(out,indent=2),encoding='utf-8');outputs.append({k:v for k,v in out.items() if k!='rows'})
print(json.dumps(outputs))
