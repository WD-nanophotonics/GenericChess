"""Freeze actual two-random-grid-initial local learning on NEW exchange roots."""
from pathlib import Path
import json,random,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1729';O.mkdir(exist_ok=False);pilot=json.loads((R/'results/dev_aux/task1728/result.json').read_bytes());assert pilot['advance_predeclared_feasibility']
p=json.loads((R/'results/dev_aux/task1727/plan.json').read_bytes());sp=importlib.util.spec_from_file_location('T',R/p['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
def frame(s,fx,sw):
 q=['.']*64
 for i,v in enumerate(s[:-1]):q[(7-i%8 if fx else i%8)+8*(7-i//8 if sw else i//8)]=v.swapcase() if sw else v
 return tuple(q+[1-s[-1] if sw else s[-1]])
rng=random.Random(2026701521);families=[];seen={tuple(s) for f in p['families'] for s in f['orbit_states']};attempts=0
while len(families)<80:
 attempts+=1;s=['.']*64
 for i,v in zip(rng.sample(range(64),8),'KkRNPrnp'):s[i]=v
 s=tuple(s+[0])
 if not T.valid(s) or T.attacked(s,T.king(s,0),1):continue
 kd=max(abs(T.king(s,0)%8-T.king(s,1)%8),abs(T.king(s,0)//8-T.king(s,1)//8))
 if not 2<=kd<=4:continue
 ll=T.moves(s)
 if len(ll)<4 or any(not T.moves(t) and T.attacked(t,T.king(t,t[-1]),1-t[-1]) for u,t in ll):continue
 captures=[];quiet=[]
 for u,t in ll:
  a=ord(u[0])-97+8*(int(u[1])-1);b=ord(u[2])-97+8*(int(u[3])-1)
  if s[a].upper()=='K':continue
  (captures if s[b]!='.' else quiet).append(u)
 if not captures or not quiet:continue
 oo=sorted({frame(s,fx,sw) for fx in (0,1) for sw in (0,1)})
 if set(oo)&seen:continue
 seen.update(oo);s=rng.choice([v for v in oo if v[-1]==0]);f=len(families);families.append(dict(family=f,phase='TRAIN' if f<32 else 'DEV',roots=[s,frame(s,0,1)],orbit_states=oo,stock='RNPrnp',train_subcohort=1 if f<16 else 2 if f<32 else None))
prng=random.Random(2026701522);initials=prng.sample(p['prices'],2)
p.update(status='FROZEN_EXCHANGE_TWO_RANDOM_GRID_INITIAL_LEARNING_BEFORE_QUERY',families=families,attempts=attempts,seed=2026701521,root_exclusions=[1727],fixed_profiles=[],initial_prices=initials,initial_seed=2026701522,selector_kind='ADAPTIVE_GRID_TWO_INITIAL',max_rounds=6,selector='Evaluateunit andbothrandomgridinitials onshared32TRAINfamilies. At each round evaluateALLone-coordinate-adjacentgridneighbors, accepthighestINTEGERsumW-L iffstrictincrease, lexprice tie; stoplocalplateau or6rounds. No neutralbridge. Maincandidate bestendpoint TRAINintegernet thenlex. DEV endpoints+unit only. Bothpathsareactualadaptiveevaluation, cachedsharedpaidchoices; notglobalgridoptimumifunevaluatedcells.',seconds_cap=1200,max_go=45000,expected_seconds=480,objective='Does new cooperative/exchange rootlaw +globallyalignedmature search yield actualrandom-grid-initial convergence andfreshDEVactualWDL? N/B720anchor,R/Ponly; nohumanpricefit. Sameopmixture/depth/H96, no quantityreward.',feasibility_advance_condition='Pilot1728 64/192 physicalmate,0UNKNOWN,23.67go/game passed frozen feasibility. This newindependentcohort excludespilotfullframes, nottestextension orpilotwinner selection.')
(O/'plan.json').write_text(json.dumps(p,indent=2));print('FROZEN_ADAPTIVE',len(families),attempts,initials)

