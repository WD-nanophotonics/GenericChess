import json,time,hashlib,importlib.util,sys
from pathlib import Path
import chess
R=Path.cwd();sys.path.insert(0,str(R));O=R/'results/dev_aux/task288';O.mkdir(exist_ok=True);D=json.loads((R/'results/dev_aux/task287/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task287/result.json').read_bytes());assert X['complete'];start=time.monotonic();TAG='$dev_aux_constant_telemetry_v1'
def hook(d):
 if set(d)=={TAG}:z=d[TAG];return [z['value']]*z['count']
 return d
sp=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);P.stop()
rows=json.loads((R/'results/dev_aux/task287/result.json').read_bytes(),object_hook=hook)['calls'];cache={};visits=0;checks=[]
def canonical(z):return json.dumps(z,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
for i,z in enumerate(json.loads(line) for line in (R/'results/dev_aux/task287/journal.jsonl').read_bytes().splitlines()):assert z['sequence']==i and hashlib.sha256(canonical(z['record'])).hexdigest()==z['sha256']
def oracle(b,w,depth):
 side=b.turn;scorelist={}
 def value(p):
  oo=b.outcome(claim_draw=False) if b.is_checkmate() or b.is_stalemate() else None
  if oo:return (0 if oo.winner is None else 100000000-p if oo.winner==side else -100000000+p)
  return sum(w[k]*(len(b.pieces(i+1,side))-len(b.pieces(i+1,not side))) for i,k in enumerate('PNBRQ'))
 def ordered():return sorted(b.legal_moves,key=lambda m:(not b.is_capture(m),m.uci()))
 def ab(d,p,lo,hi):
  global visits
  visits+=1
  if visits%1024==0:P.A.guard(start+600,P.stop)
  if not d or b.is_checkmate() or b.is_stalemate():return value(p)
  maximize=b.turn==side;best=-10**9 if maximize else 10**9
  for m in ordered():
   b.push(m);v=ab(d-1,p+1,lo,hi);b.pop()
   if maximize:best=max(best,v);lo=max(lo,best)
   else:best=min(best,v);hi=min(hi,best)
   if lo>=hi:break
  return best
 for m in ordered():b.push(m);scorelist[m.uci()]=ab(depth-1,1,-10**9,10**9);b.pop()
 best=max(scorelist.values());return dict(best=best,argmax=[m for m,v in scorelist.items() if v==best],action_scores=scorelist)
for gi,z in enumerate(rows):
 f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
 for t in f['history']:b.push_uci(t)
 for ply,text in enumerate(z['actions']):
  rr=z['search_records'][ply];raw=rr['result'];assert rr['root_fen']==b.fen() and rr['full_history']==[m.uci() for m in b.move_stack];assert rr['weights']==D['profiles'][rr['profile']];key=(tuple(rr['full_history']),tuple(rr['weights'][k] for k in 'PNBRQ'))
  if key not in cache:cache[key]=oracle(b,rr['weights'],3)
  ref=cache[key];assert raw['score']==ref['best'] and text in ref['argmax'] and raw['completed_depth']==3 and not raw['used_fallback'] and raw['root_window_pruning']==True,(gi,ply,raw['score'],ref)
  pvboard=b.copy(stack=True);actor=b.turn;pv=[]
  for a in raw['principal_variation']:
   fr=a['from_square'];to=a['to_square'];t=chess.square_name(chess.square(fr['file'],fr['rank']))+chess.square_name(chess.square(to['file'],to['rank']))+(a.get('promotion_target_id') or '').lower();m=chess.Move.from_uci(t);assert m in pvboard.legal_moves;pvboard.push(m);pv.append(t)
  oo=pvboard.outcome(claim_draw=False) if pvboard.is_checkmate() or pvboard.is_stalemate() else None;literal=(0 if oo.winner is None else 100000000-len(pv) if oo.winner==actor else -100000000+len(pv)) if oo is not None else sum(rr['weights'][k]*(len(pvboard.pieces(i+1,actor))-len(pvboard.pieces(i+1,not actor))) for i,k in enumerate('PNBRQ'));assert len(pv)==3 or oo is not None;assert literal==raw['score']
  checks.append(dict(game=gi,ply=ply,profile=rr['profile'],score=ref['best'],argmax=ref['argmax'],action=text,PV_leaf=literal));b.push_uci(text)
 assert b.fen()==z['final_fen'];oo=b.outcome(claim_draw=False);tag='unknown' if oo is None else 'draw' if oo.winner is None else 'win' if oo.winner==z['color'] else 'loss';assert tag==z['outcome'];print(gi,tag,len(checks),visits,round(time.monotonic()-start,3),flush=True)
out=dict(complete=True,actual_games_replayed=len(rows),actual_queries_checked=len(checks),independent_D3_oracles=len(cache),oracle_visits=visits,all_legal_history_score_argmax_PV_pass=True,checks=checks,seconds=time.monotonic()-start,actual_search_rules=dict(repetition_limit=100000,max_ply=1000,no_progress_draw=None,insufficient_material_draw=False),external_game_outcome='python-chess automaticFIDEdraw; distinctfromsearchterminal',scope='Independent python-chess full-history noTT alpha-beta fixedD3 with every rootaction exact fullwindow value, legalPV literal score; does not establish canonical tieordering, generalrules or machineexclusivity.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('COMPLETE',len(checks),out['seconds'])