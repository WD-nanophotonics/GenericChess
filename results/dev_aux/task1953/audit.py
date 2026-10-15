"""Fixed-opponent actual-WL factorial and leaf-vs-joint table coupling audit."""
from pathlib import Path
from collections import Counter,defaultdict
import json,random,time
from results.dev_aux.task1928.audit import audit,read,lines
from results.dev_aux.task1931.audit import profile
from results.dev_aux.task1945.audit import effect
O=Path('results/dev_aux/task1953')
def leaf_profile(folder):
 p=Path(folder);games=lines(p/'games.jsonl');moves=lines(p/'moves.jsonl');ev=lines(p/'run/transport.jsonl');ext=[m for m in moves if m['source']=='EXTERNAL_SEARCH'];ps=[e for e in ev if e['event']=='PROFILE'];cs=[e for e in ev if e['event']=='CLEAR'];ins=[e for e in ev if e['event']=='INTENT'];chs=[e for e in ev if e['event']=='CHOICE'];assert len(ext)==len(ps)==len(cs)==len(ins)==len(chs)
 for m,pr,cl,i,ch in zip(ext,ps,cs,ins,chs):
  g=games[m['slot']];r=g['R'] if m['side']==g['candidate_side'] else 720
  expected=f'info string DEV_AUX leafRNBP {r} 720 720 720 nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720'
  assert expected in pr['ack'] and pr['values']==cl['values']==i['R']==ch['R']==[r,720,720,720] and 'readyok' in cl['raw']
 return dict(status='PASS_ALL_LEAF_VARIATION_AND_FIXED_NATIVE_CAPTURE_ACKS',queries=len(ext),native_capture_prices='ALL720',leafR='varies720/1440only')
def contrast(ix,opp,terms):
 ds=[];bounds=[];roles=Counter()
 for f in range(32):
  values=[]
  for s in (0,1):
   parts=[(ix[opp,f,s,r,m],coef) for m,r,coef in terms];value=sum(g['finite_event_score']*coef for g,coef in parts);roles[s]+=value;values.append(value);bounds.append(tuple(sum((g['finite_event_score']*coef if g['outcome']!='UNKNOWN' else (-abs(coef) if k==0 else abs(coef))) for g,coef in parts) for k in (0,1)))
  ds.append(sum(values)/2)
 rng=random.Random(20261016641953);bs=sorted(sum(rng.choices(ds,k=32))/32 for _ in range(20000))
 return dict(mean=sum(ds)/32,family95=[bs[500],bs[19499]],family_deltas=ds,nonzero_families=sum(d!=0 for d in ds),role_means={s:v/32 for s,v in roles.items()},unknown_ultimate_bounds=[sum(b[k] for b in bounds)/64 for k in (0,1)])
def paired_paths(folderA,folderB,label):
 ga,gb=lines(Path(folderA)/'games.jsonl'),lines(Path(folderB)/'games.jsonl');ma,mb=lines(Path(folderA)/'moves.jsonl'),lines(Path(folderB)/'moves.jsonl');a=defaultdict(list);b=defaultdict(list)
 for m in ma:a[m['slot']].append(m)
 for m in mb:b[m['slot']].append(m)
 counts=Counter();details=[]
 for x,y in zip(ga,gb):
  assert all(x[k]==y[k] for k in ('slot','family','candidate_side','opponent_nodes','ratio'));aa,bb=a[x['slot']],b[y['slot']];k=0
  while k<min(len(aa),len(bb)) and aa[k]['choice']==bb[k]['choice']:k+=1
  same=len(aa)==len(bb)==k;adopt=[m['ply'] for m in bb[:k+1] if m['side']==y['candidate_side'] and m['source']=='PROOF'];kind='SAME_FULL_PATH' if same else 'CERTIFICATE_ADOPTED_BY_FIRST_DIVERGENCE' if adopt else 'LENGTH_ONLY' if k==min(len(aa),len(bb)) else 'NORMAL_FIRST_DIVERGENCE_CANDIDATE' if bb[k]['side']==y['candidate_side'] else 'NORMAL_FIRST_DIVERGENCE_FIXED_OPPONENT'
  if label=='proof' and adopt:assert y['outcome']=='WIN'
  counts[kind]+=1;counts['same_outcome']+=x['outcome']==y['outcome'];counts[x['outcome']+'->'+y['outcome']]+=1
  details.append(dict(slot=x['slot'],family=x['family'],role=x['candidate_side'],opponent_nodes=x['opponent_nodes'],ratio=x['ratio'],first_difference=None if same else k,kind=kind,outcomes=[x['outcome'],y['outcome']],candidate_proof_adopted_before_or_at_difference=adopt))
 return dict(counts=dict(counts),details=details,scope='Common-prefix classification only; actualcertificate soundness and physicalownerWIN separately audited. A PROOFusedinWINgame is not necessarily a marginalpayoffgain. NORMAL divergences under samepriced/nominalcap callbacks are timing/selective-search confounds, not falselyattributed to provenstrategy.')
