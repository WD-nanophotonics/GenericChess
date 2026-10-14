from pathlib import Path
import json,random,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1633';O.mkdir(exist_ok=False);sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);old=json.loads((R/'results/dev_aux/task1630/plan.json').read_bytes());seen={min(tuple(s) for s in f['orbit_states']) for f in old['families']};rng=random.Random(2026678600);families=[];attempts=0;pairs=[(1,2,7),(1,3,6),(2,3,5)]
def orbit(s):
 out=[]
 for swap in [False,True]:
  for fx in [False,True]:
   for fy in [False,True]:
    a=[]
    for z in s[:8]:
     if z==16:a.append(16);continue
     x,y=z%4,z//4
     if swap:x,y=y,x
     a.append((3-x if fx else x)+4*(3-y if fy else y))
    out.extend([tuple(a+[s[8]]),tuple(a[4:]+a[:4]+[1-s[8]])])
 return sorted(set(out))
while len(families)<128:
 attempts+=1;f=len(families);a,b,c=pairs[f%3];positions=rng.sample(range(16),5);s=[16]*8
 for i,p in zip([0,4,a,b,c],positions):s[i]=p
 s=tuple(s+[0])
 if max(abs(s[0]%4-s[4]%4),abs(s[0]//4-s[4]//4))>2 or not T.valid(s) or not T.attacked(s,s[0],1):continue
 ll=T.moves(s)
 if len(ll)<2 or any(not T.moves(t) and T.attacked(t,t[4*t[8]],1-t[8]) for u,t in ll):continue
 oo=orbit(s);key=min(oo)
 if key in seen:continue
 seen.add(key);q=rng.choice([t for t in oo if t[8]==0]);other=tuple(q[4:8]+q[:4]+(1-q[8],));families.append({'family':f,'phase':'TRAIN' if f<64 else 'DEV','stock':['RNvsB','RBvsN','NBvsR'][f%3],'orbit_states':oo,'roots':[q,other]})
plan={'status':'FROZEN_NEW_ROOTS_BEFORE_GAME_LEARNING','families':families,'seed':2026678600,'attempts':attempts,'rootlaw':old['rootlaw'],'R_grid':[360,720,1440,1728],'B_grid':[360,720,1440],'N':720,'nodes':64,'handoff_horizon_plies':24,'TRAIN_seeds_per_color':2,'DEV_seeds_per_color':4,'primary_selector':'MaximumTRAINmeanlower=(knownWin-knownLoss-UNRESOLVED)/N; lowerlexR,B ties. UNRESOLVEDisnotLosslabel orDraw. NoDEVselection/humanfit.','secondary_H48':'First16DEVfamilies, baseline720720 andfixedC501440720 only,4seeds/color, horizon48 predeclared, do notchoosebest horizon.','pilot_diagnostic':'Previous16PILOTfamilies baseline/C50,4seeds/color,H24; fixedpolicies, compareknown realizedpayoffs againstcertifiedALLlower bounds, nottraining ornewholdout.','opponent':'Uniformlegalrandomuntilfirstcapture, thenBOTHperfect4rulepolicy. Candidateactualcold64untilcapture. NOTpurematurevsrandomwholegame.','labels':'Physicalrulemate/stale atanyply; otherwisefirstcapture<=H gets exactinfinite4WDL; atH unresolved keeps[-1,+1]bounds, noquantity/matescore reward.','expected_seconds':180,'single_seconds':600,'max_physical_go':70000,'binary':old['binary'],'binary_sha256':old['binary_sha256'],'variant_ini':old['variant_ini'],'teacher':'task1627','fairness':'Commonrandomuniformquantile stream byfamily/seed, sameacrossprices; colors/seedsdependent, familybootstrapunit. Old60000qualifiedactual4x4policychoices mayreused, geometry/price/state explicit.'};(O/'plan.json').write_text(json.dumps(plan,indent=2));print('NEW_FROZEN',len(families),'attempts',attempts,'maxgo',plan['max_physical_go'])
