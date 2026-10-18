"""Standalone scientific figures, all seeds and actual paid costs."""
from pathlib import Path
import os,json
os.environ.setdefault("MPLCONFIGDIR",str(Path(".local_agent/mpl99").resolve()))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
D=Path("results/dev_aux/task2576");E=Path("results/dev_aux/task2577")
def run():
 s=json.loads((E/"summary.json").read_text());info=json.loads((D/"information.json").read_text());foes=list(s["matching_interaction"]);colors={"TD_plain-initial":"#2166ac","TD_q2-initial":"#b2182b","TD_q2-TD_plain":"#555555"}
 fig,ax=plt.subplots(1,2,figsize=(11,4),sharey=True)
 for a,foe in zip(ax,foes):
  for j,(method,color)in enumerate(colors.items()):
   for i,context in enumerate(("plain","q2")):
    v=s["contrasts"][context][method]["by_foe"][foe]["bounds"];x=i+(j-1)*.18;a.plot([x,x],v,color=color,lw=3);a.scatter([x],[(v[0]+v[1])/2],color=color,label=method if i==0 else None)
    values=[s["contrasts"][context][method]["by_seed"][str(seed)][foe]["bounds"]for seed in(1977,8173,27182,31415)]
    for k,vv in enumerate(values):a.scatter(x+(k-1.5)*.025,sum(vv)/2,marker="x",color=color,alpha=.5,s=16)
  a.axhline(0,color="black",lw=.7);a.set_xticks([0,1],["plain deployment","bounded q2 deployment"]);a.set_title(foe);a.set_ylabel("Mean paired W-L gain");a.grid(alpha=.15)
 ax[0].legend(fontsize=8);fig.suptitle("All four initializations: TRAIN context versus DEPLOY context\nmarkers: bounds midpoint (exact mean when resolved); bars: unresolved bounds; x: each seed; not CIs",fontsize=10);fig.tight_layout();fig.savefig(E/"context-matching.png",dpi=160);plt.close(fig)
 fig,ax=plt.subplots(1,2,figsize=(11,4))
 labels=[];nodes=[];terms=[];grad=[];walls=[]
 for seed in(1977,8173,27182,31415):
  for m in("TD_plain","TD_q2"):
   a=info["arms"][str((seed,m))];labels.append(str(seed)+"/"+m[3:]);terms.append(a["valid_TD_terms_per_Mnodes"]);grad.append(a["nonzero_observations_per_Mnodes"]);walls.append(a["seconds"]/60)
 x=list(range(len(labels)));ax[0].bar([i-.2 for i in x],terms,.4,label="valid TD terms / M paid nodes");ax[0].bar([i+.2 for i in x],grad,.4,label="nonzero free-gradient observations / M paid nodes");ax[0].set_ylim(0,max(terms+grad)*1.28);ax[0].legend(fontsize=8);ax[1].bar(x,walls);ax[1].set_ylabel("Actual TRAIN producer minutes")
 for a in ax:a.set_xticks(x,labels,rotation=55,ha="right");a.grid(axis="y",alpha=.15)
 fig.suptitle("Same 1.5M paid-node budget per arm; data volume and wall time can differ",fontsize=11);fig.tight_layout();fig.savefig(E/"information-cost.png",dpi=160);plt.close(fig)
 curves=json.loads((D/"training-curves.json").read_text())["curves"];fig,ax=plt.subplots(2,2,figsize=(11,7),sharex=True)
 for a,seed in zip(ax.flat,(1977,8173,27182,31415)):
  for m,color in(("TD_plain","#2166ac"),("TD_q2","#b2182b")):
   g=curves[str((seed,m))];a.plot([r["paid_nodes"]/1e6 for r in g],[r["changing_data_loss"]if r["changing_data_loss"]is not None else float("nan")for r in g],color=color,lw=.8,label=m);a.set_title(str(seed));a.set_ylabel("Episode training loss");a.grid(alpha=.15)
 ax[0,0].legend();ax[1,0].set_xlabel("Cumulative ALL paid nodes (millions)");ax[1,1].set_xlabel("Cumulative ALL paid nodes (millions)");fig.suptitle("All closed training episodes; changing data, not held-out accuracy");fig.tight_layout();fig.savefig(E/"training-loss.png",dpi=160);plt.close(fig)
 h=json.loads(Path("results/dev_aux/task2579/summary.json").read_text());fig,ax=plt.subplots(1,2,figsize=(10,4),sharey=True)
 for a,o in zip(ax,foes):
  names=["initial|q2","TD_plain|q2","TD_q2|q2"];x=list(range(3))
  vals=[h["absolute_WLD"][m+"/"+o]["W_minus_L_bounds"]for m in names]
  a.bar(x,[(v[0]+v[1])/2 for v in vals],color=["#999999","#2166ac","#b2182b"]);a.vlines(x,[v[0]for v in vals],[v[1]for v in vals],color="black");a.axhline(0,color="black",lw=.7);a.set_xticks(x,["initial","plain TRAIN","q2 TRAIN"]);a.set_title(o+" / fixed q2 foe");a.set_ylabel("Actual W-L mean");a.set_ylim(-1,1);a.grid(axis="y",alpha=.15)
 fig.suptitle("Same q2 candidate and fixed q2 opponents for every price\nNew roots; cross-panel difference is not a causal opponent-policy ablation",fontsize=10);fig.tight_layout();fig.savefig(E/"fixed-q2-foes.png",dpi=160);plt.close(fig)
 print("Wrote4standalone scientific figures; requireactualpixelinspection.")
if __name__=="__main__":run()
