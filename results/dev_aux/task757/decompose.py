import json,hashlib,collections
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task757'
for n in [745,751,756]:assert json.loads((R/f'results/dev_aux/task{n}/result.json').read_bytes())['status'].startswith('PASS_ALL_')
by={};hashes={}
for task,label in [(744,'A'),(750,'B'),(755,'other')]:
 p=R/f'results/dev_aux/task{task}';r=json.loads((p/'result.json').read_bytes());gs=[json.loads(t) for t in (p/'games.jsonl').open(encoding='utf-8')];hashes[str(task)]=hashlib.sha256((p/'games.jsonl').read_bytes()).hexdigest()
 for row in r['rows']:
  gg=[gs[x['line']-1] for x in row['batch']['sources']]
  for name in row['names']:by[(label,name)]=gg
rows=[]
def state(g,cap):
 if len(g['actions'])<=cap and not g['termination']['kind'].startswith('cap'):
  w=g['termination']['winner'];return 'true_draw' if w is None else 'true_win' if w==g['color'] else 'true_loss'
 q=g['quantity12'] if cap==12 else g['quantity24'];return 'unfinished_more' if q>0 else 'unfinished_less' if q<0 else 'unfinished_equal'
def real(s):return (s=='true_win')-(s=='true_loss')
def proxy(s):return (s=='unfinished_more')-(s=='unfinished_less')
for opp in ['unit','other_random2514']:
 for method in ['A','B']:
  for start in ['unit','random2514']:
   aa=by[(method if opp=='unit' else 'other',start+'-initial')];bb=by[(method, start+'-endpoint')] if opp=='unit' else by[('other',method+'-'+start+'-endpoint')];assert len(aa)==len(bb)==16 and [(g['root'],g['color']) for g in aa]==[(g['root'],g['color']) for g in bb]
   for cap in [12,24]:
    pairs=[(state(a,cap),state(b,cap)) for a,b in zip(aa,bb)];rd=[real(y)-real(x) for x,y in pairs];pd=[proxy(y)-proxy(x) for x,y in pairs];total=[real(y)+proxy(y)-real(x)-proxy(x) for x,y in pairs];assert all(r+p==t for r,p,t in zip(rd,pd,total));masked=[]
    for i,(x,y) in enumerate(pairs):
     if (x=='unfinished_less' and y=='true_loss') or (x=='true_win' and y=='unfinished_more'):masked.append(dict(family=aa[i]['root']['source_family'],color=aa[i]['color'],before=x,after=y,scalar_delta=total[i],real_delta=rd[i],proxy_delta=pd[i]));assert total[i]==0
    rows.append(dict(opponent=opp,method=method,start=start,cap=cap,cells=16,real_terminal_contribution=str(F(sum(rd),16)),unfinished_proxy_contribution=str(F(sum(pd),16)),literal_sign_total=str(F(sum(total),16)),initial_counts=dict(collections.Counter(x for x,y in pairs)),endpoint_counts=dict(collections.Counter(y for x,y in pairs)),state_pairs=[dict(family=a['root']['source_family'],color=a['color'],before=x,after=y,real_delta=r,proxy_delta=p,scalar_delta=t) for a,(x,y),r,p,t in zip(aa,pairs,rd,pd,total)],entering_true_loss=sum(x!='true_loss' and y=='true_loss' for x,y in pairs),leaving_true_loss=sum(x=='true_loss' and y!='true_loss' for x,y in pairs),scalar_masked_terminal_damage=masked))
out=dict(status='ALL256_SIXSTATE_PAIR_DECOMPOSITIONS_EXACT',rows=rows,source_sha256=hashes,new_go=0,scope='752Dot postA/exploratory/preB diagnostic appliedALL16devcells/2starts/2methods/2opponents/2horizons. Classificationterminal-first perstate NOTaggregatelexicographicpriority; scalar+1truewin andproxyplus collide. Exactsignsumdecomp checked, Bmagnitude actualfitness isdistinct andnotreplaced. Root/opponent family dependence andsparse trueoutcomes retained; no completeWDL/pricecopy/humanvalues/modelselection claims.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(opponent=x['opponent'],method=x['method'],start=x['start'],cap=x['cap'],real=x['real_terminal_contribution'],proxy=x['unfinished_proxy_contribution'],sign=x['literal_sign_total'],enterloss=x['entering_true_loss'],leaveloss=x['leaving_true_loss'],masked=len(x['scalar_masked_terminal_damage'])) for x in rows]))
