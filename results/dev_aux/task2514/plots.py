"""All-initialization learning/actual-strength figures; no fitted best selection."""
from pathlib import Path
import os,json
os.environ['MPLCONFIGDIR']=str(Path.cwd()/'.local_agent/plot-cache88')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path('results/dev_aux/task2514')
def run():
 data=json.loads((OUT/'training-audit.json').read_text());fig,axs=plt.subplots(4,2,figsize=(12,12),sharex=True,sharey=True);colors=['#0072B2','#009E73','#D55E00','#CC79A7'];names=['N','B','R','Q'];seeds=[1977,8173,27182,31415]
 for i,seed in enumerate(seeds):
  for j,method in enumerate(('td','tree')):
   ax=axs[i,j];rr=[r for r in data['curves']if r['seed']==seed and r['method']==method];initial=next(a['initial']for a in data['arms']if a['seed']==seed and a['method']==method)
   for k in range(1,5):ax.plot([0]+[r['nodes']/1e6 for r in rr],[initial[k]]+[r['weights'][k]for r in rr],color=colors[k-1],label=names[k-1],lw=1.2)
   ax.axhline(1,color='grey',lw=.5,ls=':');ax.grid(alpha=.2);ax.set_title(str(seed)+' | '+('TDLeaf episode sum'if method=='td'else'TreeStrap query mean'));ax.set_ylabel('Coefficient; pawn fixed = 1')
   if i==0:ax.legend(ncol=4,fontsize=8)
 for ax in axs[-1]:ax.set_xlabel('Training work (million searched nodes)')
 fig.suptitle('Every initial seed retained: same plainD2 / equal node ceilings\nDifferent update units and on-policy data; not stable-ratio evidence');fig.tight_layout(rect=(0,0,1,.95));fig.savefig(OUT/'all-weights.png',dpi=150);plt.close(fig)
 fig,axs=plt.subplots(1,3,figsize=(15,5),sharey=True,sharex=True)
 for ax,panel,title in zip(axs,('midpoint','endpoint','different_foe'),('500k node ceiling | NEW8 families','1M nodes | NEW16 families','1M nodes | matched8 / random foe')):
  ev=json.loads((OUT/(panel+'-audit.json')).read_text());pooled=[r for r in ev['estimates']if r['seed']is None]
  for i,r in enumerate(pooled):
   lo,hi=r['missing_or_U_bounds'];ci=r['descriptive_family_95_envelope'];ax.plot([ci[0],ci[1]],[i,i],color='#0072B2',lw=1);ax.plot([lo,hi],[i,i],color='#D55E00',lw=6)
   if lo==hi:ax.plot(lo,i,'o',color='#0072B2')
  ax.set_yticks(range(3),['TD - initial','Tree - initial','Tree - TD']);ax.axvline(0,color='black',lw=.7);ax.grid(alpha=.2);ax.set_xlabel('Actual W-L per game difference');ax.set_title(title,fontsize=10)
 fig.suptitle('Common plainD2 deployment: actual rule outcomes, all seeds/roles\nBlue: descriptive family envelope; orange: UNKNOWN/missing bounds (not draw); panels not longitudinal pairs',fontsize=11);fig.tight_layout(rect=(0,0,1,.87));fig.savefig(OUT/'actual-strength.png',dpi=150);plt.close(fig)
 fig,axs=plt.subplots(1,2,figsize=(12,4.7))
 for method,ax in zip(('td','tree'),axs):
  for seed in seeds:
   rr=[r for r in data['curves']if r['seed']==seed and r['method']==method];yy=[]
   for i in range(len(rr)):
    ss=rr[max(0,i-4):i+1];yy.append(sum(r['loss']*r['samples']for r in ss)/max(1,sum(r['samples']for r in ss)))
   ax.plot([r['nodes']/1e6 for r in rr],yy,label=str(seed),lw=1)
  ax.set_title(('TDLeaf temporal errors'if method=='td'else'TreeStrap one-sided internal-node errors')+'\nFive-episode rolling TRAIN loss');ax.set_xlabel('Million searched nodes');ax.set_ylabel('Half-squared error (different objectives)');ax.grid(alpha=.2);ax.legend(fontsize=8)
 fig.suptitle('Changing on-policy distributions; losses are NOT directly comparable or strength labels',fontsize=11);fig.tight_layout(rect=(0,0,1,.92));fig.savefig(OUT/'training-loss.png',dpi=150);plt.close(fig);print('Three standalone PNG figures ready')
if __name__=='__main__':run()
