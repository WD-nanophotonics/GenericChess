"""All-model scientific plots; raw endpoints and finite utility bounds."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path('results/dev_aux/task2557');seeds=[1977,8173,27182,31415];colors=['#0072B2','#D55E00','#009E73','#CC79A7']
def load(p):return json.loads(Path(p).read_text())
def utility(e,path,names,title):
 fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained',sharex=True)
 for ax,foe in zip(axes,['uniform','random99031']):
  labels=[]
  for i,name in enumerate(names):
   q=next(q for q in e['contrasts']if q['foe']==foe and q['name']==name);a,b=q['bounds'];lo,hi=q['descriptive_95'];ax.hlines(i,lo,hi,color='.78',lw=5);ax.hlines(i,a,b,color='#0072B2',lw=2);ax.plot([a,b],[i,i],'|',color='#0072B2');labels.append(name.replace('TreeStrap','Tree').replace('DepthInteraction:','Interaction:'))
  ax.set_yticks(range(len(labels)),labels);ax.invert_yaxis();ax.axvline(0,color='black',lw=.8);ax.set_title('Fixed D2 foe: '+foe);ax.grid(axis='x',alpha=.2);ax.set_xlabel('Actual candidate W-L difference\nUNKNOWN / missing bounded, not draw')
 fig.suptitle(title+'\nBlue: finite utility bounds. Grey: descriptive crossed envelope; not guaranteed CI.',fontsize=11);fig.savefig(path,dpi=145);plt.close(fig)
def run(part='all'):
 if part in('all','utility'):
  e=load('results/dev_aux/task2553/audit.json');utility(e,O/'matched-depth.png',['TD-initial@D2','TreeStrap-initial@D2','TD-initial@D3','TreeStrap-initial@D3','DepthInteraction:TD-initial','DepthInteraction:TreeStrap-initial'],f"Same roots / candidate D2 versus D3; {e['returned']}/{e['planned']} returned, {e['missing']} missing")
  e=load(O/'deployment.json');utility(e,O/'training-depth.png',['D3TD-D2TD@D3','D3Tree-D2Tree@D3','D3TD-initial@D3','D3Tree-initial@D3','D3Tree-D3TD@D3','D2Tree-D2TD@D3'],f"D3 deployment throughout; OLD D2-trained versus NEW D3-trained weights\n{e['returned']}/{e['planned']} returned / {e['missing']} missing; equal TRAIN nodes, different actual cost")
 if part=='utility':return
 d=load(O/'signals.json');rows=d['rows'];features=['board P','board A','board X','hand A','hand P','hand X']
 for g in sorted({r['rule']for r in rows}):
  fig,axes=plt.subplots(2,3,figsize=(12,7),layout='constrained')
  for j,ax in enumerate(axes.flat):
   for method,marker,jitter in [('TD','o',-.035),('TreeStrap','^',.035)]:
    for z,color in zip(seeds,colors):
     rr=sorted([r for r in rows if(r['rule'],r['method'],r['seed'])==(g,method,z)],key=lambda r:r['training']);xx=[int(r['training'][-1])+jitter for r in rr];yy=[r['raw_weights'][j]for r in rr];ax.plot(xx,yy,color=color,marker=marker,ls='-'if method=='TD'else'--',lw=1,ms=4,label=str(z)+' '+method)
   ax.axhline(0,color='.5',lw=.5);ax.set_xticks([2,3],['D2 train','D3 train']);ax.set_title(features[j]);ax.set_ylabel('Raw free coefficient');ax.grid(alpha=.15)
  h,l=axes[0,0].get_legend_handles_labels();fig.legend(h,l,loc='outside lower center',ncols=4,fontsize=8);fig.suptitle(f'Rule {g}: all seeds and both learners / no deployed normalization\nTraining depth changes visitation and updates; coefficients are not intrinsic rule prices',fontsize=11);fig.savefig(O/f'endpoints-{g}.png',dpi=140);plt.close(fig)
 for method in['TD','TreeStrap']:
  fig,axes=plt.subplots(2,2,figsize=(12,7),layout='constrained')
  for ax,g in zip(axes.flat,sorted({r['rule']for r in rows})):
   for z,color in zip(seeds,colors):
    for depth,ls in [('D2','--'),('D3','-')]:
     rr=[r for r in d['loss_bins']if(r['rule'],r['method'],r['seed'],r['training'])==(g,method,z,depth)];ax.plot([r['paid_node_upper']/1000 for r in rr],[r['mean']for r in rr],color=color,ls=ls,marker='o',ms=3,label=str(z)+' '+depth)
   ax.set_title('Rule '+str(g));ax.set_xlabel('All paid TRAIN node-bin upper edge (thousands)');ax.set_ylabel('Own mean half-squared error');ax.grid(alpha=.15)
  h,l=axes[0,0].get_legend_handles_labels();fig.legend(h,l,loc='outside lower center',ncols=4,fontsize=8);fig.suptitle(method+': D3 solid / D2 dashed; all initializations\nTargets and visitation differ; loss levels are not cross-method strength or stationary test loss',fontsize=11);fig.savefig(O/f'loss-{method}.png',dpi=140);plt.close(fig)
 print('Signal/endpoint figures rendered; actual visual inspection still required')
if __name__=='__main__':run()
