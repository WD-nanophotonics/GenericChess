"""Frozen candidate component diagnostic; no new games or alternative trajectory."""
import json,statistics,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task174';O.mkdir(exist_ok=True)
def select(v):return max(range(3),key=lambda k:v[k]) if max(v)>v[0] else 0
def values(c):
 sc=c['result']['score'];color=c['context']['agent_color'];winner=sc['winner']
 sign=0 if winner is None else (1 if winner==color else -1)
 terminal=F(100*sign) if sc['terminal'] else F(0);speed=F(sign*(16-sc['played_plies']),16) if sc['terminal'] else F(0);quantity=F(sc['quantity_difference'],15);cutoff=F(0) if sc['terminal'] else quantity
 return dict(original=terminal+speed+cutoff,without_terminal=speed+cutoff,bounded=F(sign) if sc['terminal'] else quantity,final_quantity=quantity,terminal_only=terminal+speed,cutoff_only=cutoff,terminal=terminal,speed=speed)
def execute():
 if (O/'analysis.json').exists():raise FileExistsError('frozen')
 P=R/'results/dev_aux/task169';C=json.loads((P/'controller.json').read_bytes());D=json.loads((P/'declaration.json').read_bytes());assert C['completed'];by={c['context']['name']:c for c in C['calls']};rows=[];plateaus=0;methods={}
 for run in C['runs']:
  seed=run['seed'];opp=run['opponent']
  for index,u in enumerate(run['updates']):
   sweep=index//4;k=index%4;groups=[[by[f's{seed}-{opp}-train-g{sweep}-k{k}-a{a}-o{oi}-c{int(color)}'] for oi in range(len(D['train_roots'])) for color in (True,False)] for a in range(3)]
   totals={metric:[sum((values(c)[metric] for c in group),F(0)) for group in groups] for metric in ('original','bounded','final_quantity','terminal_only','cutoff_only','terminal','speed','without_terminal')}
   chosen={metric:select(t) for metric,t in totals.items()};assert chosen['original']==u['selected']
   row=dict(seed=seed,opponent=opp,sweep=sweep,coordinate=u['coordinate'],actual_selected=u['selected'],selected_by_component=chosen,total_fractions={k:list(map(str,v)) for k,v in totals.items()},same_original_mean_allarms=len(set(totals['original']))==1,same_final_quantity_mean_allarms=len(set(totals['final_quantity']))==1)
   best=lambda t:[i for i,v in enumerate(t) if v==max(t)]
   row['optimal_sets']={metric:best(t) for metric,t in totals.items()}
   row['original_without_terminal_sets_intersect']=bool(set(row['optimal_sets']['original'])&set(row['optimal_sets']['without_terminal']))
   row['original_cutoff_only_sets_intersect']=bool(set(row['optimal_sets']['original'])&set(row['optimal_sets']['cutoff_only']))
   clusters=[]
   for oi in range(len(D['train_roots'])):
    cluster_totals={metric:[sum((values(c)[metric] for c in group[2*oi:2*oi+2]),F(0)) for group in groups] for metric in totals}
    clusters.append(dict(root=oi,delta_from_incumbent={metric:[str(v-vv[0]) for v in vv] for metric,vv in cluster_totals.items()},removed_root_original_best=best([t-c for t,c in zip(totals['original'],cluster_totals['original'])]),removed_root_cutoff_best=best([t-c for t,c in zip(totals['cutoff_only'],cluster_totals['cutoff_only'])])))
   row['per_root_clusters']=clusters
   gain=[F(c['delta_from_incumbent']['original'][u['selected']]) for c in clusters]
   positive=[v for v in gain if v>0]
   row['selected_original_advantage']=str(totals['original'][u['selected']]-totals['original'][0])
   row['positive_advantage_root_count']=len(positive)
   row['largest_positive_root_share']=float(max(positive)/sum(positive,F(0))) if positive else None
   row['selected_advantage_from_single_positive_root']=len(positive)==1
   rows.append(row)
 for opp in D['opponents']:
  group=[r for r in rows if r['opponent']==opp];methods[opp]=dict(updates=len(group),bounded_changed=sum(r['selected_by_component']['bounded']!=r['actual_selected'] for r in group),finalquantity_changed=sum(r['selected_by_component']['final_quantity']!=r['actual_selected'] for r in group),cutoffonly_changed=sum(r['selected_by_component']['cutoff_only']!=r['actual_selected'] for r in group),terminalonly_changed=sum(r['selected_by_component']['terminal_only']!=r['actual_selected'] for r in group),original_mean_ties=sum(r['same_original_mean_allarms'] for r in group),quantity_mean_ties=sum(r['same_final_quantity_mean_allarms'] for r in group),cutoff_quantity_mean_ties=sum(len(set(r['total_fractions']['cutoff_only']))==1 for r in group),original_vs_without_terminal_disjoint=sum(not r['original_without_terminal_sets_intersect'] for r in group),original_vs_cutoff_disjoint=sum(not r['original_cutoff_only_sets_intersect'] for r in group),actual_nonincumbent_choices=sum(r['actual_selected']!=0 for r in group),selected_gain_single_positive_root=sum(r['selected_advantage_from_single_positive_root'] for r in group))
 out=dict(complete=True,source_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest(),methods=methods,rows=rows,scope='All recordedcandidategroups exactrescoring; alternativechosenarm canchangefutureweightpath, so notnewtrajectory orproofglobalrewardoptimum. Finalquantity includes terminalpositions andmay rewardlosingmaterialadvantage; retainthatfailuremode.')
 (O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(complete=True,methods=methods),indent=2))
if __name__=='__main__':execute()
