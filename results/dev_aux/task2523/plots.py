"""All-seed learning/consistency/actual-utility plots, never select prices."""
from pathlib import Path
import os,json
os.environ['MPLCONFIGDIR']=str(Path('.local_agent/plot-cache89').resolve())
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('results/dev_aux');OUT=R/'task2523'
def run():
 train=json.loads((R/'task2521/result.json').read_text());a=json.loads((OUT/'training-audit.json').read_text());e=json.loads((OUT/'exposure-consistency.json').read_text());seeds=[1977,8173,27182,31415];methods=['p16','p64'];names=['P fixed','N','B','R','Q']
 fig,axs=plt.subplots(4,2,figsize=(12,12),sharex=True,sharey=True)
 for arm in train['arms']:
  ax=axs[seeds.index(arm['seed']),methods.index(arm['method'])];rows=[dict(nodes=0,weights=arm['initial'])]+arm['checkpoints'];rows+=[dict(nodes=arm['nodes'],weights=arm['weights'])]
  for j,name in enumerate(names):ax.plot([r['nodes']/1e6 for r in rows],[r['weights'][j]for r in rows],label=name,lw=1.4)
  ax.set_title(str(arm['seed'])+' / '+arm['method']);ax.grid(alpha=.25)
 for ax in axs[-1]:ax.set_xlabel('Actual search nodes (millions)')
 for ax in axs[:,0]:ax.set_ylabel('Material coefficient, pawn = 1')
 axs[0,1].legend(ncol=5,fontsize=8,loc='upper left');fig.suptitle('All four initializations / same TD learner / 16 vs 64 legal prefix plies\nNo weight, seed or checkpoint selected; actual node work fixed',fontsize=13);fig.tight_layout(rect=(0,0,1,.96));fig.savefig(OUT/'all-weights.png',dpi=150);plt.close(fig)
 fig,axs=plt.subplots(4,2,figsize=(12,10),sharex=True,sharey=True)
 for i,seed in enumerate(seeds):
  for j,method in enumerate(methods):
   ax=axs[i,j];rows=[r for r in a['curves']if r['seed']==seed and r['method']==method];buckets=[[0.,0]for _ in range(6)]
   for row in rows:
    k=min(5,int(row['nodes']/250000));buckets[k][0]+=row['loss']*row['samples'];buckets[k][1]+=row['samples']
   ax.scatter([r['nodes']/1e6 for r in rows],[r['loss']for r in rows],s=5,alpha=.25)
   ax.plot([(k+.5)*.25 for k in range(6)],[x/n if n else float('nan')for x,n in buckets],color='black',marker='o',lw=1.2);ax.set_title(str(seed)+' / '+method);ax.grid(alpha=.25)
 for ax in axs[-1]:ax.set_xlabel('Actual search nodes (millions)')
 for ax in axs[:,0]:ax.set_ylabel('Mean half-square TD error')
 fig.suptitle('Moving on-policy TRAIN loss / dots = episodes, line = term-weighted250k-node bins\nDifferent visited states, not fixed validation error or a checkpoint-selection criterion');fig.tight_layout(rect=(0,0,1,.95));fig.savefig(OUT/'training-loss.png',dpi=150);plt.close(fig)
 fig,axs=plt.subplots(1,2,figsize=(11,4))
 for method in methods:
  rr=[r for r in e['consistency']if r['method']==method]
  for ax,key in zip(axs,['pairwise_free_coordinate_RMS','mean_pair_order_agreement']):ax.plot([r['target_nodes']/1e6 for r in rr],[r[key]for r in rr],marker='o',label=method)
 axs[0].set_ylabel('Pairwise free-coordinate RMS distance');axs[1].set_ylabel('Mean pair-order agreement');axs[1].set_ylim(0,1.05)
 for ax in axs:ax.set_xlabel('Registered node threshold (millions)');ax.grid(alpha=.25);ax.legend()
 fig.suptitle('Descriptive consistency across ALL four fixed initializations\nIntermediate points use last closed episode; no universal-price or convergence proof');fig.tight_layout();fig.savefig(OUT/'consistency.png',dpi=150);plt.close(fig)
 fig,axs=plt.subplots(2,2,figsize=(11,7))
 for col,panel in enumerate(['endpoint','different_foe']):
  d=json.loads((R/'task2522'/panel/'result.json').read_text());audit=json.loads((OUT/(panel+'-audit.json')).read_text())
  for j,t in enumerate(['initial','p16','p64']):
   lo=[];hi=[]
   for seed in seeds:
    row=next(r for r in d['results']if r['seed']==seed)['tallies'][t];n=2*(16 if panel=='endpoint'else 8);missing=n-sum(row.values());lo.append((row['W']-row['L']-row['U']-missing)/n);hi.append((row['W']-row['L']+row['U']+missing)/n)
   x=[i+(j-1)*.23 for i in range(4)];mid=[(a+b)/2 for a,b in zip(lo,hi)];axs[0,col].errorbar(x,mid,yerr=[(b-a)/2 for a,b in zip(lo,hi)],fmt='o',capsize=3,label=t)
  axs[0,col].set_title(panel+' / all actual W-L bounds');axs[0,col].set_xticks(range(4),seeds);axs[0,col].set_ylim(-1.05,1.05);axs[0,col].legend(fontsize=8);axs[0,col].grid(alpha=.25)
  for j,t in enumerate(methods):
   rows=[r for r in audit['estimates']if r['candidate']==t and r['baseline']=='initial'and r['seed']is not None];xx=[i+(j-.5)*.2 for i in range(4)];bounds=[r['missing_or_U_bounds']for r in rows];axs[1,col].errorbar(xx,[(a+b)/2 for a,b in bounds],yerr=[(b-a)/2 for a,b in bounds],fmt='o',label=t,capsize=3)
  axs[1,col].axhline(0,color='gray',lw=1);axs[1,col].set_xticks(range(4),seeds);axs[1,col].set_ylim(-2.05,2.05);axs[1,col].grid(alpha=.25);axs[1,col].legend(fontsize=8)
 axs[0,0].set_ylabel('Actual W-L utility, U/missing bounded');axs[1,0].set_ylabel('Paired gain over same initial policy');fig.suptitle('Final actual strength / both colors / shared baseline once per panel\nDifferent foe shares eight endpoint families; bars are censor bounds, not confidence intervals');fig.tight_layout(rect=(0,0,1,.95));fig.savefig(OUT/'actual-utility.png',dpi=150);plt.close(fig)
 print('Four all-seed scientific figures saved.')
if __name__=='__main__':run()
