import json,time,sys,importlib.util,hashlib
from pathlib import Path
import chess
R=Path.cwd();sys.path.insert(0,str(R));O=R/'results/dev_aux/task238';O.mkdir(exist_ok=True);source=R/'results/dev_aux/task236/games.json';X=json.loads(source.read_bytes());D=json.loads((R/'results/dev_aux/task236/declaration.json').read_bytes());assert X['complete'];decl=dict(task_id='238',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),question='CheckeveryrecordedD2candidatechoice/value byindependentcompleteorthodoxminimax, notPVlegality alone.',scope='Allactual236agent roots/history/candidate weights; projectmate/stalemate, otherautomaticdrawleafvisitsrecorded. PurefiniteD2only, no widergameclaims; rawtrajectorysource frozen beforeaudit.');(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8')
from generic_chess.ai.evaluation.config import MATE_SCORE
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);start=time.monotonic();cache={};checks=[];leaves=otherdraw=0
for c in X['calls']:
 b=P.board(D['roots'][c['phase']][c['opening_index']]);si=0;w=c['weights'];actor=c['result']['agent_color']
 for ply,text in enumerate(c['result']['actions']):
  if b.turn==actor:
   raw=c['result']['search_records'][si]['result'];key=(b.fen(),tuple(m.uci() for m in b.move_stack),tuple(w[k] for k in 'PNBRQ'));si+=1
   if key in cache:best,argmax=cache[key]
   else:
    side=b.turn;rows=[]
    def value(ply):
     global leaves,otherdraw
     leaves+=1
     if b.is_checkmate():return MATE_SCORE-ply if b.turn!=side else -MATE_SCORE+ply
     if b.is_stalemate():return 0
     otherdraw+=b.outcome(claim_draw=False) is not None
     return sum(w[k]*(len(b.pieces(i+1,side))-len(b.pieces(i+1,not side))) for i,k in enumerate('PNBRQ'))
    for cand in sorted(b.legal_moves,key=lambda z:z.uci()):
     b.push(cand)
     if b.is_checkmate() or b.is_stalemate():v=value(1)
     else:
      vv=[]
      for reply in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(reply);vv.append(value(2));b.pop()
      v=min(vv)
     b.pop();rows.append((cand.uci(),v))
    best=max(v for m,v in rows);argmax=[m for m,v in rows if v==best];cache[key]=best,argmax
   assert raw['completed_depth']==2 and raw['score']==best and text in argmax,(c['name'],ply,raw['score'],best,text,argmax)
   checks.append(dict(game=c['name'],ply=ply,score=best,argmax=argmax,actual=text))
  b.push_uci(text)
 P.stop()
out=dict(complete=True,actual_agent_root_checks=len(checks),unique_history_price_queries=len(cache),leaves=leaves,nonproject_draw_leaf_visits=otherdraw,seconds=time.monotonic()-start,checks=checks,scope=decl['scope']);(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:out[k] for k in ('complete','actual_agent_root_checks','unique_history_price_queries','leaves','nonproject_draw_leaf_visits','seconds')})
