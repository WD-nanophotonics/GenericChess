"""All pre-existing single-coordinate grid edges, paired full TRAIN trajectories."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,itertools,collections
R=Path.cwd();D=R/'results/dev_aux/task1723';O=R/'results/dev_aux/task1726';O.mkdir(exist_ok=False);plan=json.loads((D/'start.json').read_bytes())['plan'];games=[json.loads(l) for l in (D/'games.jsonl').open() if json.loads(l)['phase'].startswith('TRAIN')];prices=sorted(map(tuple,plan['prices']))
gm={(tuple(x['price']),x['family'],x['color'],x['opponent']):x for x in games};edges=[]
for axis,coord in [('R',0),('P',3)]:
 for p,q in itertools.combinations(prices,2):
  if any(p[i]!=q[i] for i in range(4) if i!=coord) or p[coord]==q[coord]:continue
  if any(p[coord]<z[coord]<q[coord] and all(z[i]==p[i] for i in range(4) if i!=coord) for z in prices):continue
  edges.append((axis,p,q))
def events(x):
 out=[]
 for i,z in enumerate(x['trajectory']):
  s=z['state'];u=z['move'];a=ord(u[0])-97+8*(int(u[1])-1);b=ord(u[2])-97+8*(int(u[3])-1)
  if s[b]!='.':out.append(dict(ply=i,actor=s[a],captured=s[b],move=u))
  if len(u)==5:out.append(dict(ply=i,actor=s[a],promotion=u[-1],move=u))
 return out
records=[];buckets=collections.defaultdict(collections.Counter)
for axis,p,q in edges:
 for f in plan['families']:
  if not f['phase'].startswith('TRAIN'):continue
  for color in (0,1):
   for op in plan['opponents']:
    a=gm[p,f['family'],color,op['id']];b=gm[q,f['family'],color,op['id']];aa=a['trajectory'];bb=b['trajectory'];common=0
    while common<min(len(aa),len(bb)) and aa[common]['move']==bb[common]['move']:assert aa[common]['state']==bb[common]['state'];common+=1
    same=common==len(aa)==len(bb);div=None
    if not same:
     assert common<len(aa) and common<len(bb),'one prefix terminal differs under price-independent label?'
     assert aa[common]['state']==bb[common]['state'];div=dict(ply=common,state=aa[common]['state'],low_move=aa[common]['move'],high_move=bb[common]['move'])
    ea=[z for z in events(a) if z['ply']>=common];eb=[z for z in events(b) if z['ply']>=common];pa=a['payoff'];pb=b['payoff'];delta=None if pa is None or pb is None else pb-pa
    x=dict(axis=axis,low=p,high=q,phase=f['phase'],family=f['family'],color=color,opponent=op['id'],same_complete_trajectory=same,first_same_state_divergence=div,postdivergence_low_events=ea,postdivergence_high_events=eb,event_sequences_differ=ea!=eb,low_category=a['category'],high_category=b['category'],low_payoff=pa,high_payoff=pb,delta=delta,lower=b['lower']-a['upper'],upper=b['upper']-a['lower'])
    records.append(x)
    for key in [(axis,f['phase'],op['id']),(axis,'ALL','MIXTURE')]:
     cc=buckets[key];cc['pairs']+=1;cc['same_complete_trajectory']+=same;cc['different_trajectory']+=not same;cc['different_capture_promotion_sequence']+=ea!=eb;cc['improved']+=delta is not None and delta>0;cc['worsened']+=delta is not None and delta<0;cc['same_known_WDL']+=delta==0;cc['involves_UNKNOWN']+=delta is None;cc['different_trajectory_both_proved_Draw']+=not same and pa==pb==0;cc['delta_sum']+=delta or 0;cc['lower_sum']+=x['lower'];cc['upper_sum']+=x['upper']
(O/'pairs.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in records))
summary=[dict(axis=k[0],phase=k[1],opponent=k[2],**v,mean_gain=v['delta_sum']/v['pairs'],gain_bounds=[v['lower_sum']/v['pairs'],v['upper_sum']/v['pairs']]) for k,v in buckets.items()]
out=dict(status='COMPLETE_ALL_R_ONLY_P_ONLY_ADJACENT_EDGES_NO_NEW_GO',edge_count=len(edges),edges=edges,pair_count=len(records),summary=summary,actual_native_go=0,interpretation='Posthoc TRAIN mechanism diagnostic requested by Dot. Low-to-high sign is coordinate effect, not improvement expectation. Every frozen root retained. Across edges/roles/opponents observations dependent; aggregate mean not independent N, no parameter freezing or DEV fit based solely on absence.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