def run():
 beg=time.perf_counter();folders={'off':'results/dev_aux/task1943','on':'results/dev_aux/task1944','leaf':'results/dev_aux/task1948'};audits={m:audit(p) for m,p in folders.items()};profiles={m:(leaf_profile(p) if m=='leaf' else profile(p)) for m,p in folders.items()};games={m:lines(Path(p)/'games.jsonl') for m,p in folders.items()};ix={(g['opponent_nodes'],g['family'],g['candidate_side'],g['ratio'],m):g for m,gs in games.items() for g in gs};assert len(ix)==768;factorial=[]
 for opp in (512,4096):
  cells=[]
  for mode,gs in games.items():
   for r in (1.,2.):
    cell=[g for g in gs if g['opponent_nodes']==opp and g['ratio']==r];assert len(cell)==64;cells.append(dict(mode=mode,ratio=r,outcomes=dict(Counter(g['outcome'] for g in cell)),net=sum(g['finite_event_score'] for g in cell),seconds=sum(g['seconds'] for g in cell)))
  terms={'price_with_proof':[('on',2.,1),('on',1.,-1)],'price_without_proof':[('off',2.,1),('off',1.,-1)],'proof_at_baseline':[('on',1.,1),('off',1.,-1)],'proof_at_learned':[('on',2.,1),('off',2.,-1)],'proof_price_interaction':[('on',2.,1),('on',1.,-1),('off',2.,-1),('off',1.,1)],'leafonly_price':[('leaf',2.,1),('leaf',1.,-1)],'coupling_price_interaction':[('off',2.,1),('off',1.,-1),('leaf',2.,-1),('leaf',1.,1)]}
  factorial.append(dict(opponent_nodes=opp,cells=cells,effects={name:contrast(ix,opp,t) for name,t in terms.items()}))
 out=dict(status='PASS_FIXED_OPPONENT_2X2_AND_LEAF_COUPLING',audits=audits,profiles=profiles,factorial=factorial,proof_paths=paired_paths(folders['off'],folders['on'],'proof'),coupling_paths=paired_paths(folders['off'],folders['leaf'],'coupling'),actual_study_seconds={m:read(Path(p)/'completion.json')['seconds'] for m,p in folders.items()},seconds=time.perf_counter()-beg,scope='Price2lockedOFFTRAINonly, NOTONretraining. ALL32CONFIRMfamilies/roles/2fixedopponents sharecohort;32not64independentclusters. ON/OFFONLYcandidateproof changes. Leafablation fixesNative/capturetogethertoUNIT720, no separateattributionbetweenthem, developmentnotfreshvalidation. Equalnormalrequestedcaps/phasewallsnot equaltotalcost; ordinaryconcurrentload and actualreportednodeovershoot retained. UNKNOWNneverDRAW/infiniteWDL, nohumanfit/defaultchanges.')
 (O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(status=out['status'],effects=[dict(opponent_nodes=f['opponent_nodes'],means={k:v['mean'] for k,v in f['effects'].items()}) for f in factorial],actual_study_seconds=out['actual_study_seconds'],proof_paths=out['proof_paths']['counts'],coupling_paths=out['coupling_paths']['counts'],seconds=out['seconds'])))
if __name__=='__main__':run()
