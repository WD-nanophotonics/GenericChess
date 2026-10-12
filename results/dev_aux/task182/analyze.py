"""Weighted per-root concentration; positive support count alone is not robustness."""
import json,statistics,hashlib
from fractions import Fraction as F
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task182';O.mkdir(exist_ok=True);P=R/'results/dev_aux/task174/analysis.json';X=json.loads(P.read_bytes());out=[]
for opponent in ('random','unit2ply'):
 group=[r for r in X['rows'] if r['opponent']==opponent and r['actual_selected']!=0];rows=[]
 for r in group:
  chosen=r['actual_selected'];clusters=r['per_root_clusters'];gains=[F(c['delta_from_incumbent']['original'][chosen]) for c in clusters];largest=max(range(len(gains)),key=lambda i:gains[i]);c=clusters[largest]
  rows.append(dict(seed=r['seed'],sweep=r['sweep'],coordinate=r['coordinate'],actual_selected=chosen,largest_positive_root_share=r['largest_positive_root_share'],positive_advantage_root_count=r['positive_advantage_root_count'],largest_root=largest,selected_still_optimal_without_largest_root=chosen in c['removed_root_original_best'],total_original_advantage=r['selected_original_advantage'],largest_root_original_gain=str(gains[largest]),largest_root_terminal_gain=c['delta_from_incumbent']['terminal'][chosen],largest_root_cutoff_gain=c['delta_from_incumbent']['cutoff_only'][chosen],largest_root_speed_gain=c['delta_from_incumbent']['speed'][chosen]))
 out.append(dict(opponent=opponent,actual_nonincumbent_updates=len(rows),largest_root_positive_share_atleast_90pct=sum(r['largest_positive_root_share']>=.9 for r in rows),selected_not_optimal_after_largest_root_removed=sum(not r['selected_still_optimal_without_largest_root'] for r in rows),rows=rows))
data=dict(complete=True,source_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),methods=out,correction='Positive advantage in multiple roots doesnotprovewidelysupported gains: one rootmaycontribute>99pct while othersare tiny. Earlier checkpoint shorthand gainsnotsinglecluster meant positivecountonly andmustnot beusedasweightedrobustness claim.',threshold='90pct is a descriptive posthoc summary, not hypothesis/significance threshold; all exactcomponents and per-root removalbestsets retained.',scope='Recorded adaptivecandidate data only; not independenttrajectory, formalconfidence orsourcecause proof.')
(O/'analysis.json').write_text(json.dumps(data,indent=2),encoding='utf-8');print(json.dumps([dict(opponent=r['opponent'],noninc=r['actual_nonincumbent_updates'],share90=r['largest_root_positive_share_atleast_90pct'],lost_optimal=r['selected_not_optimal_after_largest_root_removed']) for r in out],indent=2))
