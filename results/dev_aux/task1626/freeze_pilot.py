from pathlib import Path
import json,random,importlib.util,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1630';O.mkdir(exist_ok=False);sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);rng=random.Random(2026678200);families=[];seen=set();attempts=0
pairs=[(1,2,7),(1,3,6),(2,3,5)]
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
     if fx:x=3-x
     if fy:y=3-y
     a.append(x+4*y)
    out.extend([tuple(a+[s[8]]),tuple(a[4:]+a[:4]+[1-s[8]])])
 return sorted(set(out))
while len(families)<16:
 attempts+=1;f=len(families);a,b,c=pairs[f%3];actors=[0,4,a,b,c];positions=rng.sample(range(16),5);s=[16]*8
 for i,p in zip(actors,positions):s[i]=p
 s=tuple(s+[0]);k0,k1=s[0],s[4]
 if max(abs(k0%4-k1%4),abs(k0//4-k1//4))>2 or not T.valid(s) or not T.attacked(s,s[0],1):continue
 ll=T.moves(s)
 if len(ll)<2 or any(not T.moves(t) and T.attacked(t,t[4*t[8]],1-t[8]) for u,t in ll):continue
 oo=orbit(s);key=min(oo)
 if key in seen:continue
 seen.add(key);white=[t for t in oo if t[8]==0];q=rng.choice(white);other=tuple(q[4:8]+q[:4]+(1-q[8],));families.append({'family':f,'phase':'PILOT','stock':'RNvsB' if f%3==0 else 'RBvsN' if f%3==1 else 'NBvsR','orbit_states':oo,'roots':[q,other]})
plan={'status':'FROZEN_BEFORE_NATIVE_QUERIES','question':'Can reachableactual4x4fivepolicy close cheaply usingONLYcommonperfect<=4oracle? Fixedprior3x4C50 transfer optionalprespecifiedsecondprofile, no4x4learning.','families':families,'seed':2026678200,'rootlaw':'Whiteinitial2nonkingsvsone, bothkingswithinCheby2, activeKingchecked>=2evasions, no immediatewinmate; randomwhite representative perD4colorfamily pluscolorpair; nopricebasedselection','attempts':attempts,'seconds_per_profile':300,'single_total_seconds':600,'max_go_per_profile':30000,'max_graph_states_per_profile':80000,'profiles':[(720,720,720),(1440,720,720)],'teacher':'task1627','teacher_scope':'<=4actor4x4 only, nofull5oracle. Unknownbounds[-1,+1], neverdrawlabels. Bothprofilecapsoriginal/noextension.','binary':'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe','binary_sha256':'0263e8d6e9677b82e179c0d1a61ea5080df3275aba3464569e040eb222a20fe9','variant_ini':'results/dev_aux/task1629/variant.ini','rules_sha256':hashlib.sha256((R/'results/dev_aux/task1626/rules.py').read_bytes()).hexdigest(),'purpose':'Baseline300sfeasibility thenpredeclaredfixedpriorpricecontrast300s; total600s10min<1hour, not12price training split.'};(O/'plan.json').write_text(json.dumps(plan,indent=2));print('ROOTS_FROZEN',len(families)*2,'attempts',attempts,'stocks',[f['stock'] for f in families])
