import json,collections,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task799';O.mkdir(exist_ok=True);rows=[]
for task,method in [(787,'D'),(791,'E')]:
 p=R/f'results/dev_aux/task{task}/endpoints.json'
 if not p.exists():continue
 ep=json.loads(p.read_bytes())
 for start in ['unit','random2514']:
  us=[u for u in ep['updates'] if u['start']==start];assert len(us)==12;steps=[]
  for u in us:
   triples=[]
   for c in u['candidates']:
    ts=c['terminations'];loss=sum(not t['kind'].startswith('cap') and t['winner'] is not None and t['winner']!=i%2 for i,t in enumerate(ts));win=sum(not t['kind'].startswith('cap') and t['winner']==i%2 for i,t in enumerate(ts));triples.append((-loss,win,F(c['mean_goal'])))
   j=u['selected_index'];base=triples[0];chosen=triples[j];first=next((i for i in range(3) if chosen[i]!=base[i]),None);steps.append(dict(axis=u['axis'],accepted=j!=0,priority_component=first,initial_loss=-base[0],selected_loss=-chosen[0],initial_win=base[1],selected_win=chosen[1],literal_gain=str(chosen[2]-base[2]),all_candidate_triples=[[-z[0],z[1],str(z[2])] for z in triples],scalar_best_index=max(range(7),key=lambda k:triples[k][2]),lex_best_index=max(range(7),key=lambda k:triples[k]),selected_index=j))
  rows.append(dict(method=method,start=start,steps=steps,accepted=sum(x['accepted'] for x in steps),loss_priority_updates=sum(x['accepted'] and x['priority_component']==0 for x in steps),win_priority_updates=sum(x['accepted'] and x['priority_component']==1 for x in steps),quantity_priority_updates=sum(x['accepted'] and x['priority_component']==2 for x in steps),accepted_literal_loss=sum(x['accepted'] and F(x['literal_gain'])<0 for x in steps),initial_loss=steps[0]['initial_loss'],final_loss=steps[-1]['selected_loss'],initial_win=steps[0]['initial_win'],final_win=steps[-1]['selected_win']))
out=dict(status='ACTUAL_TRAINING_PRIORITY_COMPONENTS',rows=rows,source_sha256={str(n):hashlib.sha256((R/f'results/dev_aux/task{n}/endpoints.json').read_bytes()).hexdigest() for n in [787,791] if (R/f'results/dev_aux/task{n}/endpoints.json').exists()},new_go=0,scope='Selected actualtrainingupdates only; componentstats/ALLvisited candidates observed, no model/value/reference orcounterfactualendpoints. Regenerate finaltable afterbothclosed, preservethis firstD-only observation.');(O/('result.json' if len(rows)==4 else 'D_only_before_E.json')).write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([{k:v for k,v in x.items() if k!='steps'} for x in rows]))
