"""Second implementation checks zero-new-game exposure and robust diagnostic aggregations."""
import json,collections,statistics,hashlib
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task339';assert not (O/'audit.json').exists();A=json.loads((R/'results/dev_aux/task334/audit.json').read_bytes());D=json.loads((R/'results/dev_aux/task322/declaration.json').read_bytes());P=json.loads((R/'results/dev_aux/task322/progress.json').read_bytes());data=json.loads((R/'results/dev_aux/task320/result.json').read_bytes())['calls'];data.extend(json.loads(s) for s in (R/'results/dev_aux/task322/games.jsonl').read_bytes().splitlines());kw=lambda w:tuple(w[k] for k in 'PNBRQK');cache={(kw(z['weights']),z['root'],z['color'],z['seed']):z for z in data};checked=0
for a in A['diagnostics']:
 rd=next(r for r in P['rounds'] if r['family']==a['family'] and r['generation']==0);candidate=next(c for c in rd['candidates'] if c['variant']==a['variant']);assert candidate['weights']==a['weights'];rr=[cache[(kw(candidate['weights']),ri,color,seed)] for ri in range(2) for color in D['colors'] for seed in D['random_seeds']];base=[cache[(kw(rd['starting']),z['root'],z['color'],z['seed'])] for z in rr];vs=[F(z['fitness']) for z in rr];delta=[F(z['fitness'])-F(b['fitness']) for z,b in zip(rr,base)];assert a['mean']==str(sum(vs)/64) and a['mean_delta']==str(sum(delta)/64) and a['median']==str(statistics.median(vs));assert a['same_trajectory_cells']==sum(z['actions']==b['actions'] for z,b in zip(rr,base));cap=collections.Counter();ev=collections.Counter();presence=collections.Counter();first=[]
 for z,b0 in zip(rr,base):
  f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
  for u in f['history']:b.push_uci(u)
  captured=set()
  for u in z['actions']:
   m=chess.Move.from_uci(u);assert m in b.legal_moves;who='candidate' if b.turn==z['color'] else 'opponent';actor=b.piece_at(m.from_square).symbol().upper();ev[who+'_moves_'+actor]+=1
   if b.is_capture(m):k='P' if b.is_en_passant(m) else b.piece_at(m.to_square).symbol().upper();ev[who+'_captures_'+k]+=1;captured.add(k)
   if m.promotion:ev[who+'_promotes_'+chess.piece_symbol(m.promotion).upper()]+=1
   for k in 'PNBRQ':presence[k]+=len(b.pieces(chess.PIECE_SYMBOLS.index(k.lower()),z['color']))>0
   b.push(m)
  for k in 'NB':cap[k]+=k in captured
  ix=0
  while ix<min(len(z['actions']),len(b0['actions'])) and z['actions'][ix]==b0['actions'][ix]:ix+=1
  first.append(None if ix==len(z['actions'])==len(b0['actions']) else ix)
 assert dict(cap)==a['capture_type_cells'] and dict(ev)==a['aggregate_events'] and dict(presence)==a['candidate_presence_ply'] and first==a['first_divergence_ply'];dd=[sum(delta[i] for i,z in enumerate(rr) if z['seed']!=seed)/60 for seed in D['random_seeds']];assert list(map(str,dd))==a['leave_one_seed_delta'];blocks=[sum(F(z['fitness']) for z in rr if z['root']==ri and z['color']==co)/16 for ri in range(2) for co in D['colors']];assert str(min(blocks))==a['min_root_color_mean'];checked+=1
assert checked==27
(O/'audit.json').write_text(json.dumps(dict(complete=True,all27fixedfirst_roundcandidates_checked=True,new_queries=0,source_sha256=hashlib.sha256((R/'results/dev_aux/task334/audit.json').read_bytes()).hexdigest(),scope='Independent fulltrajectory type/capture/presence/firstdivergence andexactFraction summaries; no causal identification or robustloss re-selection.'),indent=2),encoding='utf-8');print('PASS',checked)