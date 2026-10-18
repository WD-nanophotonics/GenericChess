"""Every seeded actual-strength cost curve; finite censor bounds, no selection."""
from pathlib import Path
import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path('results/dev_aux/task2571');SEEDS=[1977,8173,27182,31415];COLORS=['#2864a0','#d16a26','#308453','#894a9e'];STYLES=['-','--',':','-.'];B=[250000,500000,750000,1000000]
def curves():
 r=json.loads((D/'summary.json').read_text());fig,axs=plt.subplots(2,3,figsize=(15,9),constrained_layout=True)
 for i,foe in enumerate(['uniform','random99031']):
  for j,m in enumerate(['TD','TC','WDL']):
   ax=axs[i,j]
   for seed,c,ls in zip(SEEDS,COLORS,STYLES):
    vv=[r['all_seed_curves'][str(seed)][m][str(b)][foe]['bounds']for b in B];xx=[0]+[b/1000 for b in B];yy=[0]+[a if a==z else float('nan')for a,z in vv];ax.plot(xx,yy,color=c,ls=ls,lw=1.3,alpha=.8,label=str(seed))
    for b,(a,z)in zip(B,vv):
     if a!=z:ax.vlines(b/1000,a,z,color=c,alpha=.5)
   macro=[r['gain_vs_initial'][m][str(b)][foe]['bounds']for b in B];ax.plot([0]+[b/1000 for b in B],[0]+[a if a==z else float('nan')for a,z in macro],color='black',lw=2,marker='o',ms=4,label='All seeds')
   for b,(a,z)in zip(B,macro):
    if a!=z:ax.vlines(b/1000,a,z,color='black',lw=3)
   ax.axhline(0,color='gray',lw=.8);ax.set(title=m+' vs '+foe,xlabel='Nominal paid TRAIN nodes (thousands)',ylabel='Actual paired W-L gain vs initial');ax.set_xticks([0,250,500,750,1000]);ax.grid(alpha=.2)
 axs[0,0].legend(fontsize=8,ncol=2);fig.suptitle('Chess98: ALL frozen cost points / four new roots / both roles; last closed-episode snapshots'+chr(10)+'All seeds retained; UNKNOWN and missing bounded, not confidence intervals; no best-checkpoint selection',fontsize=12);fig.savefig(D/'strength-curves.png',dpi=140);plt.close(fig)
 fig,axs=plt.subplots(1,3,figsize=(14,4.5),constrained_layout=True)
 for ax,m in zip(axs,['TD','TC','WDL']):
  for seed,c,ls in zip(SEEDS,COLORS,STYLES):
   aa=sorted([a for a in r['snapshot_model_costs']if a['seed']==seed and(a['method']==m or a['method'].startswith(m+'@'))],key=lambda a:a['nominal']);ax.plot([a['nominal']/1000 for a in aa],[a['actual_nodes']/1000 for a in aa],color=c,ls=ls,label=str(seed))
  ax.plot([0,1000],[0,1000],color='black',lw=.8,ls=':');ax.set(title=m,xlabel='Nominal boundary (thousand nodes)',ylabel='Actual closed-episode cost (thousand nodes)');ax.grid(alpha=.2)
 axs[0].legend(fontsize=8);fig.suptitle('Snapshot cost lag: all candidate AND opponent TRAIN search work included');fig.savefig(D/'actual-snapshot-costs.png',dpi=140);plt.close(fig)

def loss():
 r=json.loads((D/'loss-diagnostics.json').read_text());fig,axs=plt.subplots(1,2,figsize=(12,4.5),constrained_layout=True)
 for ax,m in zip(axs,['TD','TC']):
  for seed,c,ls in zip(SEEDS,COLORS,STYLES):
   aa=sorted([x for x in r['training_loss_cost_curves']if x['seed']==seed and x['method']==m],key=lambda x:x['nominal_nodes']);ax.plot([x['actual_nodes']/1000 for x in aa],[x['weighted_changing_data_loss']for x in aa],color=c,ls=ls,marker='o',ms=3,label=str(seed))
  ax.set(title=m,xlabel='Actual paid TRAIN nodes (thousands)',ylabel='Cumulative mean half squared TD residual');ax.grid(alpha=.2)
 axs[0].legend(fontsize=8);fig.suptitle('Changing TRAIN data loss is not independent validation or strength'+chr(10)+'All four initializations; WDL selector has no TD loss and is excluded from these two panels',fontsize=11);fig.savefig(D/'training-loss-cost.png',dpi=140);plt.close(fig)

def context():
 d=Path('results/dev_aux/task2572');r=json.loads((d/'summary.json').read_text());fig,axs=plt.subplots(2,3,figsize=(15,8),constrained_layout=True)
 for i,foe in enumerate(['uniform','random99031']):
  for j,m in enumerate(['TD','TC','WDL']):
   ax=axs[i,j]
   for x,ctx in enumerate(['plain','q2']):
    for k,seed in enumerate(SEEDS):
     a,z=r['all_seed_curves'][str(seed)][m][ctx][foe]['bounds'];xx=x+(k-1.5)*.09;ax.vlines(xx,a,z,color=COLORS[k],lw=1);ax.scatter([xx,xx],[a,z],color=COLORS[k],s=22)
    a,z=r['within_context_gain'][m][ctx][foe]['bounds'];ax.vlines(x,a,z,color='black',lw=3);ax.scatter([x,x],[a,z],color='black',marker='_',s=140)
   a,z=r['difference_of_gains'][m][foe]['bounds'];ax.vlines(2,a,z,color='black',lw=3);ax.scatter([2,2],[a,z],color='black',marker='_',s=140)
   ax.axhline(0,color='gray',lw=.8);ax.set_xticks([0,1,2],['Plain gain','Bounded q2 gain','Gain difference'],rotation=15);ax.set(title=m+' vs '+foe,ylabel='Paired W-L difference');ax.grid(axis='y',alpha=.2)
 fig.suptitle('Frozen prices under candidate-only search change; opponent always plain D2'+chr(10)+'Black aggregate; colored ALL4 seeds left-to-right; finite censor bounds, not CIs',fontsize=12);fig.savefig(d/'context-gains.png',dpi=140);plt.close(fig)
if __name__=='__main__':globals()[sys.argv[1]]()
