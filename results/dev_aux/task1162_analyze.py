from pathlib import Path
import json,ast,chess,random,collections
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1162';O.mkdir()
load=lambda n:[json.loads(s) for s in (R/f'results/dev_aux/task{n}/games.jsonl').read_text().splitlines()]
base=load(1154);new=load(1160)
key=lambda g:(g['root']['seed'],g['color'],g['opponent'])
bm={key(g):g for g in base};out=[]
for arm in ['J','L']:
 gs=[g for g in new if g['arm']==arm]; ds=[(g,bm[key(g)]) for g in gs]; y=lambda g:(g['label']=='W')-(g['label']=='L')
 for opp in ['ALL','unit_search','uniform_random']:
  z=[(g,b) for g,b in ds if opp=='ALL' or g['opponent']==opp]
  cc=lambda j:dict(collections.Counter(p[j]['label'] for p in z))
  by=collections.defaultdict(int)
  for g,b in z:by[g['root']['seed']]+=y(g)-y(b)
  out.append(dict(arm=arm,opponent=opp,N=len(z),baseline=cc(1),candidate=cc(0),baseline_J=str(F(sum(y(b) for g,b in z),len(z))),candidate_J=str(F(sum(y(g) for g,b in z),len(z))),paired_delta=str(F(sum(y(g)-y(b) for g,b in z),len(z))),family_deltas=dict(by),changed_labels=sum(g['label']!=b['label'] for g,b in z)))
(O/'result.json').write_text(json.dumps(dict(status='PAIRED_CONSUMPTION_NO_REFIT',rows=out,scope='16 dev families, finiteH24; predictivefixedpolicy coefficients are not intrinsicallyoptimalprices. Sameexposed dev cohort, newcandidateoutcomes; notindependentpopulationreplication.'),indent=2))
print(out)
# reconstruct all contact samples; independent royal movement/attacks
O=R/'results/dev_aux/task1163';O.mkdir()
src=(R/'results/dev_aux/task1016/audit_pilot.py').read_text(encoding='utf-8-sig')
defs=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name in ['reachable','attacked','literal']]
text=ast.unparse(ast.Module(body=defs,type_ignores=[])).replace('range(5)','range(8)')
inside=lambda s:0<=s<64
exec(text)
src=(R/'results/dev_aux/task1151/generate.py').read_text(encoding='utf-8-sig')
defs=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='contactdraw'];exec(compile(ast.Module(body=defs,type_ignores=[]),'sampling_replay','exec'))
d=json.loads((R/'results/dev_aux/task1153/roots.json').read_bytes());picked=[];counts=collections.Counter();valid=0;frontiers=0
for r in d['trace']:
 assert contactdraw(r['seed'],r['types'],r['colors'])==r['squares']
 b=chess.Board(None)
 for s,t,c in zip(r['squares'],r['types'],r['colors']):b.set_piece_at(s,chess.Piece(t,bool(c)))
 b.turn=not((r['index']//4)%2);assert b.fen()==r['fen8']
 failure=None
 if not b.is_valid():failure='invalid'
 else:
  valid+=1;legal=literal(b);assert legal==r['legal'];frontiers+=1
  cap=[u for u in legal if b.piece_at(chess.Move.from_uci(u).to_square)];assert cap==r['captures']
  if not legal or b.is_insufficient_material():failure='terminal'
  elif len(legal)<2:failure='too_few_legal'
  elif not cap:failure='no_capture'
  else:
   for u in legal:
    b.push_uci(u); ll=literal(b);frontiers+=1
    dd={s:(p.piece_type,p.color) for s,p in b.piece_map().items()};king=b.king(b.turn)
    win=not ll and attacked(dd,king,not b.turn);b.pop()
    if win:failure='immediate_win';break
 assert failure==r['failure']
 if failure is None and counts[r['composition']]<8:
  picked.append(r['seed']);counts[r['composition']]+=1
assert picked==[r['seed'] for r in d['roots']]
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL_CONTACT_SAMPLING_AND_LITERAL_FILTERS',attempts=len(d['trace']),valid=valid,literal_frontiers=frontiers,selected=len(picked),scope='Samplingfunction replay, independentliteralKRNroyalrulefilter. Invalidsamplespreserved; sufficientinsufficiency predicatepythonchess notcompleteFIDEdeadoracle.'),indent=2))
print('CONTACTPASS',valid,frontiers)
# budget and scale summaries (do not invent sub-batch wall)
O=R/'results/dev_aux/task1147';O.mkdir()
rows=[]
for n,param in [(1145,'budget'),(1149,'scale')]:
 gs=load(n);print(n,gs[0].keys())
 groups=collections.defaultdict(list)
 for g in gs:groups[(g.get(param,g.get('candidate_nodes',64)),g['opponent'])].append(g)
 for (v,opp),ss in groups.items():
  p={k:{key(g):g for g in ss if g['price']==k} for k in [90,164]}
  if set(p[90])!=set(p[164]):raise AssertionError()
  y=lambda g:(g['label']=='W')-(g['label']=='L')
  delta={k:y(p[164][k])-y(p[90][k]) for k in p[90]}
  fam=collections.defaultdict(int)
  for k,t in delta.items():fam[k[0]]+=t
  rows.append(dict(task=n,parameter=param,value=v,opponent=opp,N=len(delta),paired_delta=str(F(sum(delta.values()),len(delta))),families=dict(fam),different_outcomes=sum(t!=0 for t in delta.values())))
(O/'result.json').write_text(json.dumps(dict(status='EXPOSED_TINY_DIAGNOSTICS',rows=rows,scope='No adoption/retraining; budgets/scalechangeintervention; sourcecombined wall only, no per-arm host timing.'),indent=2))
# total actual cost
tasks=[1118,1121,1127,1133,1138,1141,1145,1149,1154,1160];bb=[]
for n in tasks:
 d=json.loads((R/f'results/dev_aux/task{n}/result.json').read_bytes());assert d['complete'] and not d['error'];bb.append(dict(task=n,games=d['closed_games'],go=d['actual_go'],seconds=d['seconds']))
cost=dict(games=sum(b['games'] for b in bb),go=sum(b['go'] for b in bb),producer_seconds=sum(b['seconds'] for b in bb),perft_go=576,batches=bb,scope='Actual serial producer wall, normal concurrent machine, no speedup/token-cost claim; no single hour job; all actual WLD/C retained.')
(R/'results/dev_aux/COST_20261014_42.json').write_text(json.dumps(cost,indent=2));print('COST',cost)
