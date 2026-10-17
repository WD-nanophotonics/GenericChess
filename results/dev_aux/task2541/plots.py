"""Static scientific figures of every initialization and actual utility bounds."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path('results/dev_aux/task2541')
def run():
 d=json.loads((O/'diagnostics.json').read_text());rows=d['rows'];colors=['#0072B2','#D55E00','#009E73','#CC79A7'];seeds=[1977,8173,27182,31415];labels=['board P','board A','board X','hand A','hand P','hand X'];files=[]
 for g in sorted({r['rule']for r in rows}):
  fig,axes=plt.subplots(2,3,figsize=(12,6.5),sharex=True)
  for j,ax in enumerate(axes.flat):
   for r in rows:
    if r['rule']!=g:continue
    points=[dict(nodes=0,weights=r['initial'])]+r['path'];ax.plot([x['nodes']/1000 for x in points],[x['weights'][j]for x in points],color=colors[seeds.index(r['seed'])],linestyle='-'if r['method']=='TD'else'--',linewidth=1.1,label=str(r['seed'])+' '+r['method'])
   ax.axhline(0,color='.6',lw=.5);ax.set_title(labels[j]);ax.grid(alpha=.18);ax.set_xlabel('All paid search nodes (thousands)');ax.set_ylabel('Raw coefficient')
  handles,ls=axes[0,0].get_legend_handles_labels();fig.legend(handles,ls,loc='lower center',ncol=4,fontsize=8);fig.suptitle(f'Rule {g}: ALL initializations, TD solid / paid WDL dashed\nNo normalization or human target; training path is not a strength curve',fontsize=11);fig.tight_layout(rect=(0,.08,1,.91));name=f'weights-{g}.png';fig.savefig(O/name,dpi=135);plt.close(fig);files.append(name)
 fig,axes=plt.subplots(2,2,figsize=(11,6),sharex=True)
 for ax,g in zip(axes.flat,sorted({r['rule']for r in rows})):
  for r in rows:
   if r['rule']==g and r['method']=='TD':
    bb=r['TDloss_node_bins'];ax.plot([x['closed_game_node_bin'][1]/1000 for x in bb],[x['mean_half_squared_TD_error']for x in bb],marker='o',ms=3,color=colors[seeds.index(r['seed'])],label=str(r['seed']))
  ax.set_title('Rule '+str(g));ax.set_xlabel('Paid node-bin upper edge (thousands)');ax.set_ylabel('Mean half-squared TD error');ax.grid(alpha=.18)
 handles,ls=axes[0,0].get_legend_handles_labels();fig.legend(handles,ls,loc='lower center',ncol=4,fontsize=8);fig.suptitle('ALL TD initializations: training error in closed-game paid-node bins\nDifferent roots/targets across bins; not stationary test loss or proof of stronger play',fontsize=11);fig.tight_layout(rect=(0,.06,1,.9));fig.savefig(O/'training-loss.png',dpi=140);plt.close(fig);files.append('training-loss.png')
 e=json.loads((O/'evaluation-audit.json').read_text());foes=['uniform','random99031'];fig,axes=plt.subplots(1,2,figsize=(12,5.5),sharex=True)
 for ax,foe in zip(axes,foes):
  labels2=[];k=0
  for treatment,base in [('TD','initial'),('WDL','initial'),('TD','WDL')]:
   r=next(r for r in e['contrasts']if r['foe']==foe and r['treatment']==treatment and r['base']==base);lo,hi=r['bounds'];ci=r['descriptive_95'];ax.hlines(k,*ci,color='.75',linewidth=5);ax.hlines(k,lo,hi,color='#0072B2',linewidth=3);ax.plot([lo,hi],[k,k],'|',color='#0072B2');labels2.append(treatment+' minus '+base);k+=1
  ax.set_yticks(range(3),labels2);ax.axvline(0,color='black',lw=.8);ax.set_title('Fixed foe: '+foe);ax.grid(axis='x',alpha=.2);ax.set_xlabel('Actual candidate W-L difference (U/missing bounded)');ax.invert_yaxis()
 fig.suptitle('Shared NEW finite validation: ALL rules / initials / families / both roles\nBlue: utility bounds. Grey: descriptive crossed-resampling envelope, not guaranteed CI.',fontsize=11);fig.tight_layout(rect=(0,0,1,.9));fig.savefig(O/'actual-strength.png',dpi=140);plt.close(fig);files.append('actual-strength.png')
 fig,axes=plt.subplots(1,2,figsize=(12,6.5));ys=list(range(len(rows)));labs=[f"{r['rule']} / {r['seed']} / {r['method']}"for r in rows];cs=['#0072B2'if r['method']=='TD'else'#D55E00'for r in rows]
 for ax,field,title in zip(axes,['seconds','games'],['Per-arm measured wall seconds','Paid training games']):
  ax.barh(ys,[r[field]for r in rows],color=cs);ax.set_yticks(ys,labs,fontsize=6);ax.invert_yaxis();ax.set_title(title);ax.grid(axis='x',alpha=.18)
 fig.suptitle('Same node ceiling; wall/sample counts are outcomes, not controlled speedup\nBlue TD, orange paid WDL; every initialization retained',fontsize=11);fig.tight_layout(rect=(0,0,1,.91));fig.savefig(O/'paid-costs.png',dpi=145);plt.close(fig);files.append('paid-costs.png');print(json.dumps(files))
if __name__=='__main__':run()
