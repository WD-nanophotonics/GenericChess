"""Inputs only for the next diagnostic; no engine search or game execution."""
from pathlib import Path
import json,array,random,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1760';O.mkdir(exist_ok=False);T=R/'results/dev_aux/task1741';wdl=(T/'wdl8.bin').read_bytes();rank=array.array('H');rank.frombytes((T/'rank8.bin').read_bytes());proof=json.loads((T/'proof8.json').read_bytes());assert hashlib.sha256(wdl).hexdigest()==proof['wdl_sha256']
def decode(i):
 c=i%2;i//=2;r=i%64;i//=64;b=i%64;k=i//64;s=['.']*64;s[k]='K';s[b]='k';s[r]='R';return tuple(s+[c])
def orbit(s):
 out=set()
 for rot in range(4):
  for flip in (0,1):
   for swap in (0,1):
    q=['.']*64
    for i,p in enumerate(s[:-1]):
     x,y=i%8,i//8
     if flip:x=7-x
     for _ in range(rot):x,y=7-y,x
     q[x+8*y]=p.swapcase() if swap else p
    out.add(tuple(q+[1-s[-1] if swap else s[-1]]))
 return out
ids=[i for i,v in enumerate(wdl) if v==1 and i%2==0];rng=random.Random(2026701560);rng.shuffle(ids);bins=[(1,4),(5,8),(9,16),(17,32)];groups={b:[] for b in bins};seen=set()
for i in ids:
 d=rank[i];band=next(b for b in bins if b[0]<=d<=b[1])
 if len(groups[band])==16:continue
 s=decode(i);oo=orbit(s)
 if seen&oo:continue
 seen|=oo;other=tuple(p.swapcase() for p in s[:-1])+(1-s[-1],);groups[band].append(dict(table_id=i,DTM=d,roots=[s,other],orbit_states=sorted(oo)))
 if all(len(g)==16 for g in groups.values()):break
assert all(len(g)==16 for g in groups.values())
families=[]
for band in bins:
 for f in groups[band]:families.append(dict(f,family=len(families),DTM_band=band))
plan=dict(status='FROZEN_INPUTS_ONLY_NO_NATIVE_QUERIES',seed=2026701560,families=families,question='Which fixedcheapNativebudget actuallyconverts knownKRK wins, andwhichDTMrange canseedlatermixed-materiallearning?',candidate_prices=[[720]*4,[1440,720,720,720]],candidate_nodes=[64,4096,16384],opponent=dict(price=[720]*4,nodes=4096),H=64,seconds_cap=600,max_go=30000,expected_seconds=180,objective='Conversioncapabilitydiagnostic ONLY, notmateriallearning: everyrootruleWIN forRside, dividedbyexactmate-distance beforequery. RsideNativecandidate,bareKingactualfixedNativeopponent,bothcolorframes. Actualphysicalmates/provedpolicystockDraw/cycles/UNKNOWN. NooptimalWDLDrawshortcut orwinningadjudication.',rules='ClosedKRK qualifiedsame8model, noPawn/drop/castle/historydraw; completeD4colorrootorbitsdistinct. All175168R-to-moveWINcandidates available, selectedbyruleDTMnotNativeprice success. Knownwinselection legitimateforcapabilitycurve, NOTevidenceoflearnablepieceprices.',next_action='Qualifyfrozenstates/actualNativefrontiers andbuildmatchingINI/cacheidentity, thenoneboundedcurve; reportwork/depth/actualWDLbyDTMbin andbudget withoutadaptiveextension.',table_sha256=proof['wdl_sha256'],rank_sha256=proof['rank_sha256'],session_prepared=json.loads((R/'.local_agent/session.json').read_bytes())['id'])
(O/'plan.json').write_text(json.dumps(plan,indent=2));(O/'summary.json').write_text(json.dumps(dict(status=plan['status'],families=64,bothcolor_roots=128,DTM_bins=[dict(interval=b,families=len(groups[b]),ranks=sorted({g['DTM'] for g in groups[b]})) for b in bins],actual_native_go=0,actual_games=0),indent=2));print('NEXT_INPUTS_ONLY',[(b,sorted({g['DTM'] for g in groups[b]})) for b in bins])

