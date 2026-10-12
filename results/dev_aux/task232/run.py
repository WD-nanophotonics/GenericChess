import json,time,sys,random,importlib.util,hashlib
import chess
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R));O=R/'results/dev_aux/task232';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'games.json').exists()
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);P.stop();assert hashlib.sha256((R/'generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest()==D['native_binary_sha256'];start=time.monotonic();c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);out=dict(complete=False,calls=[],native_binary_sha256=D['native_binary_sha256'],scope=D['scope']);deadline=start+600

def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'games.json',out)
try:
 for name,w in D['profiles'].items():
  for opponent in D['opponents']:
   for oi,f in enumerate(D['roots']):
    for color in (True,False):
     P.A.guard(deadline,P.stop);b=P.board(f);ss=GameSession(c)
     for text in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==text))
     e=SemanticSearchEngine(c,n,board_values=w,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=0);rng=random.Random(D['random_seeds'][oi]);actions=[];searches=[];oppo=[];mismatch=[]
     for ply in range(8):
      P.A.guard(deadline,P.stop)
      if b.is_game_over(claim_draw=False):break
      aa={uci(a):a for a in ss.legal_actions()};assert sorted(aa)==sorted(m.uci() for m in b.legal_moves)
      if b.turn==color:
       before=(ss.state,ss.history,ss.result);t=time.monotonic();v=e.search(ss,SearchLimits(max_depth=3,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=False);assert before==(ss.state,ss.history,ss.result);move=chess.Move.from_uci(uci(v.action));searches.append(dict(ply=ply,full_history=[m.uci() for m in b.move_stack],root_fen=b.fen(),result=record_value(v),wall_seconds=time.monotonic()-t))
      elif opponent=='random':move=rng.choice(sorted(b.legal_moves,key=lambda z:z.uci()))
      else:move,v=P.P.unit2ply(b.copy(stack=True),deadline,P.stop);oppo.append(v)
      assert move in b.legal_moves;ss.submit(aa[move.uci()]);b.push(move);actions.append(move.uci());assert (ss.state.position.side_to_move==0)==b.turn
     score=P.G.score(b,color,len(actions),8);out['calls'].append(dict(name=f'{name}-{opponent}-o{oi}-c{int(color)}',profile=name,weights=w,opponent=opponent,opening_index=oi,random_seed=D['random_seeds'][oi],result=dict(root_fen=f['initial_fen'],opening_history=f['history'],opening_fen=f['expected_fen'],agent_color=color,actions=actions,search_records=searches,opponent_records=oppo,final_fen=b.fen(),score=score,reward=score['reward'],generic_terminal=record_value(ss.result))));save();print(len(out['calls']),name,opponent,oi,int(color),round(time.monotonic()-start,1),flush=True)
 out['complete']=True;save()
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
