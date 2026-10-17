"""All-rule/all-initial plots from closed actual learningcurve receipts."""
from pathlib import Path
import os,json,collections
os.environ['MPLCONFIGDIR']=str(Path('.local_agent/mpl90').resolve())
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path('results/dev_aux/task2527');D=Path('results/dev_aux/task2529')
def run():
 p=json.loads((T/'registration.json').read_text());tr=json.loads((T/'result.json').read_text());diag=json.loads((D/'learning-diagnostics.json').read_text());ev=json.loads((D/'evaluation-audit.json').read_text());idx={(a['generator_seed'],a['seed']):a for a in tr['arms']};colors=plt.get_cmap('tab10');labels=['board P (fixed)','board A','board X','hand A','hand P','hand X'];fig,axes=plt.subplots(4,4,figsize=(17,12),sharex=True,constrained_layout=True)
 for i,gs in enumerate(p['generator_seeds']):
  for j,seed in enumerate(p['initial_seeds']):
   ax=axes[i,j];a=idx.get((gs,seed));ax.set_title(f'Rule {gs}; init {seed}',fontsize=9);ax.grid(alpha=.2)
   if a is None:ax.text(.5,.5,'UNSTARTED',transform=ax.transAxes,ha='center');continue
   snaps=[dict(nodes=0,weights=a['initial'])]+a['snapshots'];x=[s['nodes']/1000 for s in snaps]
   for k in range(6):ax.plot(x,[s['weights'][k]for s in snaps],marker='o',ms=3,lw=1,color=colors(k),label=labels[k])
   if i==3:ax.set_xlabel('Actual closed-episode nodes (thousands)')
   if j==0:ax.set_ylabel('Raw coefficient / fixed board P = 1')
 fig.legend(*axes[0,0].get_legend_handles_labels(),loc='outside lower center',ncol=6,fontsize=9);fig.suptitle('All 16 rule-conditioned TD models; all checkpoints, no selected winner',fontsize=15);fig.savefig(D/'all-weights.png',dpi=170);plt.close(fig)
 fig,axes=plt.subplots(4,2,figsize=(11,12),sharex=True,constrained_layout=True)
 for i,gs in enumerate(p['generator_seeds']):
  c=[x for x in diag['curves']if x['generator_seed']==gs];x=[0 if a['level']=='initial'else int(a['level'][1:])/1000 for a in c];axes[i,0].plot(x,[a['summary']['free_coordinate_pairwise_RMS']for a in c],'-o');axes[i,1].plot(x,[a['summary']['all_channel_pairwise_order_agreement']for a in c],'-o');axes[i,0].set_ylabel(f'Rule {gs}');axes[i,1].set_ylim(-.05,1.05)
  for ax in axes[i]:ax.grid(alpha=.2)
 axes[0,0].set_title('Pairwise RMS across 5 free coordinates');axes[0,1].set_title('Pairwise ordering agreement across all 6 channels');axes[-1,0].set_xlabel('Nominal checkpoint nodes (thousands)');axes[-1,1].set_xlabel('Nominal checkpoint nodes (thousands)');fig.suptitle('Within each rule only: four initializations; not a universal price scale',fontsize=12);fig.savefig(D/'consistency.png',dpi=170);plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,constrained_layout=True)
 for ax,gs in zip(axes.flat,p['generator_seeds']):
  for seed in p['initial_seeds']:
   b=[r for r in diag['bins']if r['generator_seed']==gs and r['seed']==seed];b.sort(key=lambda r:r['node_bin']);ax.plot([(r['node_bin']+.5)*62.5 for r in b],[r['episodes']['half_square_sum']/max(1,r['episodes']['loss_terms'])for r in b],'-o',label=str(seed),ms=4)
  ax.set_title(f'Rule {gs}');ax.grid(alpha=.2);ax.set_ylabel('Mean half-squared TD residual / valid term');ax.set_xlabel('62,500-node bins (thousands)');ax.legend(title='Initialization',fontsize=8)
 fig.suptitle('Changing on-policy TRAIN loss; not fixed validation error or model selection',fontsize=12);fig.savefig(D/'training-loss.png',dpi=170);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(13,5.5),constrained_layout=True);x=[int(c['level'][1:])/1000 for c in ev['curves']];lo=[c['pooled_gain_bounds'][0]for c in ev['curves']];hi=[c['pooled_gain_bounds'][1]for c in ev['curves']];outerlo=[c['descriptive_rule_seed_family_95_envelope'][0]for c in ev['curves']];outerhi=[c['descriptive_rule_seed_family_95_envelope'][1]for c in ev['curves']];ax=axes[0];ax.fill_between(x,outerlo,outerhi,alpha=.14,color='steelblue',label='Descriptive rule/seed/family 95% envelope');ax.fill_between(x,lo,hi,alpha=.35,color='steelblue',label='UNKNOWN/missing gain bounds');ax.plot(x,lo,'v-',color='steelblue');ax.plot(x,hi,'^-',color='steelblue');ax.axhline(0,color='black',lw=.8);ax.grid(alpha=.2);ax.set_xlabel('Nominal TRAIN node checkpoint (thousands)');ax.set_ylabel('Paired actual W-L gain over initialization');ax.legend(fontsize=8);ax.set_title('Same NEW starts / fixed uniform opponent')
 levels=['initial']+['n'+str(t)for t in p['checkpoints']];count={l:collections.Counter()for l in levels}
 for r in ev['tallies']:count[r['treatment']].update(r['counts'])
 for l in levels:count[l]['M']=128-sum(count[l].values())
 bottom=[0]*len(levels)
 for k,col in [('W','#3a9d63'),('L','#d65a53'),('D','#a5a5a5'),('U','#e4ba45'),('M','#d6d9dd')]:
  values=[count[l][k]for l in levels];axes[1].bar(range(4),values,bottom=bottom,color=col,label=k,hatch='//'if k=='M'else None);bottom=[a+b for a,b in zip(bottom,values)]
 axes[1].set_xticks(range(4),['Init','62.5k','125k','250k']);axes[1].set_ylim(0,135);axes[1].set_ylabel('Physical evaluation games');axes[1].set_title('Real W/L/D; U = censored; M = missing');axes[1].legend(ncol=5,fontsize=9);fig.suptitle('All predeclared Generic checkpoints; repeated families are not independent units',fontsize=12);fig.savefig(D/'actual-strength.png',dpi=170);plt.close(fig)
 if(D/'foe-audit.json').exists():
  foe=json.loads((D/'foe-audit.json').read_text());shift=json.loads((D/'foe-shift.json').read_text());fig,axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
  for data,color,label in[(ev,'steelblue','Uniform foe'),(foe,'darkorange','Fixed random foe 99031')]:
   low=[c['pooled_gain_bounds'][0]for c in data['curves']];high=[c['pooled_gain_bounds'][1]for c in data['curves']];axes[0].fill_between(x,low,high,color=color,alpha=.22,label=label);axes[0].plot(x,low,'v-',color=color);axes[0].plot(x,high,'^-',color=color)
  low=[c['foe_minus_uniform_gain_bounds'][0]for c in shift['interaction_curves']];high=[c['foe_minus_uniform_gain_bounds'][1]for c in shift['interaction_curves']];axes[1].fill_between(x,low,high,alpha=.25,color='purple');axes[1].plot(x,low,'v-',color='purple');axes[1].plot(x,high,'^-',color='purple');axes[0].legend(fontsize=9)
  for ax in axes:ax.axhline(0,lw=.8,color='black');ax.grid(alpha=.2);ax.set_xlabel('Nominal TRAIN checkpoint (thousands of nodes)')
  axes[0].set_title('Paired W-L gain bounds, including all UNKNOWN');axes[1].set_title('Difference of gains: random minus uniform');axes[0].set_ylabel('W-L gain over initialization');axes[1].set_ylabel('Conservative interaction interval');fig.suptitle('Matched same starts / all models and checkpoints; no general opponent claim');fig.savefig(D/'opponent-switch.png',dpi=170);plt.close(fig)
 print('All5 figures written from closed receipts')
if __name__=='__main__':run()
