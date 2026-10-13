import json,re,math,hashlib,time,sys,collections
from pathlib import Path
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task817';start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import audit as V
for n in [806,816]:assert json.loads((R/f'results/dev_aux/task{n}/result.json').read_bytes())['status'].startswith('PASS_ALL_')
d=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());weights={tuple(x['weights']):x['name'] for x in d['initial_profiles']};cohorts={1024:{},256:{}};hashes={}
for task,budget in [(787,1024),(791,1024),(804,1024),(814,256)]:
 p=R/f'results/dev_aux/task{task}/games.jsonl';hashes[str(task)]=hashlib.sha256(p.read_bytes()).hexdigest()
 for i,line in enumerate(p.open(encoding='utf-8'),1):
  g=json.loads(line)
  if tuple(g['weights']) not in weights:continue
  opp=g.get('opponent','unit');key=(opp,tuple(g['weights']),json.dumps(g['root'],sort_keys=True),g['color']);cohorts[budget].setdefault(key,(g,dict(task=task,line=i)))
rows=[];counterexamples=[]
for budget,games in cohorts.items():
 assert len(games)==128,(budget,len(games));counts=collections.Counter()
 for key,(g,ref) in games.items():
  for qi,q in enumerate(g['queries']):
   assert q['nodes_limit']==budget;infos=[s for s in q['lines'] if ' score ' in s];assert infos;selections=[('final_reported',infos[-1])];ub=[s for s in infos if 'score cp ' in s and 'upperbound' not in s and 'lowerbound' not in s]
   if ub:selections.append(('last_unbounded_cp',ub[-1]))
   for policy,line in selections:
    counts[policy+'_queries']+=1;bound='upperbound' in line or 'lowerbound' in line
    if bound:counts[policy+'_bound']+=1
    m=re.search(r' score cp (-?\d+)',line)
    if not m:counts[policy+'_mate_or_noncp']+=1;continue
    if ' pv ' not in line:counts[policy+'_missing_PV']+=1;continue
    b=C.Board(q['initial_sfen'])
    for u in q['history']:mm=b.move_from_usi(u);assert b.is_legal(mm);b.push(mm)
    rootturn=b.turn;pv=line.split(' pv ',1)[1].split()
    for u in pv:mm=b.move_from_usi(u);assert b.is_legal(mm);b.push(mm)
    raw,n=V.literal(b.sfen(),q['weights']);stm=raw if rootturn==0 else -raw;cp=math.trunc(100*stm/90);reported=int(m[1]);match=cp==reported;counts[policy+'_cp_PV']+=1;counts[policy+'_material_match']+=match;counts[policy+'_material_mismatch']+=not match
    row=dict(budget=budget,policy=policy,source=ref,query=qi,opponent=key[0],start=weights[tuple(g['weights'])],family=g['root']['source_family'],color=g['color'],reported_cp=reported,leaf_raw_rootSTM=stm,leaf_cp=cp,bound=bound,pv=pv,leaf_sfen=b.sfen(),material_matches=match);rows.append(row)
    if not match:counterexamples.append(row)
 outrow=dict(nodes=budget,initial_games=len(games),counts=dict(counts));print(json.dumps(outrow),flush=True);(O/f'counts_{budget}.json').write_text(json.dumps(outrow,indent=2),encoding='utf-8')
out=dict(status='ALL256_INITIAL_GAMES_SCORE_PV_LEAF_DIAGNOSTIC',source_sha256=hashes,rows=rows,counterexamples=counterexamples,new_go=0,seconds=time.perf_counter()-start,scope='ALL128initialgames per256/1024 budget twooriginalprices/twofixedopponents/16families/2colors, fullqual806816 and789792. Finalreported andlastunboundedcp policies separate. ActualMATERIAL_LEVEL1 purematerial andto_cp trunc100v/90 reviewed. LegalprintedPV matchingmaterial doesnotcertifysearchvalue/gradient/fullleaf; bound/mate/truncation/mismatch retained. No discardedgames/newsearch/training/referencefit. TDLeaf isfutureapproximation/mechanismroute, failureslimitprintedPV exactassumption notwholefield.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('PVleafdiagnosticcomplete',len(rows),len(counterexamples),round(out['seconds'],3))
