"""All48 raw endpoints and separate second-panel utility; no selection."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from results.dev_aux.task2560.plots import utility
A=Path('results/dev_aux/task2564')
def run():
 e=json.loads((A/'deployment.json').read_text());utility(e,A/'utility.png',['CostClock-TrainRate@D3','TrainRate-Mean@D3','CostClock-Mean@D3','TrainRate-initial@D3','CostClock-initial@D3','Mean-initial@D3'],f"Separate NEW roots / TRAIN-derived constant-rate control; {e['returned']}/{e['planned']} returned")
 models=json.loads(Path('results/dev_aux/task2563/models.json').read_text())['arms'];seeds=[1977,8173,27182,31415];colors=['#0072B2','#D55E00','#009E73','#CC79A7'];methods=['Mean','CostClock','TrainRate']
 for kind,features,start in [('board',['P','A','X'],0),('hand',['A','P','X'],3)]:
  fig,axes=plt.subplots(4,3,figsize=(12,12),layout='constrained')
  for i,g in enumerate(sorted({a['generator_seed']for a in models})):
   for j,feature in enumerate(features):
    ax=axes[i,j]
    for seed,color in zip(seeds,colors):
     yy=[next((a['weights'][start+j]for a in models if(a['generator_seed'],a['method'],a['seed'])==(g,m,seed)),float('nan'))for m in methods];ax.plot(range(3),yy,color=color,marker='o',lw=1,label=str(seed))
    ax.axhline(0,color='.5',lw=.5);ax.set_xticks(range(3),['Mean','Clock','TrainRate']);ax.set_title(str(g)+' '+kind+' '+feature);ax.set_ylabel('Raw free coefficient');ax.grid(alpha=.15)
  h,l=axes[0,0].get_legend_handles_labels();fig.legend(h,l,loc='outside lower center',ncols=4,fontsize=8);fig.suptitle('All initializations and all3 learned methods / each3.2M TRAIN nodes\nRaw endpoints from separate runs; actual step counts/masses differ; no human-price labels',fontsize=11);fig.savefig(A/(kind+'-all-methods.png'),dpi=140);plt.close(fig)
 print('3followupfigures rendered; actual inspection required')
if __name__=='__main__':run()
