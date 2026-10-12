import json,time,hashlib
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task284';D=json.loads((R/'results/dev_aux/task283/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task283/result.json').read_bytes());T=json.loads((R/'results/dev_aux/task258/tree.json').read_bytes());assert X['complete'] and len(X['rows'])==64;start=time.monotonic();TAG='$dev_aux_constant_telemetry_v1'
def decode(v):
 if isinstance(v,dict):
  if set(v)=={TAG}:a=v[TAG];return [a['value']]*a['count']
  return {k:decode(z) for k,z in v.items()}
 if isinstance(v,list):return [decode(z) for z in v]
 return v
rows=[]
for z in X['rows']:
 f=next(f for f in D['roots'] if f['id']==z['root']);tree=next(t for t in T['roots'] if t['root']==z['root']);w=z['weights'];raw=decode(z['result']);actor=chess.Board(f['fen']).turn
 def value(ld):return ld['terminal'] if 'terminal' in ld else sum(w[k]*v for k,v in zip('PNBRQ',ld['vector']))
 scores={a['move']:min(value(br['terminal']) if 'terminal' in br else max(value(ch['leaf']) for ch in br['children']) for br in a['branches']) for a in tree['actions']};best=max(scores.values());argmax=[m for m,v in scores.items() if v==best];assert raw['completed_depth']==3 and raw['score']==best and z['action'] in argmax and raw['root_window_pruning']==z['arm']['root'] and not raw['used_fallback'];b=chess.Board(f['initial_fen'])
 for text in f['history']:b.push_uci(text)
 pv=[]
 for ac in raw['principal_variation']:
  a=ac['from_square'];d=ac['to_square'];text=chess.square_name(chess.square(a['file'],a['rank']))+chess.square_name(chess.square(d['file'],d['rank']));p=ac.get('promotion_target_id');text+=p.lower() if p else '';m=chess.Move.from_uci(text);assert m in b.legal_moves;b.push(m);pv.append(text)
 oo=b.outcome(claim_draw=False);literal=(0 if oo.winner is None else (100000000-len(pv) if oo.winner==actor else -100000000+len(pv))) if oo is not None else sum(w[k]*(len(b.pieces(i+1,actor))-len(b.pieces(i+1,not actor))) for i,k in enumerate('PNBRQ'));full=len(pv)==3 or oo is not None
 rows.append(dict(root=z['root'],profile=z['profile'],arm=z['arm'],score=best,action=z['action'],argmax=argmax,pv=pv,full_PV=full,literal_PV_leaf=literal,literal_matches_return=full and literal==best,caller_seconds=z['seconds'],nodes=raw['nodes'],tt_hits=raw['tt_hits']))
for z in rows:
 if z['arm']['root']:assert z['literal_matches_return'],'ActualpublicRootTruebadPV'
groups=[]
for arm in D['arms']:
 rr=[z for z in rows if z['arm']==arm];groups.append(dict(arm=arm,queries=len(rr),caller_seconds=sum(z['caller_seconds'] for z in rr),nodes=sum(z['nodes'] for z in rr),PV_full_and_value_matches=sum(z['literal_matches_return'] for z in rr),tt_hits=sum(z['tt_hits'] for z in rr)))
pairs=[]
for f in D['roots']:
 for p in D['profiles']:
  rr=[z for z in rows if z['root']==f['id'] and z['profile']==p];assert len(rr)==4;assert len({z['score'] for z in rr})==1;pairs.append(dict(root=f['id'],profile=p,same_score=True,same_action=len({z['action'] for z in rr})==1,same_PV=len({tuple(z['pv']) for z in rr})==1))
out=dict(complete=True,actual_queries=64,all_exact_score_argmax_checks=64,all_legal_PV_checks=64,groups=groups,pairs=pairs,PV_mismatch_records=[z for z in rows if not z['literal_matches_return']],seconds=time.monotonic()-start,source_sha256=hashlib.sha256((R/'results/dev_aux/task283/result.json').read_bytes()).hexdigest(),scope='Samefixedpublicsource/compiler/DLL/leaf/history/3s budget; actualRootMode xcoldTT factor, all64D3complete/finitevalue/argmax. PVtracechecks separatefromvalues; mismatchrecordsretained. Differentnodes/searchalg workdefinitions remain; notisolatedold/newcanonicalpatch orhumanvalueproof. No product/default/UI adoption.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('pairs','PV_mismatch_records')},indent=2));print('PV_MISMATCHES',len(out['PV_mismatch_records']))
