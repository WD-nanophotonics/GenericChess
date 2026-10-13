from pathlib import Path
import json,collections
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task951';O.mkdir(exist_ok=False);p=json.loads((R/'results/dev_aux/task947/plan.json').read_bytes());gs=[]
for n in [923,929,948]:
 for i,l in enumerate((R/f'results/dev_aux/task{n}/games.jsonl').open(),1):
  g=json.loads(l)
  if g['root']['variant']=='edge8' and g['opponent']=='unit_search' and g['weights'][5] in p['B_grid']:g['source']=dict(file=f'task{n}/games.jsonl',line=i);gs.append(g)
def st(g):
 t=g['termination'];return 'C' if t['kind'].startswith('cap') else 'D' if t['winner'] is None else 'W' if t['winner']==g['color'] else 'L'
def v(g):return 1 if st(g)=='W' else -1 if st(g)=='L' else 0
rows=[]
for b in p['B_grid']:
 for gold in p['G_promN_grid']:
  a=[g for g in gs if g['weights'][5]==b and g['weights'][7]==gold and g['weights'][11]==gold];assert len(a)==24;row=dict(B=b,G=gold,J24=str(F(sum(map(v,a)),24)),counts=dict(collections.Counter(map(st,a))),sources=[g['source'] for g in a]);rows.append(row);print(b,gold,row['J24'],row['counts'])
best=max(F(r['J24']) for r in rows);plateau=[r for r in rows if F(r['J24'])==best];chosen=plateau[0];profiles=sorted(set([(90,90),(chosen['B'],90),(chosen['B'],chosen['G'])]));out=dict(status='TWO_AXIS_ENDPOINTS_FROZEN_BEFORE_FRESH_ROOT_GENERATION',rows=rows,best_plateau=[{k:r[k] for k in ['B','G','J24']} for r in plateau],chosen={k:chosen[k] for k in ['B','G','J24']},validation_profiles=[dict(B=b,G=g) for b,g in profiles],new_go=0,scope='Sourcegridfirst-order ties fixedBascendingthenG; globalargmaxnotinitconvergence, validconditionalG/promNfamily andB/Horsefamily.' );(O/'endpoints.json').write_text(json.dumps(out,indent=2));print('CHOSEN',out['chosen'],'PROFILES',out['validation_profiles'])
memo='''State: ACTIVE research39; DEV_AUX sidemissiononly; scienceOPEN; heartbeatACTIVE; primaryread-only.
Segment:39 58aae0a9-c16a-4300-bc78-7c2cc0967c6b start2026-10-13T16:20:52.866691+00:00; preserveclock, nosecondwriter.
Main: Do stock-safe two-axis terminal prices transfer? | frozen951 endpoints then947 new32seed sameedgeN4B2G2 validation beforefit/read | actualW/L/D/C familypaired andcost | noquantity/humanfitness, allfailedslots andnegatives kept; oldtestsunchanged.
Backup1: Are joint gains from leaf vsnativepriceconsumers? | onlyvalidstockfrozenpair/exposeddiagnostic withdualprice38 | actualleaf/readback andallrules/PV | noSEE-only orbaseB-onlyclaim, noinvalidfourBcache.
Backup2: Can danger grammar improve informative outcomes rather than trivialmates? | 935/946 independentlyverified3force roots and16pricevectors, thenprospectivepriceblindnoimmediatemate grammar | familyterminalvariation andconservedstock | keeporiginalmu/labels, notfitfavorableprice-selectedroots.
Evidence:39 validNB4 grid/holdouts/horizon andstockNBG923/924,929/930,938/939,943/944,948/949 closed. 920zero-go Bhand4overflow(native/Cshogi) invalidatesoldNB8 search/learning/force claims;925guard rejects96oldroots;92632maxhandcontrolsPASS. 941syntax/earlycheckpoint handlingerror correctedexplicitly. Dotq39 readallpages/adopt fc3b3a63...; rawprivate. Current951two-axis freeze; consultnotapproval; noactivefailedproducer.
'''
assert len(memo.encode())<2048;(R/'.local_agent/NEXT_WORK.md').write_text(memo,encoding='utf-8')
