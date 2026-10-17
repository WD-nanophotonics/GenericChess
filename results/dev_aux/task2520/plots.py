"""All-initialization learning/actual-strength figures; no fitted best selection."""
from pathlib import Path
import os,json
os.environ['MPLCONFIGDIR']=str(Path.cwd()/'.local_agent/plot-cache88-root')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path('results/dev_aux/task2520')
def run():
 data=json.loads((OUT/'training-audit.json').read_text());fig,axs=plt.subplots(4,2,figsize=(12,12),sharex=True,sharey=True);colors=['#0072B2','#009E73','#D55E00','#CC79A7'];names=['N','B','R','Q'];seeds=[1977,8173,27182,31415]
 for i,seed in enumerate(seeds):
  for j,method in enumerate(('root','tree')):
   ax=axs[i,j];rr=[r for r in data['curves']if r['seed']==seed and r['method']==method];initial=next(a['initial']for a in data['arms']if a['seed']==seed and a['method']==method)
   for k in range(1,5):ax.plot([0]+[r['nodes']/1e6 for r in rr],[initial[k]]+[r['weights'][k]for r in rr],color=colors[k-1],label=names[k-1],lw=1.2)
   ax.axhline(1,color='grey',lw=.5,ls=':');ax.grid(alpha=.2);ax.set_title(str(seed)+' | '+('RootStrap query'if method=='root'else'TreeStrap query mean'));ax.set_ylabel('Coefficient; pawn fixed = 1')
   if i==0:ax.legend(ncol=4,fontsize=8)
 for ax in axs[-1]:ax.set_xlabel('Training work (million searched nodes)')
 fig.suptitle('Every initial seed retained: same plainD2 / equal node ceilings\nInitial RMS matched only; later norms/data differ; no stable-ratio claim');fig.tight_layout(rect=(0,0,1,.95));fig.savefig(OUT/'root-control-weights.png',dpi=150);plt.close(fig)
 print('Rootcontrol allseed coefficient figure ready')
if __name__=='__main__':run()
