"""Adaptive matched-prefix figure and report supplement, ALL frozen models."""
from pathlib import Path
import json
D=Path('results/dev_aux/task2544');R=Path('results/dev_aux')
def run():
 a=json.loads((D/'audit.json').read_text());r=json.loads((D/'result.json').read_text());out=['','## Separate adaptive matched-prefix followup','',f"After inspecting the original role asymmetry, ALL existing models were frozen. NEW211001..211004 families, both candidate colors, two fixed foes and matched4/5-action prefixes produced {r['actual']}/{r['expected']} slots, {r['actual_terminal']} actual terminals, {r['unknown']} UNKNOWN, {r['missing']} missing, {r['nodes']:,} nodes/{r['seconds']:.3f}s; original900s cap unchanged. No retraining/price selection or original cap extension. Full history/outcome audit passed. Parent-to-child extra legal edges {a['counts']['legal_parent_child_prefix_edges']}, terminal parents retained {a['counts'].get('terminal_parent_retained',0)}.",'','Original root replay established31 ongoing player0-to-move roots and1 already terminal root. The followup changes actual positions/history as well as side-to-move; this is an initiative/input-distribution association check, not a pure color intervention. Ordering is canonical by full prefix action count. The full stratification audit was prepared after the followup started but before inspecting its outcomes; its timing is recorded, not mislabeled wholly pre-query.','', '| Foe | Prefix length | Contrast | Finite utility bounds | Candidate0 | Candidate1 |','|---|---:|---|---|---|---|']
 for c in a['contrasts']:out.append(f"| {c['foe']} | {c['prefix_plies']} | {c['treatment']}-{c['base']} | {c['bounds']} | {c['per_color'][0]['bounds']} | {c['per_color'][1]['bounds']} |")
 out+=['','| Foe | Actual root side matches candidate | TD-WDL bounds | Pairs |','|---|---|---|---:|']
 for c in a['opportunity']:out.append(f"| {c['foe']} | {c['root_side_matches_candidate']} | {c['bounds']} | {c['pairs']} |")
 out+=['',f"Matched prefix5-minus-prefix4 TD-WDL bounds: {a['prefix_interaction']}. These are conservative finite-panel intervals, not a causal initiative effect or population/equivalence test.",'',f"Roots registered {a['roots']['registered']}, distinct full records {a['roots']['distinct']}, already terminal {a['roots']['already_terminal']}, original TRAIN overlap {a['roots']['TRAIN_overlap']}, original EVAL overlap {a['roots']['original_EVAL_overlap']}. None filtered. Exact unchanged-model controls: {a['unchanged']}. All per-rule/per-initial strata remain in the [followup audit](task2544/audit.json).",'', '![Adaptive matched-prefix TD-WDL bounds](task2544/prefix-role.png)','', 'This additional panel does not replace, pool away or hide the original registered comparison. No parameter choice is made from either evaluation. The remaining priority is to test incremental learning and its distribution/role dependence, rather than resume quantity rewards, human-price fitting or prover coverage as a prerequisite.']
 p=R/'SEGMENT_20261017_92.md';s=p.read_text();assert '## Separate adaptive matched-prefix followup'not in s;p.write_text(s+'\n'.join(out)+'\n')
 costp=R/'COST_20261017_92.json';cost=json.loads(costp.read_text());cost['producers'].append(dict(task='2544_ADAPTIVE_PREFIX_FROZEN_MODELS',nodes=r['nodes'],seconds=r['seconds']));cost['scope']+=' Separateadaptivefollowupnotoriginalcapextension; originalallclosedbeforelaunch.';costp.write_text(json.dumps(cost,indent=2));print(json.dumps(dict(followup_games=r['actual'],opportunity=a['opportunity'])))
def plot():
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 a=json.loads((D/'audit.json').read_text());fig,axes=plt.subplots(1,2,figsize=(12,5.4),sharex=True);foes=['uniform','random99031']
 for ax,foe in zip(axes,foes):
  labels=[];i=0
  for k in(4,5):
   row=next(c for c in a['contrasts']if(c['foe'],c['prefix_plies'],c['treatment'],c['base'])==(foe,k,'TD','WDL'))
   for color,shade in((0,'#0072B2'),(1,'#D55E00')):
    lo,hi=row['per_color'][color]['bounds'];ax.hlines(i,lo,hi,color=shade,lw=3);ax.plot([lo,hi],[i,i],'|',color=shade);labels.append(f'Prefix{k}, candidate{color}');i+=1
  ax.axvline(0,color='black',lw=.8);ax.set_yticks(range(4),labels);ax.invert_yaxis();ax.set_title('Fixed foe: '+foe);ax.set_xlabel('TD minus WDL actual utility bounds');ax.grid(axis='x',alpha=.2)
 fig.suptitle('Adaptive NEW matched-prefix panel: ALL prices frozen / all initializations\nFinite bounds only; added move changes states as well as side. Association, not color causality.',fontsize=11);fig.tight_layout(rect=(0,0,1,.88));fig.savefig(D/'prefix-role.png',dpi=145);plt.close(fig)
if __name__=='__main__':run()
