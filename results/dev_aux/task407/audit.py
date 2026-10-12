import sys,json,random,math,hashlib,time,re
from pathlib import Path
from fractions import Fraction
import cshogi as C
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
O=R/'results/dev_aux/task407';O.mkdir(exist_ok=True);D=R/'results/dev_aux/task405/declaration.json';d=json.loads(D.read_text(encoding='utf-8'));t0=time.monotonic();axes=d['axes'];rootchecks=[]
for f in d['roots']:
 b=C.Board(f['initial_sfen']);rng=random.Random(f['seed']);states=[' '.join(b.sfen().split()[:3])];movers=[];checks=[]
 for u in f['history']:
  assert V.terminal(b,states,movers,checks) is None
  legal=sorted(C.move_to_usi(m) for m in b.legal_moves);assert rng.choice(legal)==u,(f['seed'],u);m=b.move_from_usi(u);assert b.is_legal(m);movers.append(b.turn);b.push(m);checks.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]))
 assert V.terminal(b,states,movers,checks) is None and b.sfen()==f['expected_sfen'];rootchecks.append(dict(seed=f['seed'],phase=f['phase'],legal_prefix_plies=len(f['history'])))
rng=random.Random(d['direction_seed']);assert d['directions']=={p['name']:[[rng.choice([-1,1]) for a in axes] for _ in range(24)] for p in d['initial_profiles']}
partial='--partial' in sys.argv;ep=R/'results/dev_aux/task406'/('progress.json' if partial else 'endpoints.json');e=json.loads(ep.read_text(encoding='utf-8'));games=[json.loads(x) for x in (R/'results/dev_aux/task406/games.jsonl').read_text(encoding='utf-8').splitlines()];batchchecks=0
train=[f for f in d['roots'] if f['phase']=='train']
def batch(row):
 global batchchecks
 gs=[games[s['line']-1] for s in row['sources']];assert len(gs)==8;assert [(g['root'],g['color']) for g in gs]==[(f,c) for f in train for c in [0,1]]
 assert all(g['weights']==row['weights'] for g in gs);goals=[Fraction(g['goal']) for g in gs];assert row['goals']==[str(x) for x in goals] and Fraction(row['mean_goal'])==sum(goals)/8;assert Fraction(row['mean_quantity'])==sum(Fraction(g['raw_quantity']) for g in gs)/8;batchchecks+=1;return gs
for family in [p['name'] for p in d['initial_profiles']]:
 start=next(p['weights'] for p in d['initial_profiles'] if p['name']==family)
 for rr in [r for r in e['rounds'] if r['family']==family]:
  assert rr['start_weights']==start;expected=[('base',list(start))]
  for a in axes:
   for mode in ['half','double']:
    w=list(start);w[a]=max(32,min(4096,(w[a]+1)//2 if mode=='half' else w[a]*2));expected.append((str(a)+'-'+mode,w))
  assert [(r['label'],r['weights']) for r in rr['candidates']]==expected
  for row in rr['candidates']:batch(row)
  scores=[Fraction(r['mean_goal']) for r in rr['candidates']];best=max(range(25),key=lambda i:scores[i]);assert rr['selected_index']==best and Fraction(rr['strict_gain'])==scores[best]-scores[0];start=rr['candidates'][best]['weights']
 for endpoint in [x for x in e.get('endpoints',[]) if x['family']==family and x['method']=='coordinate']:assert endpoint['endpoint']==start
updates=[]
for p in d['initial_profiles']:
 w=list(p['weights']);last_mean=None
 for u in [x for x in e['updates'] if x['family']==p['name']]:
  i=u['iteration'];direction=d['directions'][p['name']][i];assert u['direction']==direction and u['start_weights']==w
  plus=list(w);minus=list(w)
  for axis,sign in zip(axes,direction):
   plus[axis]=max(32,min(4096,math.floor(w[axis]*math.exp(.25*sign)+.5)))
   minus[axis]=max(32,min(4096,math.floor(w[axis]*math.exp(-.25*sign)+.5)))
  cs=u['candidates'];assert [x['weights'] for x in cs]==[w,plus,minus]
  for row in cs:batch(row)
  scores=[Fraction(row['mean_goal']) for row in cs];best=max(range(3),key=lambda j:scores[j]);gain=scores[best]-scores[0];assert u['selected_index']==best and Fraction(u['accepted_strict_gain'])==gain;new=cs[best]['weights']
  changed=sum(w[axis]!=new[axis] for axis in axes);assert changed==u['changed_integer_axes'] and u['after_weights']==new;assert last_mean is None or scores[0]==last_mean
  updates.append(dict(family=p['name'],iteration=i,accepted=best!=0,accepted_gain=str(gain),changed_integer_axes=changed,before_integer=w,after_integer=new,mean_before=str(scores[0]),mean_after=str(scores[best])));w=new;last_mean=scores[best]
 if not partial:assert len([u for u in e['updates'] if u['family']==p['name']])==24 and next(x for x in e['endpoints'] if x['family']==p['name'] and x['method']=='joint')['endpoint']==w
ackchecks=0
if not partial:
 acks=json.loads((R/'results/dev_aux/task406/price_acks.json').read_text(encoding='utf-8'))
 for a in acks:
  vals=[]
  for line in a['prices']:
   if not line.startswith('info string auxprice '):continue
   pc,value,signed,capture,promotion=map(int,line.split()[3:]);pt=pc%16;base=pt-8 if 9<=pt<=14 else pt;w=a['weights'];assert value==w[pt] and signed==(1 if pc<16 else -1)*w[pt] and capture==(0 if pt in (0,8,15) else w[pt]+w[base]) and promotion==(w[base+8]-w[base] if 1<=base<=6 else 0),(line,w);vals.append(pc)
  assert sorted(vals)==list(range(32));ackchecks+=32
summary=[]
for p in d['initial_profiles']:
 us=[u for u in updates if u['family']==p['name']];summary.append(dict(family=p['name'],iterations=len(us),accepted_steps=sum(u['accepted'] for u in us),integer_flat_steps=sum(u['changed_integer_axes']==0 for u in us),changed_axes_per_iteration=[u['changed_integer_axes'] for u in us],last_integer=us[-1]['after_integer'] if us else p['weights']))
result=dict(status='PARTIAL_PASS' if partial else 'PASS',roots=rootchecks,batches_checked=batchchecks,price_ack_entries=ackchecks,updates=updates,summary=summary,seconds=time.monotonic()-t0,declaration_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),scope='independentcshogi generator/exactarithmetic/resource refs; noendoutcomes/H/gainchoice; no uniquely identifiedoptimizercoverage explanation')
(O/('partial.json' if partial else 'result.json')).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['updates','roots']}))