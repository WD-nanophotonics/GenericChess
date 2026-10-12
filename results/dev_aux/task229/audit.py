import json,math,time,importlib.util,sys
from pathlib import Path
import chess,numpy as np
R=Path.cwd();O=R/'results/dev_aux/task229';O.mkdir(exist_ok=True);D=json.loads((R/'results/dev_aux/task228/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task228/result.json').read_bytes());assert X['complete'];decl=dict(task_id='229',question='Independentlyverify all12NativeD2scores/actionargmax underpurematerialrules.',source='228frozen3roots/all4prices, completeorthodox2ply enumeration, rootfullhistory retained.',scope='Checkmate/stalemate anchored, project history/no-progress/insufficient scopeexplicit; nonprojectdrawleafcountrecorded. D3completed not independentlyvalueprovedbyD2oracle; no sourcepatch/training.')
assert json.loads((O/'declaration.json').read_bytes())==decl
sys.path.insert(0,str(R))
from generic_chess.ai.evaluation.config import MATE_SCORE
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);started=time.monotonic();rows=[];leaves=0;otherdraw=0
for oi,f in enumerate(D['roots']):
 b=P.board(f);col=b.turn
 for profile,w in D['profiles'].items():
  results=[]
  for move in sorted(b.legal_moves,key=lambda z:z.uci()):
   b.push(move)
   def value(ply):
    global otherdraw,leaves
    leaves+=1
    if b.is_checkmate():return MATE_SCORE-ply if b.turn!=col else -MATE_SCORE+ply
    if b.is_stalemate():return 0
    otherdraw+=bool(b.outcome(claim_draw=False) and not b.is_checkmate() and not b.is_stalemate())
    return sum(w[k]*(len(b.pieces(i+1,col))-len(b.pieces(i+1,not col))) for i,k in enumerate('PNBRQ'))
   if b.is_checkmate() or b.is_stalemate():v=value(1)
   else:
    vv=[]
    for reply in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(reply);vv.append(value(2));b.pop()
    v=min(vv)
   b.pop();results.append(dict(move=move.uci(),value=v))
  best=max(z['value'] for z in results);argmax=[z['move'] for z in results if z['value']==best];actual=next(z for z in X['rows'] if z['root']==oi and z['profile']==profile and z['requested_depth']==2);assert actual['decision']['score']==best and actual['action_uci'] in argmax
  rows.append(dict(root=oi,profile=profile,score=best,argmax=argmax,actual_action=actual['action_uci'],all_root_actions=results))
summary=dict(complete=True,checked=len(rows),leaf_evaluations=leaves,nonproject_draw_leaf_visits=otherdraw,seconds=time.monotonic()-started,rows=rows,scope=decl['scope']);(O/'audit.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print({k:summary[k] for k in ('complete','checked','leaf_evaluations','nonproject_draw_leaf_visits','seconds')})
Q=R/'results/dev_aux/task230';Q.mkdir();C=json.loads((R/'results/dev_aux/task214/controller.json').read_bytes());M=json.loads((R/'results/dev_aux/task223/models.json').read_bytes());count=0
for model in M['models']:
 src=next(r for r in C['runs'] if r['seed']==model['seed'] and r['mode']=='fixed_teacher');theta=np.array(src['initial_theta']);expected=[];unknown=[]
 for c in C['calls']:
  q=c['context'];r=c['result']
  if q['phase']!='train' or q['seed']!=model['seed'] or q['mode']!='fixed_teacher':continue
  b=chess.Board(r['root_fen'])
  for text in r['opening_history']:b.push_uci(text)
  states=[]
  for ply,text in enumerate(r['actions']):
   if b.turn==r['agent_color']:states.append((ply,[len(b.pieces(t,r['agent_color']))-len(b.pieces(t,not r['agent_color'])) for t in range(1,6)]))
   b.push_uci(text)
  term=b.outcome(claim_draw=False)
  if term is None:unknown.append(q['name']);continue
  y=0 if term.winner is None else (1 if term.winner==r['agent_color'] else -1)
  for ply,f in states:
   u=model['updates'][len(expected)];assert (q['name'],ply,f,y)==(u['game'],u['ply'],u['features'],u['target']);v=math.tanh((f[0]+np.dot(f[1:],np.exp(theta)))/4);g=(1-v*v)/4*np.array(f[1:])*np.exp(theta);alpha=.02/max(1,float(g@g));assert np.max(abs(theta-np.array(u['before'])))<1e-12;theta=np.clip(theta+alpha*(y-v)*g,math.log(.25),math.log(16));assert np.max(abs(theta-np.array(u['after'])))<1e-12;assert u['loss_after']<=u['loss_before']+1e-12;expected.append(u);count+=1
 assert unknown==model['excluded_unknown_games'];assert np.max(abs(theta-np.array(model['final_theta'])))<1e-12;assert len(expected)==len(model['updates'])
(Q/'audit.json').write_text(json.dumps(dict(complete=True,models=3,updates=count,actualroot_features_reconstructed=True,unknown_games_excluded=True,no_searchscores_used=True),indent=2),encoding='utf-8');print('terminalfit independentlyverified',count)
