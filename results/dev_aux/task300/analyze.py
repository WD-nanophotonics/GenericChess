import json,time,hashlib,importlib.util
from pathlib import Path
from fractions import Fraction
import chess
R=Path.cwd();O=R/'results/dev_aux/task300';O.mkdir(exist_ok=False);old=json.loads((R/'results/dev_aux/task291/declaration.json').read_bytes());profiles=json.loads((R/'results/dev_aux/task267/declaration.json').read_bytes())['profiles'];W={k:profiles[k] for k in ('semantic','unit','s703-base','s704-base','s705-base')};f=old['root'];b=chess.Board(f['initial_fen'])
for t in f['history']+[old['selected'][0]['first'],old['selected'][0]['reply']]:b.push_uci(t)
D=dict(task_id='300',question='Does a realpromotion branch yield differenttrueBlackmate-by5 goals acrosspositiveprice policies?',initial_fen=f['initial_fen'],history=[m.uci() for m in b.move_stack],parent_fen=b.fen(),forced_first_choices=['e2d1b','e2d1n','e2d1q','e2d1r'],profiles=W,H=5,opponent='Whiteuniform acrossalllegalreplyactions, Blackmax expectedterminal+leafprice; exactFraction means, lexicalties. Mate-goaloracle maximizesindependentBlackmateprobability, candidateprices never definegoal.',terminal='Actualcheckmate(stalemate/automaticfivefolddraw0); terminalprice+-100000000-ply, nonterminalBlackPNBRQdifference. FinitegoalsBlackmate1/Whitemate-1/other0 byfixed5 only, notfinalWDL.',whole_fuse_seconds=600,estimated_cost='Full5ply4forcedpromotions about4Mleafvisits/expected1-5min; stopat600s preservepartialfinishedpromotion; norescue/deepergrowth.',selection='First3promotionchildren291areallONEparent. Addedrookcompletesall4legalpromotionoptions, not3independentstates. Nohumanrules/labels/modelselection; sourcefail280exclusion remains.')
(O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8');assert set(D['forced_first_choices']).issubset({m.uci() for m in b.legal_moves});sp=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);P.stop();start=time.monotonic();visits=0;leaves=0;mateleaves=0;rows=[];out=dict(complete=False,rows=rows)
def save():out.update(seconds=time.monotonic()-start,visits=visits,leaves=leaves,mateleaves=mateleaves);P.A.atomic_json(O/'result.json',out)
def solve(depth,ply):
 global visits,leaves,mateleaves
 visits+=1
 if visits%1024==0:P.A.guard(start+600,P.stop)
 oo=b.outcome(claim_draw=False)
 if depth==0 or oo is not None:
  leaves+=1
  goal=0 if oo is None or oo.winner is None else 1 if oo.winner==False else -1
  if goal:mateleaves+=1
  if oo is not None:v=0 if oo.winner is None else 100000000-ply if oo.winner==False else -100000000+ply;vals=[Fraction(v)]*len(W)
  else:
   vec=[len(b.pieces(i+1,False))-len(b.pieces(i+1,True)) for i in range(5)];vals=[Fraction(sum(w[k]*x for k,x in zip('PNBRQ',vec))) for w in W.values()]
  return vals,[Fraction(goal)]*len(W),Fraction(goal),Fraction(goal==1)
 choices=[]
 for m in sorted(b.legal_moves,key=lambda m:m.uci()):
  b.push(m);res=solve(depth-1,ply+1);b.pop();choices.append(res)
 if b.turn==True:
  nn=len(choices);return [sum(c[0][i] for c in choices)/nn for i in range(len(W))],[sum(c[1][i] for c in choices)/nn for i in range(len(W))],sum(c[2] for c in choices)/nn,sum(c[3] for c in choices)/nn
 ix=[max(range(len(choices)),key=lambda j:choices[j][0][i]) for i in range(len(W))];return [choices[j][0][i] for i,j in enumerate(ix)],[choices[j][1][i] for i,j in enumerate(ix)],max(c[2] for c in choices),max(c[3] for c in choices)
try:
 for text in D['forced_first_choices']:
  ts=time.monotonic();b.push_uci(text);vals,goals,netbest,winbest=solve(4,1);b.pop();rows.append(dict(first=text,expected_price={k:str(v) for k,v in zip(W,vals)},candidate_finite_goal={k:str(v) for k,v in zip(W,goals)},oracle_net_goal=str(netbest),oracle_win_probability=str(winbest),seconds=time.monotonic()-ts));save();print(text,rows[-1],visits,flush=True)
 out['complete']=True;save();print('COMPLETE',out['seconds'],leaves)
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise