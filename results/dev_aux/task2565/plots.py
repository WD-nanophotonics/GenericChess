"""All-initial cost/weight/loss curves and finite actualWLD bounds; no selection."""
from pathlib import Path
import json,sys,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path('results/dev_aux/task2565');METHODS=['Fixed','SelfCandidate','SelfEvery'];COLORS=['#555555','#2277aa','#d97800'];STYLES=['-','--',':','-.']
def train_chess():
 d=D/'chess';r=json.loads((d/'result.json').read_text());games=[json.loads(l)for l in(d/'games.jsonl').open()];fig,axs=plt.subplots(2,3,figsize=(13,7),constrained_layout=True)
 for j,ax in enumerate(axs.flat):
  if j==5:ax.axis('off');ax.text(0,.9,'All 4 random initializations\nSolid/dash/dot/dash-dot = seeds\n1977 / 8173 / 27182 / 31415\nPawn fixed at 1\nD2, no quiescence or human priors\nNot a convergence/strength claim',va='top',fontsize=10);continue
  for a in r['arms']:
   seed=a['seed'];method=a['method'];g=[g for g in games if g['seed']==seed and g['method']==method];x=[0]+[g['total_nodes']for g in g];y=[a['initial'][j]]+[g['weights'][j]for g in g];ax.step(np.array(x)/1000,y,where='post',color=COLORS[METHODS.index(method)],linestyle=STYLES[[1977,8173,27182,31415].index(seed)],alpha=.75,lw=1)
  ax.set(title=['Pawn','Knight','Bishop','Rook','Queen'][j],xlabel='Paid BOTH-actor search nodes (thousands)',ylabel='Raw coefficient');ax.grid(alpha=.2)
 for m,c in zip(METHODS,COLORS):axs.flat[0].plot([],[],color=c,label=m)
 axs.flat[0].legend(fontsize=8);fig.suptitle('Chess96: every seeded material-learning trajectory');fig.savefig(d/'weights.png',dpi=140);plt.close(fig)
 fig,axs=plt.subplots(1,2,figsize=(12,4),constrained_layout=True)
 for a in r['arms']:
  g=[g for g in games if g['seed']==a['seed']and g['method']==a['method']];x=np.array([g['total_nodes']for g in g])/1000;c=COLORS[METHODS.index(a['method'])];ls=STYLES[[1977,8173,27182,31415].index(a['seed'])];axs[0].plot(x,[g['stats']['loss']for g in g],color=c,ls=ls,alpha=.75);axs[1].plot(x,np.cumsum([g['stats']['samples']for g in g]),color=c,ls=ls,alpha=.75)
 axs[0].set(title='TD error on changing training trajectories',ylabel='Mean half squared TD residual');axs[1].set(title='Completed TD terms (not independent labels)',ylabel='Cumulative terms')
 axs[0].set_ylim(bottom=0)
 for m,c in zip(METHODS,COLORS):axs[0].plot([],[],color=c,label=m)
 axs[0].legend(fontsize=8)
 for ax in axs:ax.set_xlabel('Paid BOTH-actor search nodes (thousands)');ax.grid(alpha=.2)
 fig.suptitle('Chess96: loss and information use, ALL seeds (no heldout-loss claim)');fig.savefig(d/'loss-terms.png',dpi=140);plt.close(fig)
