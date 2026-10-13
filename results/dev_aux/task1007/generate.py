from pathlib import Path
import json,random,chess
R=Path.cwd();T=R/'results/dev_aux/task1008';T.mkdir(exist_ok=False);p=json.loads((R/'results/dev_aux/task1007/generation_spec.json').read_bytes());trace=[];roots=[];counts=[0]*4;region=[chess.square(f,r) for r in range(1,6) for f in range(1,6)];types=[[6,2,2,6,4],[6,2,2,2,6,4],[6,4,4,6,2,2],[6,4,2,6,4,2]];colors=[[1,1,1,0,0],[1,1,1,1,0,0],[1,1,1,0,0,0],[1,1,1,0,0,0]]
for i,seed in enumerate(p['seeds']):
 ci=i%4;sq=random.Random(seed).sample(region,len(types[ci]));b=chess.Board(None)
 for s,t,c in zip(sq,types[ci],colors[ci]):b.set_piece_at(s,chess.Piece(t,bool(c)))
 b.turn=not((i//4)%2);legal=sorted(m.uci() for m in b.legal_moves);captures=sorted(m.uci() for m in b.legal_moves if b.is_capture(m));fail=None
 if not b.is_valid():fail='invalid:'+str(b.status())
 elif b.is_game_over():fail='terminal'
 elif len(legal)<2:fail='too_few_moves'
 elif not captures:fail='no_capture'
 else:
  for text in legal:
   b.push_uci(text);mate=b.is_checkmate();b.pop()
   if mate:fail='immediate_mate';break
 row=dict(index=i,seed=seed,squares=sq,fen=b.fen(),legal=legal,captures=captures,failure=fail,composition=p['compositions'][ci],types=types[ci],colors=colors[ci]);trace.append(row)
 if fail is None and counts[ci]<16:roots.append(dict(row,ordinal=len(roots),composition_ordinal=counts[ci],phase='new_replication'));counts[ci]+=1
assert counts==[16]*4;(T/'roots.json').write_text(json.dumps(dict(roots=roots,trace=trace),indent=2),encoding='utf-8');print('NEW_ROOTS',len(roots),'eligible',sum(r['failure'] is None for r in trace))
