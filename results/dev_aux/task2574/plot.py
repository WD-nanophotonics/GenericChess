"""All-seed finite teacher-transfer effects, with no winner/model selection."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path('results/dev_aux/task2575')
def run():
 r=json.loads((D/'summary.json').read_text());fig,axs=plt.subplots(1,2,figsize=(12,5),constrained_layout=True);keys=['TD-initial','TD_mixed-initial','TD_mixed-TD'];seeds=[1977,8173,27182,31415];colors=['#2864a0','#d16a26','#308453','#894a9e']
 for ax,foe in zip(axs,['uniform','random48821']):
  for i,key in enumerate(keys):
   for j,seed in enumerate(seeds):
    a,b=r['contrasts'][key]['by_seed'][str(seed)][foe]['bounds'];x=i+(j-1.5)*.10;ax.vlines(x,a,b,color=colors[j],lw=1);ax.scatter([x,x],[a,b],color=colors[j],s=22,label=str(seed)if i==0 else None)
   a,b=r['contrasts'][key]['by_foe'][foe]['bounds'];ax.vlines(i,a,b,color='black',lw=3);ax.scatter([i,i],[a,b],color='black',marker='_',s=140)
  ax.axhline(0,color='gray',lw=.8);ax.set_xticks(range(3),['Old fixed - initial','New mixed - initial','Mixed - fixed'],rotation=15);ax.set(title=foe,ylabel='Actual paired W-L difference');ax.grid(axis='y',alpha=.2)
 axs[0].legend(fontsize=8);fig.suptitle('TD teacher-protocol transfer: all 4 seeds / new 4 roots / both roles'+chr(10)+'Same TRAIN node budgets, different data/episode counts; finite censor bounds, not CIs',fontsize=11);fig.savefig(D/'teacher-transfer.png',dpi=140);plt.close(fig)
if __name__=='__main__':run()
