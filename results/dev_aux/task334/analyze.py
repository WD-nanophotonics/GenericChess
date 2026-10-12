"""Zero-new-game first-round intervention exposure and robust diagnostics."""
import json,time,collections,statistics,hashlib
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task334';assert not (O/'audit.json').exists();start=time.monotonic();D=json.loads((R/'results/dev_aux/task322/declaration.json').read_bytes());P=json.loads((R/'results/dev_aux/task322/progress.json').read_bytes());data=json.loads((R/'results/dev_aux/task320/result.json').read_bytes())['calls']+[json.loads(s) for s in (R/'results/dev_aux/task322/games.jsonl').read_bytes().splitlines()];key=lambda w:tuple(w[k] for k in 'PNBRQK');cache={(key(z['weights']),z['root'],z['color'],z['seed']):z for z in data};assert len(cache)==len(data);out=[];groups=[]
def trace(z):
 f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
 for u in f['history']:b.push_uci(u)
 c=collections.Counter();seen={k:0 for k in 'PNBRQ'};boards=[]
 for ply,u in enumerate(z['actions']):
  m=chess.Move.from_uci(u);assert m in b.legal_moves;actor=chess.piece_symbol(b.piece_type_at(m.from_square)).upper();victim='P' if b.is_en_passant(m) else (chess.piece_symbol(b.piece_type_at(m.to_square)).upper() if b.is_capture(m) else None);who='candidate' if b.turn==z['color'] else 'opponent';c[who+'_moves_'+actor]+=1
  if victim:c[who+'_captures_'+victim]+=1
  if m.promotion:c[who+'_promotes_'+chess.piece_symbol(m.promotion).upper()]+=1
  for k in seen:seen[k]+=bool(b.pieces(chess.PIECE_SYMBOLS.index(k.lower()),z['color']))
  boards.append(b.fen());b.push(m)
 return dict(counters=dict(c),presence_candidate_ply=seen,boards=boards,plies=len(z['actions']))
traces={}
for rd in P['rounds']:
 if rd['generation']!=0:continue
 base=rd['candidates'][0];base_rows=[cache[(key(base['weights']),ri,color,seed)] for ri in range(2) for color in D['colors'] for seed in D['random_seeds']]
 for cand in rd['candidates']:
  zz=[cache[(key(cand['weights']),ri,color,seed)] for ri in range(2) for color in D['colors'] for seed in D['random_seeds']];delta=[F(b['fitness'])-F(a['fitness']) for a,b in zip(base_rows,zz)];same=0;firsts=[];counters=collections.Counter();presence=collections.Counter();capture_cells=collections.Counter()
  for a,b in zip(base_rows,zz):
   ka=(key(b['weights']),b['root'],b['color'],b['seed'])
   if ka not in traces:traces[ka]=trace(b)
   t=traces[ka];counters.update(t['counters']);presence.update(t['presence_candidate_ply'])
   for k in 'NB':capture_cells[k]+=any(t['counters'].get(who+'_captures_'+k,0)>0 for who in ('candidate','opponent'))
   first=next((i for i,(u,v) in enumerate(zip(a['actions'],b['actions'])) if u!=v),None)
   if first is None and len(a['actions'])!=len(b['actions']):first=min(len(a['actions']),len(b['actions']))
   same+=a['actions']==b['actions'];firsts.append(first)
  vals=[F(z['fitness']) for z in zz];block={str((ri,color)):sum(F(z['fitness']) for z in zz if z['root']==ri and z['color']==color)/16 for ri in range(2) for color in D['colors']};dropseed=[sum(delta[i] for i,z in enumerate(zz) if z['seed']!=seed)/60 for seed in D['random_seeds']];record=dict(family=rd['family'],variant=cand['variant'],weights=cand['weights'],mean=str(sum(vals)/64),median=str(statistics.median(vals)),min_root_color_mean=str(min(block.values())),block_means={k:str(v) for k,v in block.items()},mean_delta=str(sum(delta)/64),positive_cells=sum(v>0 for v in delta),negative_cells=sum(v<0 for v in delta),nonzero_cells=sum(v!=0 for v in delta),same_trajectory_cells=same,first_divergence_ply=firsts,leave_one_seed_delta=list(map(str,dropseed)),negative_leave_one_seed=sum(v<0 for v in dropseed),capture_type_cells=dict(capture_cells),aggregate_events=dict(counters),candidate_presence_ply=dict(presence));out.append(record)
 groups.append(dict(family=rd['family'],variants=len(rd['candidates']),selected_original=rd['selected']))
result=dict(complete=True,new_games=0,new_queries=0,unique_cached_traces=len(traces),first_rounds=groups,diagnostics=out,source_progress_sha256=hashlib.sha256((R/'results/dev_aux/task322/progress.json').read_bytes()).hexdigest(),seconds=time.monotonic()-start,scope='All first-round nine candidates/threeinitials, fixed64cells reused; no robust-loss model reselection or new seeds/generation. Captures/presence/firstdivergence describe exposure not causal explanation. PRNG coupling after different boards doesnot imply identical opponent moves. Median and worst fixed root/color mean are only retrospective diagnostics, not an independently validated objective.')
(O/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='diagnostics'},indent=2));print(json.dumps([{k:z[k] for k in ('family','variant','mean_delta','nonzero_cells','same_trajectory_cells','capture_type_cells','median','min_root_color_mean','negative_leave_one_seed')} for z in out],indent=2))