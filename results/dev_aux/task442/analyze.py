import json,sys,time,hashlib
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task442';O.mkdir(exist_ok=True);r=json.loads((R/'results/dev_aux/task441/result.json').read_text(encoding='utf-8'));cache={};metrics=[];trace_equal=True;semantic_equal=True
def source(row):
 ref=row['source'];path=ref['file']
 if path not in cache:cache[path]=[json.loads(x) for x in (R/path).open(encoding='utf-8')]
 return cache[path][ref['line']-1]
for arm,task in [('mixed',439),('terminal_only',440)]:
 e=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_text(encoding='utf-8'))
 for p in e['endpoints']:
  for env in ('unit','random'):
   prefix=arm+'-trained-'+p['family'];a=sorted([x for x in r['rows'] if x['opponent']==env and prefix+'-initial' in x['names']],key=lambda x:(x['root_index'],x['color']));b=sorted([x for x in r['rows'] if x['opponent']==env and prefix+'-endpoint' in x['names']],key=lambda x:(x['root_index'],x['color']));assert len(a)==len(b)==8
   for goal in ('mixed','terminal_only','fast_terminal'):
    def value(row):
     g=source(row);t=g['termination'];pure=Fraction(0) if t['winner'] is None else Fraction(32 if t['winner']==g['color'] else -32);qty=Fraction(g['raw_quantity'],19) if t['kind']=='cap24' else Fraction(0);assert pure+qty==Fraction(g['goal'])
     return pure+qty if goal=='mixed' else pure if goal=='terminal_only' else Fraction(0) if t['winner'] is None else (1 if t['winner']==g['color'] else -1)*(32+Fraction(24-len(g['actions']),24))
    aa=list(map(value,a));bb=list(map(value,b));dif=[y-x for x,y in zip(aa,bb)];fam=[sum(dif[i:i+2])/2 for i in range(0,8,2)]
    metrics.append(dict(train_objective=arm,family=p['family'],opponent=env,evaluation_goal=goal,initial_mean=str(sum(aa)/8),endpoint_mean=str(sum(bb)/8),gain=str(sum(dif)/8),paired_deltas=list(map(str,dif)),root_family_deltas=list(map(str,fam)),leave_one_family_deltas=[str(sum(x for j,x in enumerate(fam) if j!=i)/3) for i in range(4)],initial_true_wins=sum(x['termination']['winner']==x['color'] for x in a),endpoint_true_wins=sum(x['termination']['winner']==x['color'] for x in b)))
a=json.loads((R/'results/dev_aux/task439/endpoints.json').read_text(encoding='utf-8'));b=json.loads((R/'results/dev_aux/task440/endpoints.json').read_text(encoding='utf-8'))
for x,y in zip(a['updates'],b['updates']):
 assert (x['family'],x['iteration'])==(y['family'],y['iteration']);trace_equal &= x['start_weights']==y['start_weights'] and x['after_weights']==y['after_weights'] and x['selected_index']==y['selected_index'] and [v['weights'] for v in x['candidates']]==[v['weights'] for v in y['candidates']]
import re
norm=lambda q:[' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in q['lines']]
ga=(R/'results/dev_aux/task439/games.jsonl').open(encoding='utf-8');gb=(R/'results/dev_aux/task440/games.jsonl').open(encoding='utf-8');count=0
from itertools import zip_longest
for la,lb in zip_longest(ga,gb):
 assert la is not None and lb is not None;g=json.loads(la);h=json.loads(lb);count+=1
 for key in ['weights','root','color','actions','termination','final_sfen','raw_quantity','goal']:semantic_equal &= g[key]==h[key]
 assert len(g['queries'])==len(h['queries'])
 for x,y in zip(g['queries'],h['queries']):
  semantic_equal &= all(x[k]==y[k] for k in ['initial_sfen','history','weights','nodes_limit','cold_isready','state','command','bestmove','player','ply']) and norm(x)==norm(y)
out=dict(status='PASS_DERIVATION',all_actual_parameter_paths_equal=trace_equal,all_actual_game_response_except_timeNPS_equal=semantic_equal,paired_physical_fitgames=count,metrics=metrics,new_go=0,scope='Actualmixed-vs-pureterminal interventions on samecohort/optimizer; everyround/end/played/query semantic trajectorycompared, excludeonlytimingNPS. Thisfiniteequality doesnotprove quantity harmless inothercontexts; ALLoriginal/speed/terminal metrics reported, nobestgoalselector.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k!='metrics'})
