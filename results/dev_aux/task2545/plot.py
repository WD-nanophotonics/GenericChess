"""All frozen-theta role means; finite local geometry, not a WDL gradient."""
from pathlib import Path
import json,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path('results/dev_aux/task2545')
def run():
 cells=json.loads((D/'cells.json').read_text());weighted=json.loads((D/'training-role-weights.json').read_text());index={tuple(x['key']):x for x in weighted['rows']};fig,ax=plt.subplots(1,2,figsize=(11,4.6));xy=[];zeros=0
 for c in cells:
  if not c['complete_four_family_pair']:continue
  if c['cosine']is None:zeros+=1;continue
  r=index[tuple(c['key'])];d=r['mixed'];nd=math.sqrt(sum(x*x for x in d));norms=[x['norm']for x in c['roles']]
  if nd==0:zeros+=1;continue
  y=min(v/(n*nd)for v,n in zip(r['alignment'],norms));bad=any(r['negative']);ax[0].scatter(c['cosine'],y,s=17,alpha=.5,c='#D55E00'if bad else'#0072B2');xy.append((c['cosine'],y))
 ax[0].axhline(0,color='black',lw=.7);ax[0].axvline(0,color='black',lw=.7);ax[0].set(xlim=(-1.05,1.05),ylim=(-1.05,1.05),xlabel='Cosine between the two role-mean directions',ylabel='Minimum normalized alignment to weighted mixture',title=f'ALL {len(xy)} nonzero complete cells; {zeros} zero-role cells separate')
 labs=[];a=[];b=[];z=[]
 for gs in sorted({c['key'][0]for c in cells}):
  rr=[c for c in cells if c['complete_four_family_pair']and c['key'][0]==gs];labs.append(str(gs));a.append(sum(any(index[tuple(c['key'])]['negative'])for c in rr));b.append(sum(all(v>0 for v in index[tuple(c['key'])]['alignment'])for c in rr));z.append(len(rr)-a[-1]-b[-1])
 ax[1].bar(labs,a,label='One role negative',color='#D55E00');ax[1].bar(labs,b,bottom=a,label='Both positive',color='#0072B2');ax[1].bar(labs,z,bottom=[x+y for x,y in zip(a,b)],label='Zero role',color='.7');ax[1].set(ylabel='Complete four-family cells',xlabel='TRAIN-exposed generated rule',title='Actual original TD game-role weights; all initializations');ax[1].legend(fontsize=8)
 fig.suptitle('Reused frozen-theta WDL TRAIN trajectories: local TD surrogate direction only\nNegative cosine alone does not establish harmful mixing. Repeated theta / small correlated cells.',fontsize=10);fig.tight_layout(rect=(0,0,1,.89));fig.savefig(D/'role-credit.png',dpi=140);plt.close(fig);print('role-credit.png')
if __name__=='__main__':run()