def train_generic():
 d=D/'generic';r=json.loads((d/'result.json').read_text());p=json.loads((d/'plan.json').read_text());bounds=[0]+p['snapshot_nodes']
 for gs in sorted({a['generator_seed']for a in r['arms']}):
  fig,axs=plt.subplots(2,3,figsize=(13,7),constrained_layout=True)
  for j,ax in enumerate(axs.flat):
   for m,c in zip(METHODS,COLORS):
    aa=[a for a in r['arms']if a['generator_seed']==gs and a['method']==m]
    for a in aa:
     xx=[0];yy=[a['initial'][j]]
     for b in p['snapshot_nodes']:
      ss=[s for s in a['snapshots']if s['boundary']==b]
      if ss:xx.append(ss[0]['nodes']);yy.append(ss[0]['weights'][j])
     ax.plot(np.array(xx)/1000,yy,color=c,ls=STYLES[[1977,8173,27182,31415].index(a['seed'])],alpha=.75,lw=1)
    ax.plot([],[],color=c,label=m)
   ax.set(title=['board P','board A','board X','hand A','hand P','hand X'][j],xlabel='Actual closed-episode paid nodes (thousands)',ylabel='Raw signed coefficient');ax.grid(alpha=.2)
  axs.flat[0].legend(fontsize=8);fig.suptitle(f'Rule {gs}: all 4 seeds; actual paid nodes\n1977 solid | 8173 dash | 27182 dot | 31415 dash-dot',fontsize=11);fig.savefig(d/f'weights-{gs}.png',dpi=140);plt.close(fig)
def strength():
 d=D/'chess';c=D/'chess-curve';base={tuple(x['slot']):x for x in map(json.loads,(d/'eval-games.jsonl').open())};extra={tuple(x['slot']):x for x in map(json.loads,(c/'eval-games.jsonl').open())};seeds=[1977,8173,27182,31415];families=[321001,321002];fig,axs=plt.subplots(1,2,figsize=(13,5),constrained_layout=True);saved=[]
 def val(rows,slot):
  r=rows.get(tuple(slot));v=None if r is None else r['reward'];return(-1,1)if v is None else(v,v)
 for ax,foe in zip(axs,['uniform','random99031']):
  for method,col in zip(METHODS,COLORS):
   allseed=[]
   for seed in seeds:
    vals=[]
    for n in [25000,50000,75000,100000]:
     rows=base if n==100000 else extra;m=method if n==100000 else method+'@'+str(n);bs=[]
     for f in families:
      for color in [0,1]:
       l=val(rows,[0,seed,f,color,m,foe]);r=val(base,[0,seed,f,color,'initial',foe]);bs.append((l[0]-r[1],l[1]-r[0]))
     lo,hi=[sum(v[j]for v in bs)/len(bs)for j in [0,1]];vals.append((n,lo,hi));saved.append(dict(seed=seed,method=method,foe=foe,nominal_nodes=n,gain_bounds=[lo,hi]))
    allseed.append(vals);xx=[0]+[n/1000 for n,_,_ in vals];yy=[0]+[lo if lo==hi else np.nan for _,lo,hi in vals];ax.plot(xx,yy,color=col,alpha=.35,lw=1,ls=STYLES[seeds.index(seed)])
    for n,lo,hi in vals:
     if lo!=hi:ax.vlines(n/1000,lo,hi,color=col,alpha=.15,lw=1)
   for k,n in enumerate([25000,50000,75000,100000]):
    lo=sum(x[k][1]for x in allseed)/4;hi=sum(x[k][2]for x in allseed)/4;offset=(METHODS.index(method)-1)*1.3;ax.vlines(n/1000+offset,lo,hi,color=col,lw=3);ax.scatter([n/1000+offset]*2,[lo,hi],color=col,s=22,marker='_')
   ax.plot([],[],color=col,label=method)
  ax.axhline(0,color='black',lw=1,ls='--');ax.set(title=foe,xlabel='Nominal TRAIN nodes (thousands); last closed-episode snapshot',ylabel='Actual W-L gain over initialization (finite bounds)');ax.set_xticks([0,25,50,75,100]);ax.grid(alpha=.2);ax.legend(fontsize=8)
 fig.suptitle('Chess96 actual strength curves: all seeds / two roots / both roles; U & missing bounded, not CIs');fig.savefig(c/'strength.png',dpi=140);plt.close(fig);(c/'curve-bounds.json').write_text(json.dumps(saved,indent=2))
if __name__=='__main__':globals()[sys.argv[1]]()
