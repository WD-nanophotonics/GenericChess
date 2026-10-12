"""Independent completefinite controls and matchedpolicy summaries."""
import json,random,statistics,time,importlib.util,hashlib
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task198';P=R/'results/dev_aux/task197';D=json.loads((P/'declaration.json').read_bytes());C=json.loads((P/'games.json').read_bytes());M=json.loads((R/'results/dev_aux/task193/games.json').read_bytes());assert C['complete'];sp=importlib.util.spec_from_file_location('G198',R/'results/dev_aux/task104/short_game.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);counts=dict(games=0,moves=0,searches=0,leaf_nodes=0);cache={};hits=0;started=time.monotonic()
def value(b,col,w):
 o=b.outcome(claim_draw=False)
 return (0 if o.winner is None else (1000000 if o.winner==col else -1000000)) if o else sum(w[k]*(len(b.pieces(i+1,col))-len(b.pieces(i+1,not col))) for i,k in enumerate('PNBRQ'))
for c in C['calls']:
 r=c['result'];b=chess.Board(r['root_fen']);w=c['weights'];col=r['agent_color'];rng=random.Random(c['random_seed']);ix=0
 for m in r['opening_history']:b.push_uci(m)
 assert b.fen()==r['opening_fen']==D['roots'][c['opening_index']]['expected_fen']
 for text in r['actions']:
  assert not b.is_game_over(claim_draw=False);m=chess.Move.from_uci(text);assert m in b.legal_moves
  if b.turn==col:
   saved=r['search_records'][ix];assert saved['root_fen']==b.fen() and saved['full_history']==[z.uci() for z in b.move_stack];key=(tuple(w[k] for k in 'PNBRQ'),b.root().fen(),tuple(saved['full_history']))
   if key in cache:rows,n=cache[key];hits+=1
   else:
    rows=[];n=0
    for move in sorted(b.legal_moves,key=lambda z:z.uci()):
     b.push(move)
     if b.is_game_over(claim_draw=False):vals=[value(b,col,w)];n+=1
     else:
      vals=[]
      for reply in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(reply);vals.append(value(b,col,w));n+=1;b.pop()
     b.pop();rows.append(dict(move=move.uci(),worst=min(vals),reply_count=len(vals)))
    cache[key]=(rows,n)
   best=max(z['worst'] for z in rows);assert rows==saved['rows'] and saved['leaf_nodes']==n and saved['value']==best and m.uci()==next(z['move'] for z in rows if z['worst']==best);ix+=1;counts['searches']+=1;counts['leaf_nodes']+=n
  else:assert m==rng.choice(sorted(b.legal_moves,key=lambda z:z.uci()))
  b.push(m);counts['moves']+=1
 assert ix==len(r['search_records']) and b.fen()==r['final_fen'] and G.score(b,col,len(r['actions']),16)==r['score'];counts['games']+=1
pairs=[];components=[]
def summary(g):
 return dict(original=statistics.mean(c['result']['reward'] for c in g),bounded=statistics.mean((0 if c['result']['score']['winner'] is None else (1 if c['result']['score']['winner']==c['result']['agent_color'] else -1)) if c['result']['score']['terminal'] else c['result']['score']['quantity_difference']/15 for c in g),quantity=statistics.mean(c['result']['score']['quantity_difference']/15 for c in g),wins=sum(c['result']['score']['winner']==c['result']['agent_color'] for c in g if c['result']['score']['terminal']),losses=sum(c['result']['score']['winner'] is not None and c['result']['score']['winner']!=c['result']['agent_color'] for c in g if c['result']['score']['terminal']),cutoffs=sum(not c['result']['score']['terminal'] for c in g))
for backend,calls in [('complete2ply',C['calls']),('mature1024',[c for c in M['calls'] if c['opponent']=='random'])]:
 base=summary([c for c in calls if c['profile']=='unit'])
 for profile in D['profiles']:
  g=[c for c in calls if c['profile']==profile];ss=summary(g);components.append(dict(backend=backend,profile=profile,**ss))
  if profile!='unit':pairs.append(dict(backend=backend,profile=profile,paired_mean_deltas={k:ss[k]-base[k] for k in ('original','bounded','quantity')},completed_net_delta=(ss['wins']-ss['losses'])-(base['wins']-base['losses'])))
out=dict(complete=True,counts=counts,cache_hits=hits,seconds=time.monotonic()-started,source_sha256=hashlib.sha256((P/'games.json').read_bytes()).hexdigest(),components=components,paired=pairs,scope='Fullhistory/actuallegality/random/complete2ply controls verified. Exactauditcache includesweights+initialfen+fullhistory; notnewphysicalgame. Sameprofile/root/color/RNG, but algorithm/tree/work differ: backendcomparisons cannotisolate selectiveheuristics orprove equalcoststrength.')
(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('components',)},indent=2))
