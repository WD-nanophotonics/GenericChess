"""Export all-seed coefficient/loss learning curves and heldout comparisons."""
from pathlib import Path
import os,json
os.environ['MPLCONFIGDIR']=str(Path.cwd()/'.local_agent/plot-cache87')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path('results/dev_aux/task2508')
def run():
 data=json.loads((OUT/'training-audit.json').read_text());fig,axs=plt.subplots(4,2,figsize=(12,13),sharex=True,sharey=True);names=['P fixed','N','B','R','Q'];colors=['#777777','#0072B2','#009E73','#D55E00','#CC79A7']
 for i,seed in enumerate((1977,8173,27182,31415)):
  for j,q in enumerate((False,True)):
   a=axs[i,j];rows=[r for r in data['curves']if r['seed']==seed and r['quiet']==q]
   initial=next(r['initial']for r in data['arms']if r['seed']==seed and r['quiet']==q)
   for k in range(1,5):a.plot([0.]+[r['nodes']/1e6 for r in rows],[initial[k]]+[r['weights'][k]for r in rows],label=names[k],color=colors[k],lw=1.4)
   a.axhline(1,color='#777777',lw=.6,ls=':');a.set_title(f'Initial seed {seed} | '+('bounded q2 TRAIN'if q else'plain TRAIN'));a.set_ylabel('Material coefficient (pawn = 1)');a.grid(alpha=.2)
   if i==0:a.legend(ncol=4,fontsize=8)
 for a in axs[-1,:]:a.set_xlabel('Training work (million searched nodes)')
 fig.suptitle('Episode-frozen TD(lambda=.95): every initial seed retained\nSame node budget; training policies/data and elapsed cost differ',fontsize=14);fig.tight_layout(rect=(0,0,1,.96));fig.savefig(OUT/'learning-weights.png',dpi=160);fig.savefig(OUT/'learning-weights.svg');plt.close(fig)
 fig,axs=plt.subplots(1,2,figsize=(12,4.8))
 for seed in(1977,8173,27182,31415):
  for q in(False,True):
   rr=[r for r in data['curves']if r['seed']==seed and r['quiet']==q];xs=[r['nodes']/1e6 for r in rr];ys=[sum(z['loss']*z['td_terms']for z in rr[max(0,i-4):i+1])/max(1,sum(z['td_terms']for z in rr[max(0,i-4):i+1]))for i in range(len(rr))];axs[0].plot(xs,ys,label=f'{seed} '+('q2'if q else'plain'),ls='--'if q else'-',lw=1)
 axs[0].set_xlabel('Training nodes (million)');axs[0].set_ylabel('Mean squared TD error / 2');axs[0].set_title('Five-episode rolling TRAIN loss\nChanging on-policy data; not validation loss');axs[0].legend(fontsize=7,ncol=2);axs[0].grid(alpha=.2)
 ev=json.loads((OUT/'evaluation-audit.json').read_text());rr=[r for r in ev['estimates']if r['seed']is None];labels=[]
 for i,r in enumerate(rr):
  lo,hi=r['missing_or_U_bounds'];ci=r['family_bootstrap_descriptive_95_envelope'];mid=(lo+hi)/2;axs[1].errorbar(mid,i,xerr=[[mid-ci[0]],[ci[1]-mid]],fmt='o'if lo==hi else'none',capsize=4,color='#0072B2');axs[1].plot([lo,hi],[i,i],lw=5,color='#D55E00');labels.append(r['candidate']+' minus '+r['baseline'])
 axs[1].axvline(0,color='black',lw=.8);axs[1].set_yticks(range(len(labels)),labels,fontsize=8);axs[1].set_xlabel('Actual W-L per game difference');axs[1].set_title('NEW16-family common-plain deployment\nAll terminal; blue: descriptive family envelope');axs[1].grid(alpha=.2);fig.tight_layout();fig.savefig(OUT/'learning-loss-and-strength.png',dpi=160);fig.savefig(OUT/'learning-loss-and-strength.svg');plt.close(fig)

 if not(OUT/'curve-evaluation-audit.json').exists():
  print('Training/endpointfiguresready; registeredcurveproducerstillactive, noimputedfigure.');return
 ev=json.loads((OUT/'curve-evaluation-audit.json').read_text());fig,axs=plt.subplots(2,3,figsize=(14,8),sharex=True,sharey=True)
 for a,seed in zip(axs.flat,(1977,8173,27182,31415,None)):
  for method,color in(('plain','#0072B2'),('q2','#D55E00')):
   xs=[0.];ys=[0.];lower=[0.];upper=[0.]
   for n in(250000,500000,750000,1000000):
    r=next(r for r in ev['estimates']if r['seed']==seed and r['candidate']==method+'_'+str(n)and r['baseline']=='initial');lo,hi=r['missing_or_U_bounds'];xs.append(n/1e6);ys.append(lo if lo==hi else float('nan'));lower.append(lo);upper.append(hi)
   a.plot(xs,ys,'o-',label=method+' TRAIN',color=color,lw=1.2,ms=3);a.fill_between(xs,lower,upper,color=color,alpha=.2)
  a.axhline(0,color='black',lw=.6);a.grid(alpha=.2);a.set_title('Pooled all four initial seeds'if seed is None else f'Initial seed {seed}');a.set_xlabel('Training node ceiling (million)');a.set_ylabel('Actual W-L gain vs own initialization');a.legend(fontsize=8)
 axs.flat[-1].axis('off');axs.flat[-1].text(0,.9,'NEW8 families, repeated at every checkpoint.\nShared baseline paid once per seed/family/role.\nShading: UNKNOWN/missing outcome bounds.\nNo point or connecting line for unresolved values.\nLines connect preregistered points, not fitted curves.\nLast CLOSED episode at or below each ceiling.\nAll deploy with plain D2 and uniform foe.\nNo best checkpoint or seed selection.',va='top',fontsize=10,linespacing=1.6)
 fig.suptitle('Independent actual-strength learning curves: all checkpoints retained',fontsize=14);fig.tight_layout(rect=(0,0,1,.95));fig.savefig(OUT/'actual-strength-curves.png',dpi=160);fig.savefig(OUT/'actual-strength-curves.svg');plt.close(fig)
 print('Six standalone learning/strength figures saved.')
if __name__=='__main__':run()
