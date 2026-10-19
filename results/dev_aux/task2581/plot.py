"""Scientific all-seed learning/result plots, never model selection."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path('results/dev_aux/task2580');E=Path('results/dev_aux/task2581')
def load(p):return json.loads(Path(p).read_text())
def run():
 a=load(E/'summary.json');info=load(D/'information.json');curves=load(D/'training-curves.json')['curves'];seeds=(1977,8173,27182,31415);methods=('TD_early','TD_mixed');colors={'TD_early':'#3178a4','TD_mixed':'#bb5e22'}
 plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2})
 fig,axs=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey=True)
 for ax,(ctx,foe)in zip(axs.flat,[(c,f)for c in('8','64')for f in('uniform','random48821')]):
  for j,(pair,color)in enumerate([('TD_early-initial','#3178a4'),('TD_mixed-initial','#bb5e22'),('TD_mixed-TD_early','#6f579e')]):
   vals=[a['contrasts'][ctx][pair]['by_seed'][str(s)][foe]['bounds']for s in seeds];x=[i+(j-1)*.15 for i in range(4)];mid=[sum(v)/2 for v in vals];err=[(v[1]-v[0])/2 for v in vals]
   ax.errorbar(x,mid,yerr=err,fmt='o',color=color,label=pair,capsize=3)
  ax.axhline(0,color='black',lw=.7);ax.set_xticks(range(4),seeds);ax.set_title(f'EVAL prefix {ctx}; fixed {foe}');ax.set_ylabel('Paired W-L difference')
 axs[0,0].legend(fontsize=8);fig.suptitle('ALL initializations; UNKNOWN bounds, not confidence intervals');fig.tight_layout();fig.savefig(E/'all-seed-gains.png',dpi=145);plt.close(fig)
 fig,axs=plt.subplots(2,2,figsize=(12,8),sharex=True)
 for ax,seed in zip(axs.flat,seeds):
  for m in methods:
   cc=curves[str((seed,m))];xx=[r['paid_nodes']/1e6 for r in cc]
   ax.plot(xx,[r['changing_data_loss']or 0 for r in cc],alpha=.55,lw=.7,color=colors[m],label=m)
  ax.set_title(str(seed));ax.set_xlabel('All paid TRAIN nodes (M)');ax.set_ylabel('Episode TD loss, changing data')
 axs[0,0].legend();fig.suptitle('Loss on visited trajectories is not held-out accuracy or playing strength');fig.tight_layout();fig.savefig(E/'training-loss.png',dpi=145);plt.close(fig)
 fig,axs=plt.subplots(2,2,figsize=(12,8),sharex=True)
 cs=['#2a7b9b','#7d61a4','#b57320','#45834f']
 for ax,seed in zip(axs.flat,seeds):
  for m in methods:
   cc=curves[str((seed,m))]
   for j,n in enumerate(('N','B','R','Q')):
    ax.plot([r['paid_nodes']/1e6 for r in cc],[r['weights'][j+1]for r in cc],ls='-'if m=='TD_early'else'--',color=cs[j],lw=1,label=n+('/early'if m=='TD_early'else'/mixed'))
  ax.axhline(1,color='gray',lw=.5);ax.set_title(str(seed));ax.set_xlabel('All paid TRAIN nodes (M)');ax.set_ylabel('Free signed coefficient (P=1)')
 axs[0,0].legend(ncol=2,fontsize=8);fig.suptitle('ALL price curves; solid early8 / dashed mixed8,64; no human reference fitting');fig.tight_layout();fig.savefig(E/'price-curves.png',dpi=145);plt.close(fig)
 fig,axs=plt.subplots(1,2,figsize=(12,4.8))
 labels=[];terms=[];exc=[]
 for seed in seeds:
  for m in methods:
   v=info['arms'][str((seed,m))];labels.append(str(seed)+('/E'if m=='TD_early'else'/M'));terms.append(v['valid_TD_terms_per_Mnodes']);exc.append(v['nonzero_observations_per_Mnodes'])
 for ax,vals,title in zip(axs,[terms,exc],['Valid TD terms / M paid nodes','Nonzero free gradients / M paid nodes']):
  ax.bar(range(8),vals,color=[colors[m]for s in seeds for m in methods]);ax.set_xticks(range(8),labels,rotation=55,ha='right');ax.set_title(title)
 fig.suptitle('Information counts include opponent and failed search cost; not identifiability proof');fig.tight_layout();fig.savefig(E/'information-cost.png',dpi=145);plt.close(fig)
 print('4 all-seed scientific figures rendered')
if __name__=='__main__':run()
