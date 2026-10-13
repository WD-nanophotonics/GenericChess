import sys,json,random,time,re,hashlib,statistics
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task552';start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
D=json.loads((R/'results/dev_aux/task551/declaration.json').read_bytes());r=json.loads((R/'results/dev_aux/task551/result.json').read_bytes());games=[json.loads(x) for x in (R/'results/dev_aux/task551/games.jsonl').open()];raw=[json.loads(x) for x in (R/'results/dev_aux/task551/queries.jsonl').open()];expected=[];pv=0;draws=0;legalarrays=0;metadata=0
for g in games:
 b,keys,checks,movers=G.full_root(g['root']);h=list(g['root']['history']);qi=0;randomturn=0;rolecounts={}
 for ply,a in enumerate(g['actions']):
  assert G.terminal(b,keys,checks,movers) is None;actor=b.turn;assert a['before_sfen']==b.sfen() and a['actor']==actor;m=A.shogi.Move.from_usi(a['move']);assert m in b.legal_moves
  if actor==g['color'] or any(q['player']=='unit' for q in g['queries']):
   q=g['queries'][qi];qi+=1;assert q['history']==h and q['initial_sfen']==g['root']['initial_sfen'] and q['ply']==ply and q['bestmove']==a['move'];pv+=V.query(q);expected.append(V.bare(q));role=q['player'];assert q['reset_policy']=='warm_game' and q['cold_isready']==[] and q['game_start_ready'][-1]=='readyok' and q['query_index_in_game']==rolecounts.get(role,0);rolecounts[role]=rolecounts.get(role,0)+1
  else:
   legal=sorted(m.usi() for m in b.legal_moves);seed=(D['seed_base']+2*g['root']['index']+g['color'])*100+randomturn;ix=random.Random(seed).randrange(len(legal));assert a['random_draw']==dict(legal=legal,index=ix,seed=seed,opponent_turn=randomturn) and a['move']==legal[ix];randomturn+=1;draws+=1;legalarrays+=1
  cap=b.piece_at(m.to_square);moving=b.piece_at(m.from_square) if m.from_square is not None else None;assert a['captured']==(str(cap) if cap else None) and a['moving']==(str(moving) if moving else None) and a['promotion']==bool(m.promotion) and a['drop']==m.drop_piece_type;metadata+=1;movers.append(actor);b.push(m);h.append(a['move']);keys.append(G.key(b));checks.append(b.is_check());assert a['after_sfen']==b.sfen()
 assert qi==len(g['queries']);term=G.terminal(b,keys,checks,movers);assert g['termination']==(term or dict(kind='cap24',winner=None));qty=G.quantity(b,g['color']);assert qty==g['raw_quantity'];goal=Fraction(qty,19) if term is None else Fraction(0) if term['winner'] is None else Fraction(32 if term['winner']==g['color'] else -32);assert str(goal)==g['goal'] and b.sfen()==g['final_sfen']
assert expected==raw and games==[x['game'] for x in r['rows']]
# Independent exactpriceACK checker inheritedfinite function ONLY.
s=(R/'results/dev_aux/task522/audit.py').read_text();s=s[s.index('def tables('):s.index('nativegames=0')];exec(compile(s,'independentpriceACKtables','exec'));entries=tables(r['price_acks'])
summary=[]
for nodes in D['budgets']:
 for opp in D['opponents']:
  ps=[p for p in r['pairs'] if p['nodes']==nodes and p['opponent']==opp];py=sum(p['game_seconds']['python_rules'] for p in ps);na=sum(p['game_seconds']['native_rules'] for p in ps);summary.append(dict(nodes=nodes,opponent=opp,pairs=len(ps),python_game_seconds=py,native_game_seconds=na,ratio=na/py,median_paired_ratio=statistics.median(p['game_seconds']['native_rules']/p['game_seconds']['python_rules'] for p in ps),all_non_time_equal=all(p['non_time_equal'] for p in ps),bothorders_counts={c:sum(p['order'][0]==c for p in ps) for c in D['controllers']}))
out=dict(status='PASS',actual_games=len(games),actual_go=len(raw),PV_moves=pv,Python_action_metadata=metadata,exact_sorted_random_arrays=legalarrays,random_draws=draws,price_ACK_entries=entries,summary=summary,seconds=time.perf_counter()-start,scope='IndependentPythonrules audit of actualnative-producedgames plusfullrawjournal/reset/priceACK. Cost uses game.seconds endingbeforejournal BOTHcontrollers; outergame_wall confounded by oldrandom extrajournalfsync, notspeedup basis. Ordinaryconcurrency, finite paired standardShogi only; no generaldomain proof/noisefreespeedup.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
