import json,time,hashlib,importlib.util
from pathlib import Path
from fractions import Fraction
import chess
R=Path.cwd();O=R/'results/dev_aux/task304';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task300/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task300/result.json').read_bytes());assert X['complete'];sp=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);P.stop();start=time.monotonic();b=chess.Board(D['initial_fen'])
for t in D['history']:b.push_uci(t)
assert b.fen()==D['parent_fen'];visits=0;leaves=0;white_mates=0;black_mates=0;witnesses=[]
def goal(depth,path):
 global visits,leaves,white_mates,black_mates
 visits+=1
 if visits%4096==0:P.A.guard(start+600,P.stop)
 # Independentgoalonly recursion, no prices/material/PVscore.
 if b.is_checkmate():
  sign=1 if b.turn==True else -1;black_mates+=sign==1;white_mates+=sign==-1
  if sign==1 and len(witnesses)<12:witnesses.append(dict(path=path.copy(),fen=b.fen()))
  leaves+=1;return Fraction(sign),Fraction(sign==1)
 if not depth or b.is_stalemate() or b.is_insufficient_material() or b.is_fivefold_repetition() or b.is_seventyfive_moves():leaves+=1;return Fraction(0),Fraction(0)
 values=[]
 for m in sorted(b.legal_moves,key=lambda m:m.uci()):b.push(m);values.append(goal(depth-1,path+[m.uci()]));b.pop()
 if b.turn==False:return max(v[0] for v in values),max(v[1] for v in values)
 return sum(v[0] for v in values)/len(values),sum(v[1] for v in values)/len(values)
rows=[];out=dict(complete=False,rows=rows)
def save():out.update(seconds=time.monotonic()-start,visits=visits,leaves=leaves,black_mate_leaves=black_mates,white_mate_leaves=white_mates,witnesses=witnesses);P.A.atomic_json(O/'audit.json',out)
try:
 for first in D['forced_first_choices']:
  b.push_uci(first);replies=[];legal=[m.uci() for m in sorted(b.legal_moves,key=lambda m:m.uci())]
  for text in legal:b.push_uci(text);net,win=goal(3,[first,text]);b.pop();replies.append(dict(White_reply=text,conditional_best_net=str(net),conditional_best_win=str(win)))
  b.pop();net=sum(Fraction(z['conditional_best_net']) for z in replies)/len(replies);win=sum(Fraction(z['conditional_best_win']) for z in replies)/len(replies);ref=next(z for z in X['rows'] if z['first']==first);assert str(net)==ref['oracle_net_goal'] and str(win)==ref['oracle_win_probability'];rows.append(dict(first=first,White_legal_replies=legal,goal_oracle_net=str(net),goal_oracle_win=str(win),reply_contributions=replies));save();print(first,str(net),str(win),legal,visits,round(time.monotonic()-start,3),flush=True)
 out['complete']=True;out['scope']='Independentgoal-only max/mean actualrules oracle4promotions; pricepolicygoals remainproducer300 (coincidewithindependentlyvalidatedupperbound). Noassertallpolicychoicesindependentlyreplayed. RareRwinningreply notgeneralR>Qmaterialvalue; randomopponentdistributiondepends onactuallegalset/checkcapability.';save();print('COMPLETE',out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise