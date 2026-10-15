from pathlib import Path
import json,importlib.util,random,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1727';O.mkdir(exist_ok=False)
p=json.loads((R/'results/dev_aux/task1719/plan.json').read_bytes());sp=importlib.util.spec_from_file_location('T',R/p['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
def frame(s,fx,sw):
 q=['.']*64
 for i,v in enumerate(s[:-1]):q[(7-i%8 if fx else i%8)+8*(7-i//8 if sw else i//8)]=v.swapcase() if sw else v
 return tuple(q+[1-s[-1] if sw else s[-1]])
rng=random.Random(2026701511);families=[];seen=set();attempts=0
while len(families)<16:
 attempts+=1;s=['.']*64
 for i,v in zip(rng.sample(range(64),8),'KkRNPrnp'):s[i]=v
 s=tuple(s+[0])
 if not T.valid(s) or T.attacked(s,T.king(s,0),1):continue
 kd=max(abs(T.king(s,0)%8-T.king(s,1)%8),abs(T.king(s,0)//8-T.king(s,1)//8))
 if not 2<=kd<=4:continue
 ll=T.moves(s)
 if len(ll)<4 or any(not T.moves(t) and T.attacked(t,T.king(t,t[-1]),1-t[-1]) for u,t in ll):continue
 def dest(u):return ord(u[2])-97+8*(int(u[3])-1)
 def orig(u):return ord(u[0])-97+8*(int(u[1])-1)
 captures=[u for u,t in ll if s[dest(u)]!='.' and s[orig(u)].upper()!='K']
 quiet=[u for u,t in ll if s[dest(u)]=='.' and s[orig(u)].upper()!='K']
 if not captures or not quiet:continue
 oo=sorted({frame(s,fx,sw) for fx in (0,1) for sw in (0,1)})
 if set(oo)&seen:continue
 seen.update(oo);s=rng.choice([v for v in oo if v[-1]==0]);families.append(dict(family=len(families),phase='PILOT',roots=[s,frame(s,0,1)],orbit_states=oo,stock='RNPrnp'))
fixed=json.loads((R/'results/dev_aux/task1723/selection.json').read_bytes())['selected']['POOLED']
p.update(status='FROZEN_NEW8ACTOR_EXCHANGE_FEASIBILITY_BEFORE_QUERY',families=families,attempts=attempts,seed=2026701511,root_exclusions=[],root_kind='EIGHTACTOR_EXCHANGE',rootlaw='8x8 initialKkRNPrnp, bothplayers3nonkings. Candidateuncheck, KingsCheby2..4, >=4legalchoices including nonking capture and nonkingquiet, noimmediatewinningmate. NoWDL/price/rootresultfilter. Full4Pawnframesphaseunique. Thischangesinventory+rootlaw, notisolatedcausalstockcomparison.',fixed_profiles=[p['baseline'],fixed,[1440,720,720,360]],selection_source='Fixedexisting53POOLED TRAINonly plusprevious52fixed4TRAIN andunit; noPILOTwinner/learning',selector='Feasibilitypilot only; no price selection on pilot outcomes. All16families,2colors,2fixedopponents,3frozenprofiles=192games.',seconds_cap=600,max_go=12000,expected_seconds=90,objective='Structural test whether more actual exchanges/cooperation give more physical WDL within H96 cheaply; not train improvement or definitive inventorycausality.',feasibility_advance_condition='Consider a NEW independentlyfrozen training cohort onlyif pooled physicalmate+stalemate fraction>=.25, UNKNOWN fraction<=.10 and actualnewgo/games<=100. Keepall outcomes evenifconditionfails; no automatic horizon extension.')
(O/'plan.json').write_text(json.dumps(p,indent=2));print('FROZEN_EIGHTACTOR',len(families),attempts,fixed)

