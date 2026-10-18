"""All-model scientific plots; raw endpoints and finite utility bounds."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path('results/dev_aux/task2560');seeds=[1977,8173,27182,31415];colors=['#0072B2','#D55E00','#009E73','#CC79A7']
def load(p):return json.loads(Path(p).read_text())
def utility(e,path,names,title):
 fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained',sharex=True)
 for ax,foe in zip(axes,['uniform','random99031']):
  labels=[]
  for i,name in enumerate(names):
   q=next(q for q in e['contrasts']if q['foe']==foe and q['name']==name);a,b=q['bounds'];lo,hi=q['descriptive_95'];ax.hlines(i,lo,hi,color='.78',lw=5);ax.hlines(i,a,b,color='#0072B2',lw=2);ax.plot([a,b],[i,i],'|',color='#0072B2');labels.append(name.replace('TreeStrap','Tree').replace('DepthInteraction:','Interaction:').replace('CostClock','Clock').replace('TrainRate','Rate').replace('@D3',''))
  ax.set_yticks(range(len(labels)),labels);ax.invert_yaxis();ax.axvline(0,color='black',lw=.8,zorder=0);ax.set_title('Fixed D2 foe: '+foe);ax.grid(axis='x',alpha=.2);ax.set_xlabel('Actual candidate W-L difference\nUNKNOWN / missing bounded, not draw')
 fig.suptitle(title+('\nClock=CostClock; Rate=TRAIN-derived constant step.'if any('TrainRate'in n for n in names)else'\nClock=CostClock; Mean=fixed eta0.05.')+'\nBlue: finite utility bounds. Grey: descriptive crossed envelope; not guaranteed CI.',fontsize=11);fig.savefig(path,dpi=145);plt.close(fig)
def run():
 d=load(O/'signals.json');rows=d['rows'];features=['board P','board A','board X','hand A','hand P','hand X']
 for g in sorted({r['rule']for r in rows}):
  fig,axes=plt.subplots(2,3,figsize=(12,7),layout='constrained')
  for j,ax in enumerate(axes.flat):
   for seed,color in zip(seeds,colors):
    rr=[next(r for r in rows if(r['rule'],r['method'],r['seed'])==(g,m,seed))for m in ['Mean','CostClock']];yy=[r['endpoint'][j]for r in rr];ax.plot([0,1],yy,color=color,marker='o',lw=1,label=str(seed))
   ax.axhline(0,color='.5',lw=.5);ax.set_xticks([0,1],['Fixed eta','Cost clock']);ax.set_title(features[j]);ax.set_ylabel('Raw free coefficient');ax.grid(alpha=.15)
  h,l=axes[0,0].get_legend_handles_labels();fig.legend(h,l,loc='outside lower center',ncols=4,fontsize=8);fig.suptitle(f'Rule {g}: all seeds, candidate D3 / fixed D2 foe / 200k paid nodes\nPaired endpoints from separate runs; not continuation or intrinsic rule prices',fontsize=11);fig.savefig(O/f'endpoints-{g}.png',dpi=140);plt.close(fig)
 for metric in ['mean_loss','eta_sum']:
  fig,axes=plt.subplots(2,2,figsize=(12,7),layout='constrained')
  for ax,g in zip(axes.flat,sorted({r['rule']for r in rows})):
   for seed,color in zip(seeds,colors):
    for m,ls in [('Mean','--'),('CostClock','-')]:
     r=next(r for r in rows if(r['rule'],r['method'],r['seed'])==(g,m,seed));bb=r['bins'];ax.plot([(b['bin']+1)*50 for b in bb],[b[metric]for b in bb],color=color,ls=ls,marker='o',ms=3,label=str(seed)+' '+m)
   ax.set_title('Rule '+str(g));ax.set_xlabel('All paid TRAIN node-bin upper edge (thousands)');ax.set_ylabel('Own mean one-sided loss'if metric=='mean_loss'else'Sum of per-query eta');ax.grid(alpha=.15)
  h,l=axes[0,0].get_legend_handles_labels();fig.legend(h,l,loc='outside lower center',ncols=4,fontsize=8);fig.suptitle('Cost clock solid / fixed eta dashed; all initializations\nLoss targets and visitation evolve: these levels are not stationary test loss or playing strength',fontsize=11);fig.savefig(O/(metric+'.png'),dpi=140);plt.close(fig)
 e=load(O/'deployment.json');utility(e,O/'utility.png',['CostClock-Mean@D3','CostClock-initial@D3','Mean-initial@D3'],f"Same roots / fixed foes / D3 deployment; {e['returned']}/{e['planned']} returned")
 print('7figures rendered; visual inspection still required')
if __name__=='__main__':run()
