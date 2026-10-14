from pathlib import Path
import json,collections,random,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1665';O.mkdir(exist_ok=False);sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);cache={};counts=collections.Counter()
for folder in ['task1631','task1634','task1641','task1644','task1652','task1661','task1667','task1664']:
 for p in (R/f'results/dev_aux/{folder}').glob('*choices.jsonl'):
  for line in p.open():
   x=json.loads(line);k=tuple(x['price']),tuple(x['state']);assert T.fen(k[1])==x['position'] and x['move'] in dict(T.moves(k[1]))
   if k in cache:assert cache[k]==x['move']
   cache[k]=x['move']
   if folder=='task1664':
    counts['newgo']+=1
    for info in x['uci_info']:
     a=info.split()
     if 'pv' in a:
      q=k[1]
      for u in a[a.index('pv')+1:]:q=dict(T.moves(q))[u];counts['PVmoves']+=1
plan=json.loads((R/'results/dev_aux/task1663/plan.json').read_bytes());families={f['family']:f for f in plan['family_subset']};proof=json.loads((R/'results/dev_aux/task1649/result.json').read_bytes());slots=proof['slots'];safe=set(proof['proved_no_mate_masks']);groups=collections.defaultdict(list)
for line in (R/'results/dev_aux/task1664/games.jsonl').open():
 x=json.loads(line);p=tuple(x['price']);s=tuple(families[x['family']]['roots'][x['color_index']]);c=s[8];rng=random.Random(2026678600+x['family']*100+x['seed'])
 for step in x['trajectory']:
  assert tuple(step['state'])==s;ll=T.moves(s);u=rng.random();assert u==step['uniform'] and step['move']==((cache[p,s] if len(ll)>1 else ll[0][0]) if s[8]==c else ll[min(int(u*len(ll)),len(ll)-1)][0]);s=dict(ll)[step['move']];counts['plies']+=1
 assert s==tuple(x['end']);ll=T.moves(s)
 if not ll:pay=(-1 if s[8]==c else 1) if T.attacked(s,s[4*s[8]],1-s[8]) else 0;cat='PHYSICAL_MATE' if pay else 'PHYSICAL_STALE'
 elif sum(1<<i for i,k in enumerate(slots) if s[k]!=16) in safe:pay=0;cat='RULE_NO_MATE_DRAW'
 else:assert len(x['trajectory'])==48;pay=None;cat='UNRESOLVED'
 assert pay==x['payoff'] and cat==x['category'];groups[p].append(x);counts['games']+=1;counts['reused_games']+=int(x.get('reused_game',False))
assert counts['games']==1536 and counts['newgo']==3636 and counts['reused_games']==512
base={(x['family'],x['color_index'],x['seed']):x for x in groups[(1728,720,720)]};contrasts=[]
for p in [(1512,720,720),(2088,720,720)]:
 a=groups[p];differenttrajectory=0;differentpay=0;dd=collections.defaultdict(list)
 for x in a:
  y=base[x['family'],x['color_index'],x['seed']];differenttrajectory+=x['trajectory']!=y['trajectory'];differentpay+=x['payoff']!=y['payoff'];dd[x['family']].append((x['payoff'] or 0)-(y['payoff'] or 0))
 d=[sum(v)/8 for f,v in sorted(dd.items())];contrasts.append({'price':p,'different_full_trajectories':differenttrajectory,'different_payoffs':differentpay,'finite_gain':sum(d)/64,'identical_outcome_vector':not differentpay})
features=plan['features']
def sign(x):return (x>0)-(x<0)
for p in plan['profiles']:
 for a in features:
  for b in features:
   assert sign(sum((x-y)*z for x,y,z in zip(a,b,p)))==sign(sum((x-y)*z for x,y,z in zip(a,b,plan['original'])));counts['leaf_ordering_pairs']+=1
out={'status':'PASS_LEAF_ORDERING_EQUIVALENCE_AND_ACTUAL_PHYSICAL_TRAJECTORIES','counts':dict(counts),'R_open_cell':plan['R_cell_open'],'contrasts':contrasts,'scope':'ThreewidelydifferentR1512/1728/2088 sameall729materialleafrankings/ties; exactsameobservedWDLvector doesnotuniquelyidentifyR. Only64exposedfamilies, noequivalencegeneralization toallNative states. Tree-order proof scopedcompletefixeddepthminimax, selectiveconsumer maydiffer elsewhere.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

