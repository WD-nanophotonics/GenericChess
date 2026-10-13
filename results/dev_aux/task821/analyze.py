import json,hashlib,collections
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task821';O.mkdir(exist_ok=True);assert json.loads((R/'results/dev_aux/task820/result.json').read_bytes())['status']=='PASS_ALL_FROZEN_D_E_F_G_PRICES_CROSSED_BUDGETS';p=R/'results/dev_aux/task819';d=json.loads((R/'results/dev_aux/task818/execution_inputs.json').read_bytes());r=json.loads((p/'result.json').read_bytes());gs={819:[json.loads(x) for x in (p/'games.jsonl').open(encoding='utf-8')],797:[json.loads(x) for x in (O.parent/'task797/games.jsonl').open(encoding='utf-8')]};by={}
for row in r['rows']:
 gg=[gs[int(x['file'].split('/')[-2][4:])][x['line']-1] for x in row['batch']['sources']]
 for name in row['names']:by[(row['nodes'],row['opponent'],row['pool'],name)]=gg

def state(g,h):
 if len(g['actions'])<=h and not g['termination']['kind'].startswith('cap'):
  w=g['termination']['winner'];return 'draw' if w is None else 'win' if w==g['color'] else 'loss'
 q=g['quantity12' if h==12 else 'quantity24'];return 'more' if q>0 else 'less' if q<0 else 'equal'
def real(s):return (s=='win')-(s=='loss')
def proxy(s):return (s=='more')-(s=='less')
def val(g,h,m):
 s=state(g,h);q=F(g['quantity12' if h==12 else 'quantity24'],19)
 if m=='real':return F(real(s))
 if m=='proxy':return F(proxy(s))
 if m=='sign':return F(real(s)+proxy(s))
 if m=='literal':return F(real(s)) if s in ['win','loss','draw'] else q
 if m=='quantity':return q
 return F(25-len(g['actions']),25) if s=='win' else F(-1) if s=='loss' else F(0)
rows=[]
for budget in [256,1024]:
 for pool in ['development','independent_validation']:
  for opp in ['unit','random2514']:
   for start in ['unit','random2514']:
    initial=by[(budget,opp,pool,start+'-initial')];models={m:by[(budget,opp,pool,m+'-'+start+'-endpoint')] for m in ['D','E','F','G']}
    for comp,aa,bb in [(m+'-initial',initial,models[m]) for m in ['D','E','F','G']]+[('D-E',models['E'],models['D']),('F-D',models['D'],models['F']),('G-F',models['F'],models['G'])]:
     assert [(g['root'],g['color']) for g in aa]==[(g['root'],g['color']) for g in bb];families=sorted({g['root']['source_family'] for g in aa});N=len(aa);assert N==2*len(families)
     for h in [12,24]:
      pairs=[(state(a,h),state(b,h)) for a,b in zip(aa,bb)];metrics=[]
      for m in ['real','proxy','sign','literal','quantity','fast']:
       diff=[val(b,h,m)-val(a,h,m) for a,b in zip(aa,bb)];fm=[dict(family=f,gain=str(sum(z for z,g in zip(diff,aa) if g['root']['source_family']==f)/2)) for f in families];loo=[dict(omit=f,gain=str(sum(z for z,g in zip(diff,aa) if g['root']['source_family']!=f)/(N-2))) for f in families];minimum=min(F(x['gain']) for x in loo);metrics.append(dict(metric=m,gain=str(sum(diff)/N),initial_mean=str(sum(val(a,h,m) for a in aa)/N),endpoint_mean=str(sum(val(b,h,m) for b in bb)/N),by_family=fm,leave_one=loo,minimum_leave_one=str(minimum),minimum_families=[x['omit'] for x in loo if F(x['gain'])==minimum],negative_cells=sum(x<0 for x in diff)))
      mm={x['metric']:F(x['gain']) for x in metrics};assert mm['real']+mm['proxy']==mm['sign'];trans=dict(new_win=sum(x!='win' and y=='win' for x,y in pairs),avoided_loss=sum(x=='loss' and y!='loss' for x,y in pairs),lost_win=sum(x=='win' and y!='win' for x,y in pairs),new_loss=sum(x!='loss' and y=='loss' for x,y in pairs));assert F(trans['new_win']+trans['avoided_loss']-trans['lost_win']-trans['new_loss'],N)==mm['real'];rows.append(dict(nodes=budget,pool=pool,opponent=opp,start=start,comparison=comp,cap=h,cells=N,initial_counts=dict(collections.Counter(x for x,y in pairs)),endpoint_counts=dict(collections.Counter(y for x,y in pairs)),transitions=trans,metrics=metrics,state_pairs=[dict(family=g['root']['source_family'],color=g['color'],before=x,after=y) for g,(x,y) in zip(aa,pairs)]))
out=dict(status='ALL_D_E_F_G_CROSSED_BUDGETS_FROZEN_SCORE_SIXSTATE_FAMILY_DELETION',rows=rows,source_sha256={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['games.jsonl','queries.jsonl','price_acks.json','result.json']},new_go=0,reference_read_here=False,scope='FixedH12/H24 ALL8dev/16validationfamilies, twoopponents/twoinitials stratum kept. ALLD/E/F/G-initial,D-E,F-D,G-F allsixstates, win/lossnet exact andwholefamily deletion includingunfinisheddenominator, noendpointselection. Pairedcolors/fixedopponents notindependentfamilies. Leave-one notsignificance/WDLproof. Literalherequantitymagnitude, signseparate, quantityregardlessroyal, fastwin(25-plies)/25 loss-1 onlyterminalatorbeforeH.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(nodes=x['nodes'],pool=x['pool'],opponent=x['opponent'],start=x['start'],comparison=x['comparison'],cap=x['cap'],metrics={m['metric']:m['gain'] for m in x['metrics']},real_loo=next(m['minimum_leave_one'] for m in x['metrics'] if m['metric']=='real')) for x in rows if x['cap']==24]))
