"""Independent full-window no-TT D3 oracle for actual325 Native queries, second sparse decoder."""
import json,time,sys,hashlib,importlib.util,random
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task326'
CONST='$dev_aux_constant_telemetry_v1';SPARSE='$dev_aux_sparse_telemetry_v1'
def hook(z):
 if set(z)=={CONST}:v=z[CONST];assert type(v['count']) is int;return [v['value'] for _ in range(v['count'])]
 if set(z)=={SPARSE}:
  v=z[SPARSE];a=[v['default'] for _ in range(v['count'])];seen=set()
  for i,x in v['entries']:assert 0<=i<len(a) and i not in seen;seen.add(i);a[i]=x
  return a
 return z
def canonical(z):return json.dumps(z,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def execute():
 O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task325/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task325/result.json').read_bytes());rows=[json.loads(l,object_hook=hook) for l in (R/'results/dev_aux/task325/games.jsonl').read_bytes().splitlines()];assert len(rows)==X['actual_games'];start=time.monotonic();visits=0;checks=[];cache={};sp=importlib.util.spec_from_file_location('p326',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);P.stop();out=dict(complete=False)
 def save():out.update(queries_checked=len(checks),oracles=len(cache),visits=visits,seconds=time.monotonic()-start,checks=checks);P.A.atomic_json(O/'audit.json',out)
 def oracle(b,w):
  side=b.turn
  def terminal():return b.is_checkmate() or b.is_stalemate() or b.is_fivefold_repetition()
  def value(p):
   if terminal():
    oo=b.outcome(claim_draw=False);return 0 if oo.winner is None else 100000000-p if oo.winner==side else -100000000+p
   return sum(w[k]*(len(b.pieces(i+1,side))-len(b.pieces(i+1,not side))) for i,k in enumerate('PNBRQ'))
  def ordered():return sorted(b.legal_moves,key=lambda m:(not b.is_capture(m),m.uci()))
  def ab(d,p,lo,hi):
   nonlocal visits
   visits+=1
   if visits%2048==0:P.A.guard(start+1200,P.stop)
   if not d or terminal():return value(p)
   maximize=b.turn==side;best=-10**9 if maximize else 10**9
   for m in ordered():
    b.push(m);v=ab(d-1,p+1,lo,hi);b.pop()
    if maximize:best=max(best,v);lo=max(lo,best)
    else:best=min(best,v);hi=min(hi,best)
    if lo>=hi:break
   return best
  vals={}
  for m in ordered():b.push(m);vals[m.uci()]=ab(2,1,-10**9,10**9);b.pop()
  return max(vals.values()),vals
 journal=[json.loads(l,object_hook=hook) for l in (R/'results/dev_aux/task325/queries.jsonl').read_bytes().splitlines()];assert len(journal)==X['actual_queries']
 for i,z in enumerate(journal):assert z['sequence']==i+1 and hashlib.sha256(canonical(z['record']['result'])).hexdigest()==z['record']['raw_sha256']
 try:
  for gi,z in enumerate(rows):
   f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
   for u in f['history']:b.push_uci(u)
   ss={v['ply']:v for v in z['search_records']};rs={v['ply']:v for v in z['random_choices']};rng=random.Random(z['seed'])
   for ply,text in enumerate(z['actions']):
    assert not b.is_game_over(claim_draw=False);m=chess.Move.from_uci(text);assert m in b.legal_moves
    if b.turn==z['color']:
     rr=ss[ply];raw=rr['result'];assert hashlib.sha256(canonical(raw)).hexdigest()==rr['raw_sha256'];assert rr['root_fen']==b.fen() and rr['full_history']==[m.uci() for m in b.move_stack] and rr['weights']==z['weights'];key=(f['initial_fen'],tuple(rr['full_history']),tuple(z['weights'][k] for k in 'PNBRQK'))
     if key not in cache:cache[key]=oracle(b,z['weights'])
     best,vals=cache[key];assert raw['score']==best and vals[text]==best and raw['completed_depth']==3 and not raw['used_fallback'] and raw['root_window_pruning'];c=b.copy(stack=True);side=c.turn;pv=[]
     for a in raw['principal_variation']:
      fr=a['from_square'];to=a['to_square'];u=chess.square_name(chess.square(fr['file'],fr['rank']))+chess.square_name(chess.square(to['file'],to['rank']))+(a.get('promotion_target_id') or '').lower();assert chess.Move.from_uci(u) in c.legal_moves;c.push_uci(u);pv.append(u)
     term=c.is_checkmate() or c.is_stalemate() or c.is_fivefold_repetition();oo=c.outcome(claim_draw=False) if term else None;literal=(0 if oo.winner is None else 100000000-len(pv) if oo.winner==side else -100000000+len(pv)) if term else sum(z['weights'][k]*(len(c.pieces(i+1,side))-len(c.pieces(i+1,not side))) for i,k in enumerate('PNBRQ'));assert len(pv)==3 or term;assert literal==best;checks.append(dict(game=gi,ply=ply,profile=z['profile'],action=text,score=best,argmax=[u for u,v in vals.items() if v==best],PV_leaf=literal))
    else:
     legal=sorted(b.legal_moves,key=lambda m:m.uci());ix=rng.randrange(len(legal));assert rs[ply]==dict(ply=ply,index=ix,legal_count=len(legal),move=legal[ix].uci()) and legal[ix]==m
    b.push(m)
   assert b.fen()==z['final_fen'];oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if oo is None or oo.winner is None else 1 if oo.winner==z['color'] else -1;goal=F(49-len(z['actions']),48) if kind=='CHECKMATE' and sign==1 else F(-1) if kind=='CHECKMATE' and sign==-1 else F(0);assert kind==z['termination'] and str(goal)==z['fitness']
   if gi%16==0:save();print(gi,len(checks),visits,round(time.monotonic()-start,2),flush=True)
  out.update(complete=True,completed_games_replayed=len(rows),actual_queries_journal_hashchecked=len(journal),queries_in_completed_games=sum(len(z['search_records']) for z in rows),producer_complete=X['complete'],scope='Allcompletegamequeries fullrootaction exactD3/noTT/FIDE5foldsearch semantics, seconddecoder hashes checked. Ifproducerfailed, partialattemptqueries rawhashqualified only, not mistaken ascompleted/valuequalified. No-progress/insufficientmaterial notNativeinternalterminal; externalfullgameFIDEresultseparate. Differentbackend/resource budgetsnotcausality.');save();print('COMPLETE',len(checks),out['seconds'])
 except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
if __name__=='__main__':execute()