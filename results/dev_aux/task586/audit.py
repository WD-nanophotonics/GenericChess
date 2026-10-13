import json,sys,time,random,hashlib,itertools
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task586';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task583/declaration.json').read_bytes());freeze=json.loads((R/'results/dev_aux/task583/roots_frozen.json').read_bytes());start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
s=(R/'results/dev_aux/task522/audit.py').read_text();exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'independentcurriculumACK','exec'))
counts=dict(games=0,actual_go=0,PV_moves=0,Python_actions=0,random_draws=0,price_ACK_entries=0);summ=[];setups=[]
for task,cap,seedbase in [(584,48,d['setup_seed_base']),(585,12,d['probe_seed_base'])]:
 r=json.loads((R/f'results/dev_aux/task{task}/result.json').read_bytes());raw=iter((R/f'results/dev_aux/task{task}/queries.jsonl').open());seen=set()
 for gi,line in enumerate((R/f'results/dev_aux/task{task}/games.jsonl').open(),1):
  g=json.loads(line);f=g['root'];w=d['setup_weights'] if task==584 else d['profiles'][g['profile']]['weights'];assert g['weights']==w
  if task==584:assert f['seed']==d['input_policy']['seeds'][f['index']] and not f['history'];setups.append(g)
  else:assert f==freeze['roots'][f['index']]
  b,keys,checks,movers=G.full_root(f);h=list(f['history']);qi=0;ri=0
  for ply,a in enumerate(g['actions']):
   assert G.terminal(b,keys,checks,movers) is None;actor=b.turn;m=A.shogi.Move.from_usi(a['move']);assert m in b.legal_moves and a['before_sfen']==b.sfen() and a['actor']==actor
   if actor==g['color']:
    q=g['queries'][qi];qi+=1;assert q['player']=='candidate' and q['weights']==w and q['ply']==ply and q['history']==h and q['initial_sfen']==f['initial_sfen'] and q['bestmove']==a['move'] and q['nodes_limit']==1024 and q['command']=='go nodes 1024';assert V.bare(q)==json.loads(next(raw));assert q['reset_policy']=='warm_game' and q['cold_isready']==[] and q['game_start_ready'][-1]=='readyok' and q['query_index_in_game']==qi-1;v=A.material(b,w);st=q['state'].split(' ',7);assert int(st[3])==int(st[4])==v and int(st[5])==(v if actor==0 else -v);counts['PV_moves']+=V.query(q);counts['actual_go']+=1
   else:
    legal=sorted(m.usi() for m in b.legal_moves);seed=(seedbase+2*f['index']+g['color'])*100+ri;ix=random.Random(seed).randrange(len(legal));assert a['random_draw']==dict(legal=legal,index=ix,seed=seed,opponent_turn=ri) and a['move']==legal[ix];ri+=1;counts['random_draws']+=1
   captured=b.piece_at(m.to_square);p=b.piece_at(m.from_square) if m.from_square is not None else None;assert a['captured']==(str(captured) if captured else None) and a['moving']==(str(p) if p else None) and a['promotion']==bool(m.promotion) and a['drop']==m.drop_piece_type;movers.append(actor);b.push(m);h.append(a['move']);keys.append(G.key(b));checks.append(b.is_check());assert a['after_sfen']==b.sfen();counts['Python_actions']+=1
  assert qi==len(g['queries']);t=G.terminal(b,keys,checks,movers);assert len(g['actions'])==cap or t is not None;assert g['termination']==(t or dict(kind=f'cap{cap}',winner=None));qty=G.quantity(b,g['color']);goal=Fraction(qty,19) if t is None else Fraction(0) if t['winner'] is None else Fraction(32 if t['winner']==g['color'] else -32);assert g['goal']==str(goal) and g['raw_quantity']==qty and g['final_sfen']==b.sfen();counts['games']+=1
  cell=(f['index'],g['color']) if task==584 else (g['profile'],f['index'],g['color']);assert cell not in seen;seen.add(cell);row=r['rows'][gi-1];assert row['source']['line']==gi and row['termination']==g['termination'] and row['plies']==len(g['actions']) and row['go']==qi
  if task==585:assert row['goal']==g['goal'] and row['profile']==g['profile'] and row['offset']==f['offset'] and row['source_family']==f['source_family']
 assert next(raw,None) is None;assert seen==set(itertools.product(range(8),[0,1])) if task==584 else seen==set(itertools.product(range(10),range(len(freeze['roots'])),[0,1]));counts['price_ACK_entries']+=tables(r['price_acks']);summ.append(dict(task=task,games=r['actual_games'],go=r['actual_go']))
# Independently reconstruct ALL eligibility, offsets and unavailable reasons from actual setup games.
expected=[];missing=[]
for line,g in enumerate(setups,1):
 f=g['root'];seed=f['seed'];c=g['color']
 if g['termination']['kind']!='checkmate':missing.append(dict(family=seed,unit_color=c,reason='no_mate_within48',termination=g['termination'],plies=len(g['actions'])));continue
 for offset in d['input_policy']['offsets']:
  n=len(g['actions'])-offset
  if n<0:missing.append(dict(family=seed,unit_color=c,offset=offset,reason='mate_before_offset'));continue
  hist=[a['move'] for a in g['actions'][:n]];sf=g['actions'][n-1]['after_sfen'] if n else f['initial_sfen'];root=dict(index=len(expected),seed=seed,phase='curriculum_probe',initial_sfen=f['initial_sfen'],history=hist,expected_sfen=sf,source_family=seed,setup_color=c,offset=offset,setup_source=dict(file='results/dev_aux/task584/games.jsonl',line=line),setup_mate_winner=g['termination']['winner']);b,k,cc,mm=G.full_root(root);assert G.terminal(b,k,cc,mm) is None;expected.append(root)
assert expected==freeze['roots'] and missing==freeze['unavailable'];assert freeze['before_any_price_probe'];out=dict(status='PASS',counts=counts,stages=summ,eligible_roots=len(expected),eligible_families=len({f['source_family'] for f in expected}),unavailable=len(missing),source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for task in [583,584,585] for p in (R/f'results/dev_aux/task{task}').glob('*.json*')},seconds=time.perf_counter()-start,new_go=0,scope='ALLsetup/probe/Pythonrules/fullhistory/material/PV/RNG/ACK/reset/coverage AND actualeligibility+unavailable reconstruction. Curriculum generator biased, offsetsnot independent, no learning or heldoutfit.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))