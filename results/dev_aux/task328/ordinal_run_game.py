def run_game(e,weights,f,color,seed,limit,deadline,configure,cap=48,journal=None):
 probes,ack=configure(e,weights);b=chess.Board(f['initial_fen'])
 for u in f['history']:b.push_uci(u)
 assert b.fen()==f.get('expected_fen',f.get('fen'));random_turn=0;actions=[];searches=[];random_choices=[];ts=time.monotonic()
 for ply in range(cap):
  Q.P.A.guard(deadline,Q.P.stop)
  if b.is_game_over(claim_draw=False):break
  if b.turn==color:
   e.send('ucinewgame');e.ready();m,meta=Q.P.M.M.search(e,b.copy(stack=True),deadline,Q.P.stop,limit=limit);searches.append(dict(ply=ply,record=meta))
   if journal is not None:journal.write(json.dumps(dict(event='query',ply=ply,record=meta),separators=(',',':'))+'\n');journal.flush()
  else:
   legal=sorted(b.legal_moves,key=lambda m:m.uci());rng=random.Random(str(seed)+":"+str(random_turn));ix=rng.randrange(len(legal));random_turn+=1;m=legal[ix];random_choices.append(dict(ply=ply,index=ix,legal_count=len(legal),move=m.uci()))
  assert m in b.legal_moves;b.push(m);actions.append(m.uci())
 oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if oo is None or oo.winner is None else 1 if oo.winner==color else -1;reward=Fraction(49-len(actions),48) if kind=='CHECKMATE' and sign==1 else Fraction(-1) if kind=='CHECKMATE' and sign==-1 else Fraction(0)
 return dict(weights=weights,color=color,seed=seed,actions=actions,search_records=searches,random_choices=random_choices,final_fen=b.fen(),termination=kind,winner=None if oo is None else oo.winner,finite_mate_sign=sign if kind=='CHECKMATE' else 0,fitness=str(reward),seconds=time.monotonic()-ts,leaf_probes=probes,table_ack=ack)
