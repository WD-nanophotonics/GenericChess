import json,time,sys,random,copy,hashlib,importlib.util
import chess
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R));O=R/'results/dev_aux/task252';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'result.json').exists()
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);P.stop();assert hashlib.sha256((R/'generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest()==D['native_binary_sha256'];start=time.monotonic();deadline=start+180;c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);cache={};signatures={};snapshots=[];pairs=[];calls=[];out=dict(complete=False,calls=calls,pairs=pairs,native_binary_sha256=D['native_binary_sha256'],scope=D['scope'])
def signature(ss,bb):return (ss.state,ss.history,ss.result,ss._search_witnesses,bb.fen(),tuple(m.uci() for m in bb.move_stack))
def make(f):
 ss=GameSession(c);bb=P.board(f)
 for text in f['history']:P.A.guard(deadline,P.stop);ss.submit(next(a for a in ss.legal_actions() if uci(a)==text))
 return ss,bb
setupstart=time.monotonic()
for i,f in enumerate(D['roots']):
 ss,bb=make(f);cache[i]=ss,bb;signatures[i]=signature(ss,bb);snapshots.append(dict(root=i,state=record_value(ss.state),history=record_value(ss.history),witnesses=record_value(ss._search_witnesses)))
out['cache_setup_seconds']=time.monotonic()-setupstart;out['cache_audit_serialized_bytes']=len(json.dumps(snapshots).encode());out['cache_memory_scope']='Auditserializedbytes, notphysicalheapownership; compiledrulesexcluded.4ownedSessions/80historyrecords/84witnesses, sharingimmutableprefix states acrossclones.'
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
def non_time(v):
 if isinstance(v,dict):return {k:non_time(z) for k,z in v.items() if 'elapsed' not in k and k not in ('wall_seconds','seconds')}
 if isinstance(v,list):return [non_time(z) for z in v]
 return v
try:
 for i,f in enumerate(D['roots']):
  for opponent in D['opponents']:
   for color in (True,False):
    pi=len(pairs);rows=[]
    for arm in (D['arms'] if pi%2==0 else list(reversed(D['arms']))):
     P.A.guard(deadline,P.stop);gamestart=time.monotonic();ts=time.monotonic()
     if arm=='replay':ss,b=make(f)
     else:ss=copy.copy(cache[i][0]);b=cache[i][1].copy(stack=True);assert ss is not cache[i][0] and b is not cache[i][1]
     prefixseconds=time.monotonic()-ts;assert signature(ss,b)==signatures[i];ts=time.monotonic();e=SemanticSearchEngine(c,n,board_values=D['weights'],hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=0);enginesetup=time.monotonic()-ts;rng=random.Random(D['random_seeds'][i]);actions=[];searches=[];oppo=[];legal_seconds=submit_seconds=opponent_seconds=0;playstart=time.monotonic()
     for ply in range(8):
      P.A.guard(deadline,P.stop)
      if b.is_game_over(claim_draw=False):break
      ts=time.monotonic();aa={uci(a):a for a in ss.legal_actions()};assert sorted(aa)==sorted(m.uci() for m in b.legal_moves);legal_seconds+=time.monotonic()-ts
      if b.turn==color:
       before=(ss.state,ss.history,ss.result);ts=time.monotonic();v=e.search(ss,SearchLimits(max_depth=2,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=False);assert before==(ss.state,ss.history,ss.result);m=chess.Move.from_uci(uci(v.action));searches.append(dict(ply=ply,full_history=[z.uci() for z in b.move_stack],root_fen=b.fen(),result=record_value(v),seconds=time.monotonic()-ts))
      elif opponent=='random':m=rng.choice(sorted(b.legal_moves,key=lambda z:z.uci()))
      else:ts=time.monotonic();m,v=P.P.unit2ply(b.copy(stack=True),deadline,P.stop);opponent_seconds+=time.monotonic()-ts;oppo.append(v)
      ts=time.monotonic();ss.submit(aa[m.uci()]);b.push(m);actions.append(m.uci());submit_seconds+=time.monotonic()-ts
     score=P.G.score(b,color,len(actions),8);res=dict(root_fen=f['initial_fen'],opening_history=f['history'],opening_fen=f['expected_fen'],agent_color=color,actions=actions,search_records=searches,opponent_records=oppo,final_fen=b.fen(),score=score,reward=score['reward'],generic_terminal=record_value(ss.result));row=dict(pair=pi,root=i,arm=arm,opponent=opponent,color=color,weights=D['weights'],random_seed=D['random_seeds'][i],result=res,seconds=time.monotonic()-gamestart,prefix_seconds=prefixseconds,engine_setup_seconds=enginesetup,play_seconds=time.monotonic()-playstart,legal_sync_seconds=legal_seconds,submit_seconds=submit_seconds,opponent_seconds=opponent_seconds,agent_search_seconds=sum(z['seconds'] for z in searches));calls.append(row);rows.append(row);assert signature(cache[i][0],cache[i][1])==signatures[i]
    assert non_time(rows[0]['result'])==non_time(rows[1]['result']);pairs.append(dict(pair=pi,root=i,opponent=opponent,color=color,all_non_time_result_fields_equal=True,order=[z['arm'] for z in rows],seconds={z['arm']:z['seconds'] for z in rows},prefix_seconds={z['arm']:z['prefix_seconds'] for z in rows}));save();print(pi,len(calls),round(out['seconds'],3),flush=True)
 out['complete']=True;save();print('COMPLETE',len(calls),out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
