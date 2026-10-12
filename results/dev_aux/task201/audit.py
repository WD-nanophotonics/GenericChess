"""Fulltrace audit and matchedshortcap informativeness curve."""
import json,random,math,statistics,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task201';P=R/'results/dev_aux/task200';D=json.loads((P/'declaration.json').read_bytes());C=json.loads((P/'games.json').read_bytes());assert C['complete'];sp=importlib.util.spec_from_file_location('G201',R/'results/dev_aux/task104/short_game.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);counts=dict(games=0,moves=0,searches=0,probes=0);by={c['name']:c for c in C['calls']}
for c in C['calls']:
 r=c['result'];w=c['weights'];b=chess.Board(r['root_fen']);col=r['agent_color'];rng=random.Random(c['random_seed']);ix=0
 for m in r['opening_history']:b.push_uci(m)
 assert b.fen()==r['opening_fen']==D['roots'][c['opening_index']]['expected_fen']
 for text in r['actions']:
  assert not b.is_game_over(claim_draw=False);m=chess.Move.from_uci(text);assert m in b.legal_moves
  if b.turn==col:
   meta=r['search_records'][ix];assert meta['root_fen']==r['root_fen'] and meta['full_history']==[z.uci() for z in b.move_stack] and meta['backend'].endswith(D['binary_sha256']) and meta['nodes_limit']==1024;ix+=1;counts['searches']+=1
  else:assert m==rng.choice(sorted(b.legal_moves,key=lambda z:z.uci()))
  b.push(m);counts['moves']+=1
 assert ix==len(r['search_records']) and b.fen()==r['final_fen'] and G.score(b,col,len(r['actions']),c['cap'])==r['score'] and len(r['actions'])<=c['cap'];counts['games']+=1
 assert len(r['candidate_leaf_probes'])==5
 for probe in r['candidate_leaf_probes']:assert abs(probe['measured_white_pawns']-w[probe['type']]/208)<=.011;counts['probes']+=1
 assert r['table_ack']['alignment']==3 and r['table_ack']['prices']=={str(i+1):[w[k],w[k]] for i,k in enumerate('PNBRQ')}
pairs=[];prefix_fail=[]
for profile in D['profiles']:
 for oi in range(8):
  for col in (True,False):
   a=by[f'{profile}-cap16-o{oi}-c{int(col)}'];b=by[f'{profile}-cap24-o{oi}-c{int(col)}'];ra=a['result'];rb=b['result'];same=ra['actions']==rb['actions'][:len(ra['actions'])]
   if not same:prefix_fail.append(dict(profile=profile,root=oi,color=col,actions16=ra['actions'],actions24=rb['actions']))
   pairs.append(dict(profile=profile,root=oi,color=col,same_prefix=same,terminal16=ra['score']['terminal'],terminal24=rb['score']['terminal'],terminal_after16=(not ra['score']['terminal'] and rb['score']['terminal']),played=[len(ra['actions']),len(rb['actions'])],quantity=[ra['score']['quantity_difference'],rb['score']['quantity_difference']]))
rows=[]
for cap in (16,24):
 base=None
 for profile in D['profiles']:
  gs=[c for c in C['calls'] if c['cap']==cap and c['profile']==profile];cats={key:0 for key in ('win','loss','draw','cutoff_unknown')}
  for c in gs:
   s=c['result']['score'];cat='cutoff_unknown' if not s['terminal'] else 'draw' if s['winner'] is None else 'win' if s['winner']==c['result']['agent_color'] else 'loss';cats[cat]+=1
  vv=dict(cap=cap,profile=profile,categories=cats,original_mean=statistics.mean(c['result']['reward'] for c in gs),quantity_mean=statistics.mean(c['result']['score']['quantity_difference']/15 for c in gs),played_actions=sum(len(c['result']['actions']) for c in gs),play_seconds=sum(c['play_seconds'] for c in gs),search_nodes=sum(m['reported_nodes'] for c in gs for m in c['result']['search_records']))
  if profile=='unit':base=vv
  vv['paired_original_delta_vs_unit']=vv['original_mean']-base['original_mean'];rows.append(vv)
out=dict(complete=True,counts=counts,groups=rows,pairs=pairs,prefix_failures=prefix_fail,source_sha256=hashlib.sha256((P/'games.json').read_bytes()).hexdigest(),scope='Allmatchedroots/profiles/caps. Completednet atrespectivecap, unknowncutoffsnotfinaldraw/WDL; originalspeedbonusnormalizedbyeachcap, so originaldelta mixes horizon/speednormalization. Traceprefix explicitlyverified; no longerlearning/methodselection orfrozen187testextension.')
(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(counts=counts,prefix_failures=len(prefix_fail),groups=rows),indent=2))
