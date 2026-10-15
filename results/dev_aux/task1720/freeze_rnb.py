"""NEW no-Pawn cooperative R/N/B closed-domain learning freeze."""
from pathlib import Path
import json,random,importlib.util,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1737';O.mkdir(exist_ok=False);p=json.loads((R/'results/dev_aux/task1729/plan.json').read_bytes())
sp=importlib.util.spec_from_file_location('T',R/p['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
def spatial(s,rot,flip,sw):
 q=['.']*64
 for i,v in enumerate(s[:-1]):
  x,y=i%8,i//8
  if flip:x=7-x
  for _ in range(rot):x,y=7-y,x
  q[x+8*y]=v.swapcase() if sw else v
 return tuple(q+[1-s[-1] if sw else s[-1]])
rng=random.Random(2026701531);families=[];seen=set();attempts=0
while len(families)<80:
 attempts+=1;s=['.']*64
 for i,v in zip(rng.sample(range(64),8),'KkRNBrnb'):s[i]=v
 s=tuple(s+[0])
 if not T.valid(s) or T.attacked(s,T.king(s,0),1):continue
 kd=max(abs(T.king(s,0)%8-T.king(s,1)%8),abs(T.king(s,0)//8-T.king(s,1)//8))
 if not 2<=kd<=4:continue
 ll=T.moves(s)
 if len(ll)<4 or any(not T.moves(t) and T.attacked(t,T.king(t,t[-1]),1-t[-1]) for u,t in ll):continue
 def get(u,j):return ord(u[j])-97+8*(int(u[j+1])-1)
 if not any(s[get(u,2)]!='.' and s[get(u,0)].upper()!='K' for u,t in ll) or not any(s[get(u,2)]=='.' and s[get(u,0)].upper()!='K' for u,t in ll):continue
 oo=sorted({spatial(s,r,f,sw) for r in range(4) for f in (0,1) for sw in (0,1)})
 if set(oo)&seen:continue
 seen.update(oo);s=rng.choice([z for z in oo if z[-1]==0]);other=spatial(s,0,0,1);f=len(families)
 assert all(T.valid(z) and sorted(p.upper() for p in z[:-1] if p!='.')==sorted('KKRRNNBB') for z in oo)
 families.append(dict(family=f,phase='TRAIN' if f<32 else 'DEV',roots=[s,other],orbit_states=oo,stock='RNBrnb',train_subcohort=1 if f<16 else 2 if f<32 else None))
prices=[(r,720,b,720) for r in (360,720,1440,1728) for b in (360,720,1440)];names={str(q):'aux53rnb_'+'_'.join(map(str,q)) for q in prices};ini=(R/'results/dev_aux/task1688/variant.ini').read_text()
for q,n in names.items():
 import ast
 r,nv,b,pv=ast.literal_eval(q);v=f'p:{pv} n:{nv} b:{b} r:{r} q:1664';ini+=f'\n[{n}:aux_pawn8]\npieceValueMg = {v}\npieceValueEg = {v}\n'
(O/'variant.ini').write_text(ini,encoding='ascii')
prng=random.Random(2026701532);rr=prng.sample([360,720,1440,1728],3);bb=prng.sample([360,720,1440],3);initials=[[r,720,b,720] for r,b in zip(rr,bb)]
p.update(status='FROZEN_NEW_RNB_COOPERATIVE_LATIN_INITIAL_LEARNING',families=families,attempts=attempts,seed=2026701531,root_exclusions=[],root_kind='EIGHTACTOR_RNB',symmetry='D4_COLOR_16',prices=prices,active_coordinates=[0,2],initial_prices=initials,initial_seed=2026701532,initial_scheme='Latin3: independentwithout-replacementRlevels3of4,Bpermutationall3, paired; predefinedcoverage, not3iidinitials.',variant_ini='results/dev_aux/task1737/variant.ini',variant_sha256=hashlib.sha256((O/'variant.ini').read_bytes()).hexdigest(),variant_names=names,seconds_cap=1200,max_go=50000,expected_seconds=600,rootlaw='Closed no-Pawn KkRNBrnb8actors, bothplayersR/N/B. Captureonly meansnoPawncanemerge, no promotion/drop/history. Candidateuncheck,kingsCheby2..4,>=4legalchoices andnonkingcapture+quiet,noimmediatewinmate. Prices/WDL blind, complete16D4+color rootorbits excludedacrossTRAIN32/DEV48. Bothrootscolor-exchange atsamegeometry. Continuationsmayoverlap.',selector='ActualthreeLatininitialadjacentR/Bpaths onshared32TRAIN, integernetW-L bothfixedopponents/colors, max6rounds strictincrease/lex ties/no neutralbridge. DEV ONLYendpoints+unit. Nohumanreferencefit orfullgridoptimum claim.',objective='Can a closed three-piece-type cooperative game learn meaningful R/B relativeN cheaply fromactualWDL? Differentstock androotlaw fromRNP, NOTcausalpromotioncomparison. ThisdoesnotintroducePawndrops/Shogi/Genericdomain claims.',feasibility_advance_condition='Changedstock hypothesis motivatedbyRNPpositiveconditionalWDL buthighP; nohumanpricesread. All12priceprofilesmax1536TRAINgames plus<=768DEV atH96, bound1200s/50000newgo; noautomaticbudgetextension.',selector_kind='ADAPTIVE_GRID_LATIN_THREE')
(O/'plan.json').write_text(json.dumps(p,indent=2));print('FROZEN_RNB',len(families),attempts,initials)

