import json,time,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task266';assert not (O/'audit.json').exists();D=json.loads((R/'results/dev_aux/task265/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task265/result.json').read_bytes());assert X['complete'];start=time.monotonic();checks=0;groups=[]
for z in X['rows']:
 f=next(f for f in D['roots'] if f['id']==z['root']);w=D['profiles'][z['profile']];assert z['weights']==w;meta=z['metadata'];assert meta['root_fen']==f['initial_fen'] and meta['full_history']==f['history'];b=chess.Board(f['initial_fen'])
 for text in f['history']:b.push_uci(text)
 assert b.fen()==f['fen'] and chess.Move.from_uci(z['move']) in b.legal_moves
 assert z['table_ack']['alignment']==3 and z['table_ack']['prices']=={str(i+1):[w[k],w[k]] for i,k in enumerate('PNBRQ')};assert len(z['leaf_probes'])==5
 for p in z['leaf_probes']:assert abs(p['measured_white_pawns']-w[p['type']]/208)<.011
 for line in meta['uci_info']:
  if line.startswith('info ') and ' pv ' in line:
   bb=b.copy(stack=True);pv=line.split(' pv ',1)[1].split()
   for text in pv:
    m=chess.Move.from_uci(text);assert m in bb.legal_moves;bb.push(m)
 assert meta['reported_nodes'] is not None and meta['reported_depth'] is not None;checks+=1
for limit in D['node_limits']:
 rr=[r for r in X['rows'] if r['metadata']['nodes_limit']==limit];groups.append(dict(limit=limit,queries=len(rr),sum_wall_seconds=sum(r['wall_seconds'] for r in rr),reported_nodes_sum=sum(r['metadata']['reported_nodes'] for r in rr),overshoot_min=min(r['metadata']['reported_nodes']-limit for r in rr),overshoot_max=max(r['metadata']['reported_nodes']-limit for r in rr),depth_min=min(r['metadata']['reported_depth'] for r in rr),depth_max=max(r['metadata']['reported_depth'] for r in rr)))
pairs=[]
for name in D['profiles']:
 for f in D['roots']:
  rr=[r for r in X['rows'] if r['profile']==name and r['root']==f['id']];pairs.append(dict(profile=name,root=f['id'],moves={str(r['metadata']['nodes_limit']):r['move'] for r in rr},changes=len({r['move'] for r in rr})>1))
out=dict(complete=True,actual_queries_checked=checks,cold_leaf_probes=checks*5,groups=groups,node_curve_changed_root_price_groups=sum(z['changes'] for z in pairs),pairs=pairs,seconds=time.monotonic()-start,scope='Fullhistory, legalchoice/allreportedPVs, exacttableack/5evalreadbacks; reporteddepth selectivemature notuniformfiniteD. Nodeovershootsactualretained; no strength orhumanlearningclaim; commonmachineconcurrencyallowed.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='pairs'},indent=2))
