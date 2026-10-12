import json,time,sys,random,importlib.util,hashlib
import chess
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R));O=R/'results/dev_aux/task236';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'games.json').exists()
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);P.stop();assert hashlib.sha256((R/'generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest()==D['native_binary_sha256'];start=time.monotonic();c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);out=dict(complete=False,calls=[],queries=[],native_binary_sha256=D['native_binary_sha256'],scope=D['scope']);deadline=start+900

def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'games.json',out)

def block(name,w,phase):
 for opponent in D['opponents']:
  for oi,f in enumerate(D['roots'][phase]):
   for color in (True,False):
    P.A.guard(deadline,P.stop);b=P.board(f);ss=GameSession(c)
    for text in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==text))
    e=SemanticSearchEngine(c,n,board_values=w,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=0);rs=D['random_seed_base'][phase]+oi;rng=random.Random(rs);actions=[];searches=[];oppo=[]
    for ply in range(8):
     P.A.guard(deadline,P.stop)
     if b.is_game_over(claim_draw=False):break
     aa={uci(a):a for a in ss.legal_actions()};assert sorted(aa)==sorted(m.uci() for m in b.legal_moves)
     if b.turn==color:
      before=(ss.state,ss.history,ss.result);t=time.monotonic();v=e.search(ss,SearchLimits(max_depth=2,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=False);assert before==(ss.state,ss.history,ss.result);move=chess.Move.from_uci(uci(v.action));searches.append(dict(ply=ply,full_history=[m.uci() for m in b.move_stack],root_fen=b.fen(),result=record_value(v),wall_seconds=time.monotonic()-t))
     elif opponent=='random':move=rng.choice(sorted(b.legal_moves,key=lambda z:z.uci()))
     else:move,v=P.P.unit2ply(b.copy(stack=True),deadline,P.stop);oppo.append(v)
     assert move in b.legal_moves;ss.submit(aa[move.uci()]);b.push(move);actions.append(move.uci());assert (ss.state.position.side_to_move==0)==b.turn
    score=P.G.score(b,color,len(actions),8);out['calls'].append(dict(name=f'{phase}-{name}-{opponent}-o{oi}-c{int(color)}',phase=phase,profile=name,weights=w,opponent=opponent,opening_index=oi,random_seed=rs,result=dict(root_fen=f['initial_fen'],opening_history=f['history'],opening_fen=f['expected_fen'],agent_color=color,actions=actions,search_records=searches,opponent_records=oppo,final_fen=b.fen(),score=score,reward=score['reward'],generic_terminal=record_value(ss.result))));save()
 print(phase,name,len(out['calls']),round(time.monotonic()-start,3),flush=True)
try:
 for name,w in D['profiles'].items():block(name,w,'train')
 selected={};means={}
 for seed,names in D['seed_profiles'].items():
  vals={name:sum(z['result']['score']['quantity_difference']/15 for z in out['calls'] if z['phase']=='train' and z['profile']==name)/sum(z['phase']=='train' and z['profile']==name for z in out['calls']) for name in names};means[seed]=vals;selected[seed]=max(names,key=lambda k:vals[k])
 import datetime
 endpoints=dict(complete=True,selected=selected,training_means=means,weights={s:D['profiles'][name] for s,name in selected.items()},training_games=len(out['calls']),frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat());P.A.atomic_json(O/'endpoints.json',endpoints);out['endpoints']=endpoints;save()
 held={'unit':D['unit']}
 for seed,name in selected.items():held[f'initial-s{seed}']=D['profiles'][f's{seed}-base'];held[f'selected-s{seed}']=D['profiles'][name]
 for name,w in held.items():block(name,w,'heldout')
 for seed,name in selected.items():
  for label,w in [('initial',D['profiles'][f's{seed}-base']),('selected',D['profiles'][name])]:
   for oi,f in enumerate(D['roots']['heldout']):
    P.A.guard(deadline,P.stop);ss=GameSession(c)
    for text in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==text))
    before=(ss.state,ss.history,ss.result);e=SemanticSearchEngine(c,n,board_values=w,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=0);t=time.monotonic();v=e.search(ss,SearchLimits(max_depth=3,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=False);assert before==(ss.state,ss.history,ss.result);out['queries'].append(dict(seed=seed,label=label,root=oi,weights=w,decision=record_value(v),action_uci=uci(v.action),wall_seconds=time.monotonic()-t));save()
 out['complete']=True;save();print('COMPLETE',len(out['calls']),len(out['queries']),out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
