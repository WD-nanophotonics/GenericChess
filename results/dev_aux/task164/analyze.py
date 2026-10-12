"""Reportedsearch utility-type coverage; noall-defense orleaf-activationclaim."""
import json,collections
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task164';O.mkdir(exist_ok=True);sources=[]
for task in (152,160):
 C=json.loads((R/f'results/dev_aux/task{task}/controller.json').read_bytes());assert C['completed'];groups={}
 for c in C['calls']:
  if c['result'] is None:continue
  x=c['context'];method=x['alignment'] if task==152 else x['opponent'];key=(x['start_seed'],str(method),x['phase'])
  if key not in groups:groups[key]=dict(games=0,mate_wins=0,mate_losses=0,cutoffs=0,agent_searches=0,reported_mate=0,reported_cp=0,unparsed=0)
  g=groups[key];r=c['result'];s=r['score'];g['games']+=1;g['mate_wins']+=s['termination']=='CHECKMATE' and s['winner']==x['agent_color'];g['mate_losses']+=s['termination']=='CHECKMATE' and s['winner']!=x['agent_color'];g['cutoffs']+=not s['terminal']
  for m in r['search_records']:
   g['agent_searches']+=1;scorelines=[line.split() for line in m['uci_info'] if line.startswith('info ') and 'score' in line.split()]
   if not scorelines:g['unparsed']+=1;continue
   f=scorelines[-1];kind=f[f.index('score')+1]
   if kind=='mate':g['reported_mate']+=1
   elif kind=='cp':g['reported_cp']+=1
   else:g['unparsed']+=1
 rows=[dict(seed=k[0],method=k[1],phase=k[2],**g,reported_mate_fraction=g['reported_mate']/g['agent_searches']) for k,g in groups.items()]
 aggregate={k:sum(g[k] for g in groups.values()) for k in ('games','mate_wins','mate_losses','cutoffs','agent_searches','reported_mate','reported_cp','unparsed')}
 aggregate['reported_mate_fraction']=aggregate['reported_mate']/aggregate['agent_searches'];sources.append(dict(task=task,aggregate=aggregate,rows=rows))
out=dict(complete=True,sources=sources,scope='LastUCIreportedscore type, notcertifiedmate/all-defense, andnotcountofleafevaluationcalls. Searchcanusematerialpruning/ordering evenwhen reportingmate. Descriptivecoverage caninformchoiceofpricediscriminatingdistribution, notcausalfailure attribution.')
(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(task=s['task'],**s['aggregate']) for s in sources],indent=2))
