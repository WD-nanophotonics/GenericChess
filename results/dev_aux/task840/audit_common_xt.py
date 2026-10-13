import json,math,hashlib,time
from pathlib import Path
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task881';O.mkdir(exist_ok=False);start=time.perf_counter();d=json.loads((R/'results/dev_aux/task880/result.json').read_bytes());models=json.loads((R/'results/dev_aux/task849/result.json').read_bytes())['models'];games=[json.loads(l) for l in (R/'results/dev_aux/task846/games.jsonl').open(encoding='utf-8') if json.loads(l)['profile'].startswith('original_')];assert len(games)==len(d['game_inventory'])==192;records=0
for g,r in zip(games,d['game_inventory']):
 xs=[]
 for q in g['queries']:
  if q['player']!='candidate':continue
  b=C.Board(q['initial_sfen'])
  for u in q['history']:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
  x=[0]*16
  for pc in b.pieces:
   if pc:x[pc%16]+=1 if (0 if pc<16 else 1)==g['color'] else -1
  for side,h in enumerate(b.pieces_in_hand):
   for i,n in enumerate(h):x[[1,2,3,4,7,5,6][i]]+=n*(1 if side==g['color'] else -1)
  x[8]=0;xs.append(x);records+=1
 initial=g['profile'][9:];t=g['termination'];terminal=not t['kind'].startswith('cap');y=(1 if t['winner']==g['color'] else -1 if t['winner'] is not None else 0) if terminal else g['raw_quantity']/19;assert r['records']==len(xs) and r['initial']==initial and r['family']==g['root']['seed'] and r['color']==g['color'] and r['label']==y and r['terminal']==terminal
 for arm in ['trajectory','first_candidate']:
  w=next(m['weights'] for m in models if m['initial']==initial and m['arm']==arm);error=sum((math.tanh(sum(a*v for a,v in zip(x,w))/1710)-y)**2 for x in xs)/len(xs);assert abs(error-r['errors'][arm])<1e-12
for row in d['rows']:
 rs=[r for r in d['game_inventory'] if r['initial']==row['initial'] and r['pool']==row['pool'] and r['opponent']==row['opponent'] and (row['stratum']=='all' or r['terminal']==(row['stratum']=='terminal'))];fs=sorted(set(r['family'] for r in rs));assert row['games']==len(rs) and row['families']==len(fs)
 for arm in ['trajectory','first_candidate']:
  value=sum(sum(r['errors'][arm] for r in rs if r['family']==f)/sum(r['family']==f for r in rs) for f in fs)/len(fs) if fs else None;assert value is None and row['mean_error'][arm] is None or abs(value-row['mean_error'][arm])<1e-12
out=dict(status='PASS_ALL192_SHARED_XT_PRICE_COMPARISONS',actual_games=192,actual_decision_records=records,rows=24,new_go=0,new_fit_epochs=0,source_models_unchanged_sha256=hashlib.sha256((R/'results/dev_aux/task849/result.json').read_bytes()).hexdigest(),seconds=time.perf_counter()-start,scope='Independentnativecshogi fullhistory/features/labels, bothfrozenmodels onexactsameXt, allgame errors andfamily/stratum aggregation. Earlier849 remainsinputinformation comparison, notdirectpricecomparison.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
