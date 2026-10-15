from pathlib import Path
import json,random,hashlib,importlib.util,math
R=Path.cwd();O=R/'results/dev_aux/task1685';O.mkdir(exist_ok=False)
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1675/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
rng=random.Random(2026689600);families=[];seen={min(tuple(s) for s in f["orbit_states"]) for f in json.loads((R/"results/dev_aux/task1677/plan.json").read_bytes())["families"]};attempts=0;stock=[('R','N','p'),('R','P','n'),('N','P','r')]
def transform(s,fx=False,swap=False):
 q=['.']*16
 for i,p in enumerate(s[:16]):
  if p=='.':continue
  x,y=i%4,i//4;q[(3-x if fx else x)+4*(3-y if swap else y)]=p.swapcase() if swap else p
 return tuple(q+[1-s[16] if swap else s[16]])
def orbit(s):return sorted({transform(s,fx,sw) for fx in (False,True) for sw in (False,True)})
while len(families)<128:
 attempts+=1;f=len(families);pcs=stock[(f//2)%3]
 if f%2:pcs=tuple(p.swapcase() for p in pcs)
 s=['.']*16
 for i,p in zip(rng.sample(range(16),5),('K','k')+pcs):s[i]=p
 s=tuple(s+[0])
 if not T.valid(s) or max(abs(T.king(s,0)%4-T.king(s,1)%4),abs(T.king(s,0)//4-T.king(s,1)//4))>2 or not T.attacked(s,T.king(s,0),1):continue
 ll=T.moves(s)
 if len(ll)<2 or any(not T.moves(t) and T.attacked(t,T.king(t,t[16]),1-t[16]) for u,t in ll):continue
 oo=orbit(s);key=min(oo)
 if key in seen:continue
 seen.add(key);s=rng.choice([q for q in oo if q[16]==0]);other=transform(s,False,True)
 assert all(T.valid(q) for q in oo);assert sum(p!='.' and p.isupper() for p in s[:16])==(3 if f%2==0 else 2)
 families.append({'family':f,'phase':'TRAIN1' if f<32 else 'TRAIN2' if f<64 else 'DEV','stock':('OWN2_' if f%2==0 else 'OWN1_')+''.join(pcs),'orbit_states':oo,'roots':[s,other]})
plan={'status':'FROZEN_PAWN_PROMOTION_BEFORE_QUERIES','base_source_revision':'8ac8a9fc44354cc84ff5fbfe5e3361cb844be050','families':families,'attempts':attempts,'seed':2026689600,'rootlaw':'InitialglobalR,N,P each1; active1/2nonkings balanced; pressurecheckedactiveKing>=2evasions/noimmediatewinmate; rootselectionpriceandWDLblind. Pawnonlyinteriorranks; framegroupfileflip/rankflip+color, NOTD4. Phaseorbitdisjoint. PromotionR/N/B mayduplicate actors.','price_order':['R','N','B','P'],'R_grid':[360,720,1440,1728],'P_grid':[360,720,1440],'N':720,'B':720,'baseline':[720,720,720,720],'opponent':'Actualfixedbaselinecold64; actualcandidatecold64, oneengine ACK beforeeveryuncachedquery; fullstate/price coldchoice cache definesbothmemorylesspolicies.','H':96,'TRAIN_families':32,'DEV_families':64,'colors_per_family':2,'seeds':1,'primary_selector':'TRAIN1,TRAIN2 andPOOLED globalgridmax finiteWinby96-minusLossby96, lowestlexprice tie; DEV onlyselectedendpoints andbaseline, noDEVwinner. Unknown0eventscore NOTDraw, separateinfinitebounds.','labels':'Physicalmate/stale, barekingsprovableDraw, repeatedcomplete16square+turn state fixedbothpoliciescycleDraw, UNKNOWN at96. NOoldsingleN/Bstockproof, noquantityreward/winningoracle/minimaxlabels.','rules':'Royal4x4, singlePawnstep/noEP/castle/drop, mandatorypromotionRNB; allpiececurrenttypes/locations/color+turn retained; unlimitedcyclesDraw, nFold/nMove disabled. No fullChess/Shogi/generateddomain claim.','seconds_cap':1200,'max_go':50000,'expected_seconds':300,'binary':'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe','binary_sha256':'0263e8d6e9677b82e179c0d1a61ea5080df3275aba3464569e040eb222a20fe9','model':'results/dev_aux/task1675/rules.py','model_sha256':hashlib.sha256((R/'results/dev_aux/task1675/rules.py').read_bytes()).hexdigest(),'variant_ini':'results/dev_aux/task1675/variant.ini','qualification':['task1675/literal_result.json','task1676/result.json'],'cache':'Newstate/domain only, nooldprice4state8tuplealias.'}
(O/'plan.json').write_text(json.dumps(plan,indent=2));print('FROZEN_PAWN',len(families),attempts)

rng2=random.Random(2026690600);initials=[]
while len(initials)<2:
 r=18*round(math.exp(rng2.uniform(math.log(90),math.log(2880)))/18);p=18*round(math.exp(rng2.uniform(math.log(90),math.log(1440)))/18);q=(max(90,min(2880,r)),720,720,max(90,min(1440,p)))
 if q not in initials:initials.append(q)
plan.update(status="FROZEN_TWO_RANDOM_INITIAL_LOCAL_LEARNING",initials=initials,initial_seed=2026690600,root_exclusions=["task1677"],algorithm="Samepooled64TRAINfamilies for2independent randomloguniformR/Pinitials,N=B720. Strictbestofcoordinatehalf/double; ifnoimprovement exploreatmost2neutralneighborfrontiers thenstop,6roundcap. PriceboxR90..2880,P90..1440,round18. OnlyTRAINpayoffacceptance; nohumanprice/DEVfit. Notglobalgridargmaxinitialconvergence.",round_cap=6,plateau_frontiers=2,pricebox_R=[90,2880],pricebox_P=[90,1440],quantum=18,expected_seconds=400,seconds_cap=1200,max_go=80000,primary_selector="HighestTRAINfinite_net endpoint amongtwoactualpaths, lowerlex tie; DEV fixedinitials/ends/baseline, pairedlearned-minusowninitial andbaseline.",train_group="BothoriginalTRAIN1/2phasesmergedTRAIN64; preservedrootphaseIDs",source_base="8ac8a9fc44354cc84ff5fbfe5e3361cb844be050")
(O/"plan.json").write_text(json.dumps(plan,indent=2));print("INITIALS",initials)
