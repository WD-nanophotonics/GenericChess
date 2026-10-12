"""Full saved-candidate component and root-cluster control."""
import json,hashlib,statistics
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task190';P=R/'results/dev_aux/task187';C=json.loads((P/'controller.json').read_bytes());D=json.loads((P/'declaration.json').read_bytes());assert C['completed'];by={c['context']['name']:c for c in C['calls']}
def pieces(c):
 s=c['result']['score'];col=c['context']['agent_color'];wdl=(0 if s['winner'] is None else (1 if s['winner']==col else -1)) if s['terminal'] else 0
 cutoff=0 if s['terminal'] else s['quantity_difference']*16;qty=s['quantity_difference']*16;speed=15*(16-s['played_plies'])*wdl
 return dict(actual=round(c['result']['reward']*240),original=wdl*24000+speed+cutoff,bounded=wdl*240+cutoff,wdl=wdl,cutoff=cutoff,quantity=qty,speed=speed)
def best(v):return [i for i,x in enumerate(v) if x==max(v)]
def aggregate(cells):
 sums={k:[sum(pieces(c)[k] for c in g) for g in cells] for k in ('actual','original','bounded','wdl','cutoff','quantity','speed')}
 sums['wdl_then_cutoff_quantity']=list(zip(sums['wdl'],sums['cutoff']));return sums
rows=[]
for run in C['runs']:
 for index,u in enumerate(run['updates']):
  groups=[[by[f"s{run['seed']}-{run['opponent']}-train-g{index//4}-k{index%4}-a{arm}-o{oi}-c{int(col)}"] for oi in range(8) for col in (True,False)] for arm in range(3)]
  a=aggregate(groups);assert a['actual']==u['integer_sums_240'];actual=u['selected'];sets={k:best(v) for k,v in a.items()};assert actual in sets['actual']
  assert all(abs(pieces(c)['original']/240-c['result']['original_reward'])<1e-10 and abs(pieces(c)['bounded']/240-c['result']['bounded_reward'])<1e-10 for g in groups for c in g)
  for i,j in ((0,1),(0,2),(1,2)):
   if a['wdl'][i]!=a['wdl'][j]:assert (a['original'][i]>a['original'][j])==(a['wdl'][i]>a['wdl'][j])
  gains=[sum(pieces(c)['actual'] for c in groups[actual][oi*2:oi*2+2])-sum(pieces(c)['actual'] for c in groups[0][oi*2:oi*2+2]) for oi in range(8)];positive=sum(max(0,g) for g in gains);deleted=[]
  for oi in range(8):
   z=aggregate([g[:oi*2]+g[oi*2+2:] for g in groups]);deleted.append(dict(root=oi,sums=z,best={k:best(v) for k,v in z.items()}))
  rows.append(dict(seed=run['seed'],objective=run['opponent'],sweep=index//4,coordinate=u['coordinate'],selected=actual,sums=a,best=sets,selected_wdl_shortfall=max(a['wdl'])-a['wdl'][actual],actual_disjoint_lexicographic=set(sets['actual']).isdisjoint(sets['wdl_then_cutoff_quantity']),per_root_gain_240=gains,largest_positive_share=max(gains)/positive if positive else 0,root_deleted=deleted))
summ=[]
for objective in D['opponents']:
 rs=[r for r in rows if r['objective']==objective];non=[r for r in rs if r['selected']!=0]
 summ.append(dict(objective=objective,choices=len(rs),selected_wdl_sacrifices=sum(r['selected_wdl_shortfall']>0 for r in rs),actual_lex_sets_disjoint=sum(r['actual_disjoint_lexicographic'] for r in rs),nonincumbent=len(non),largest_root90pct=sum(r['largest_positive_share']>=.9 for r in non),any_root_removal_loses_selected=sum(any(r['selected'] not in z['best']['actual'] for z in r['root_deleted']) for r in rs)))
out=dict(complete=True,source_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest(),summaries=summ,rows=rows,scope='Allsamecandidategoalcontrols androotdeletions; notnewtrajectory, causalproof,statisticalCI orindependentselection.90pct descriptive only.')
(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(summ,indent=2))
