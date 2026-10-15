"""Independent fixed-candidate replication, no learning/selection or old test extension."""
from pathlib import Path
import json,random,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1744';O.mkdir(exist_ok=False);p=json.loads((R/'results/dev_aux/task1729/plan.json').read_bytes());sp=importlib.util.spec_from_file_location('T',R/p['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
def frame(s,fx,sw):
 q=['.']*64
 for i,v in enumerate(s[:-1]):q[(7-i%8 if fx else i%8)+8*(7-i//8 if sw else i//8)]=v.swapcase() if sw else v
 return tuple(q+[1-s[-1] if sw else s[-1]])
rng=random.Random(2026701551);families=[];seen={tuple(s) for old in (1727,1729) for f in json.loads((R/f'results/dev_aux/task{old}/plan.json').read_bytes())['families'] for s in f['orbit_states']};attempts=0
while len(families)<256:
 attempts+=1;s=['.']*64
 for i,v in zip(rng.sample(range(64),8),'KkRNPrnp'):s[i]=v
 s=tuple(s+[0])
 if not T.valid(s) or T.attacked(s,T.king(s,0),1):continue
 kd=max(abs(T.king(s,0)%8-T.king(s,1)%8),abs(T.king(s,0)//8-T.king(s,1)//8))
 if not 2<=kd<=4:continue
 ll=T.moves(s)
 if len(ll)<4 or any(not T.moves(t) and T.attacked(t,T.king(t,t[-1]),1-t[-1]) for u,t in ll):continue
 def get(u,j):return ord(u[j])-97+8*(int(u[j+1])-1)
 if not any(s[get(u,2)]!='.' and s[get(u,0)].upper()!='K' for u,t in ll) or not any(s[get(u,2)]=='.' and s[get(u,0)].upper()!='K' for u,t in ll):continue
 oo=sorted({frame(s,fx,sw) for fx in (0,1) for sw in (0,1)})
 if set(oo)&seen:continue
 seen.update(oo);s=rng.choice([z for z in oo if z[-1]==0]);families.append(dict(family=len(families),phase='REPLICATION',roots=[s,frame(s,0,1)],orbit_states=oo,stock='RNPrnp'))
C=json.loads((R/'results/dev_aux/task1730/selection.json').read_bytes())['selected']['POOLED']
p.update(status='FROZEN_INDEPENDENT_FIXED53C_REPLICATION',families=families,attempts=attempts,seed=2026701551,root_exclusions=[1727,1729],fixed_profiles=[p['baseline'],C],initial_prices=[],selector_kind='FIXED_ONLY',selector='No training/selection. Fixed1730POOLED TRAINcandidate andunit only on256NEWfullframefamilies, bothcolorsandop64/4096,2048games. Primaryfamilypairedmixturegain, secondaryopponentdecomposition. Reportallpositive/negative/UNKNOWN, noresultdrivenextension.',seconds_cap=1200,max_go=65000,expected_seconds=600,objective='Does limitedpositive8actorRNP trueWDLgain replicate on independentlyfrozen roots atsame requestednode/opmix/rules? Notnewhumanpriceproof.',cost_decision='Previous48familygain.083333 CI[.026042,.140625] andpriortransfernegatives justifyonepredeclared256familyfixedcandidate replicate. Positivepersistentgain supportsconditionaluse; null/negative keepsrouteconditional. No furthercohortextension basedonthisresult.')
(O/'plan.json').write_text(json.dumps(p,indent=2));print('FROZEN_REPLICATION',len(families),attempts,C)

