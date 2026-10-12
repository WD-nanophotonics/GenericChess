"""CompleteD3 same-goal deployment of every frozen quantity endpoint."""
import json,time,sys,os,copy,dataclasses,hashlib,importlib.util
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();S=R/'.local_agent/pinned/f1ea1d38';sys.path.insert(0,str(S));sys.path.insert(1,str(R))
import chess
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value
import generic_chess._native_core as native
def load(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
P=load('p340',R/'results/dev_aux/task166/run.py');C=load('codec340',R/'results/dev_aux/task308/codec.py');O=R/'results/dev_aux/task340'
def sig(ss,b):return ss.state,ss.history,ss.result,ss._search_witnesses,b.fen(),tuple(m.uci() for m in b.move_stack)
def execute():
 assert not (O/'execution.json').exists();P.stop();D=json.loads((O/'declaration.json').read_bytes());E=json.loads((R/'results/dev_aux/task338/endpoints.json').read_bytes());assert E['complete'];D0=json.loads((R/'results/dev_aux/task338/declaration.json').read_bytes());profiles={**{f'initial-{k}':w for k,w in D0['initials'].items()},**{f'endpoint-{k}':v['weights'] for k,v in E['endpoints'].items()}};unique={};aliases={}
 for name,w in profiles.items():
  kk=tuple(w[k] for k in 'PNBRQK')
  if kk not in unique:unique[kk]=name
  aliases[name]=unique[kk]
 execution=dict(profiles=profiles,unique_profiles=list(unique.values()),aliases=aliases,unit=D0['unit'],endpoint_sha256=hashlib.sha256((R/'results/dev_aux/task338/endpoints.json').read_bytes()).hexdigest(),binary_sha256='477d2117a5c5a74639f917c3ca58830593240e1905e5db594ba3a4d9877476fe',source_commit='f1ea1d3870302777de6b56ae4cd62a17d7bf7bb0',whole_fuse_seconds=1800,scope='340prepared beforeendpointresults; exactallfrozeninitial/endpointaliases afterfreeze, noselection. BothplayersNativeD3 vs342bothFairy1024 is overalldeploymentreference, notpurepruning effect.')
 P.A.atomic_json(O/'execution.json',execution);assert Path(native.__file__).resolve().is_relative_to(S.resolve()) and hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest()==execution['binary_sha256'];start=time.monotonic();deadline=start+1800;c=compile_semantic_ruleset(dataclasses.replace(build_western_chess_ruleset(),repetition_limit=5));n=compile_native_semantic_rules(c);cache={};completed=[];out=dict(complete=False,actual_games=0,actual_queries=0,rows=completed);partial=None
 def save():out.update(seconds=time.monotonic()-start,partial_game=partial);P.A.atomic_json(O/'result.json',out)
 try:
  for ri,f in enumerate(D['roots']):
   ss=GameSession(c);b=chess.Board(f['initial_fen'])
   for t in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==t));b.push_uci(t)
   assert b.fen()==f['expected_fen'];cache[ri]=(ss,b,sig(ss,b))
  with (O/'queries.jsonl').open('xb') as journal,(O/'games.jsonl').open('xb') as games:
   for name in unique.values():
    w=profiles[name]
    for ri,f in enumerate(D['roots']):
     for color in D['colors']:
      ss0,b0,signature=cache[ri];ss=copy.copy(ss0);b=b0.copy(stack=True);actions=[];rr=[];ts=time.monotonic();partial=dict(profile=name,root=ri,color=color,actions=actions,search_records=rr)
      for ply in range(24):
       P.A.guard(deadline,P.stop)
       if b.is_game_over(claim_draw=False):break
       aa={uci(a):a for a in ss.legal_actions()};assert sorted(aa)==sorted(m.uci() for m in b.legal_moves);player='candidate' if b.turn==color else 'unit';ww=w if player=='candidate' else D0['unit'];e=SemanticSearchEngine(c,n,board_values=ww,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=1);before=sig(ss,b);vt=time.monotonic();v=e.search(ss,SearchLimits(max_depth=3,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=True);raw=record_value(v);assert sig(ss,b)==before;rec=dict(ply=ply,profile=name,player=player,weights=ww,root_fen=b.fen(),full_history=[m.uci() for m in b.move_stack],result=C.encode(raw),raw_sha256=hashlib.sha256(C.canonical(raw)).hexdigest(),wall_seconds=time.monotonic()-vt);rr.append(rec);out['actual_queries']+=1;journal.write(C.canonical(dict(sequence=out['actual_queries'],game=out['actual_games'],root=ri,color=color,record=rec))+b'\n');journal.flush();os.fsync(journal.fileno());assert v.completed_depth==3 and not v.used_fallback,(v.completed_depth,v.termination_reason);text=uci(v.action);assert text in aa;ss.submit(aa[text]);b.push_uci(text);actions.append(text)
      assert sig(ss0,b0)==signature;oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if kind!='CHECKMATE' else 1 if oo.winner==color else -1;cnt=lambda co:sum(len(b.pieces(k,co)) for k in range(1,6));quantity=cnt(color)-cnt(not color);goal=F(32*sign) if sign else F(quantity,15) if oo is None else F(0);row=dict(profile=name,weights=w,root=ri,color=color,actions=actions,search_records=rr,final_fen=b.fen(),termination=kind,finite_mate_sign=sign,quantity_difference=quantity,fitness=str(goal),seconds=time.monotonic()-ts);games.write(C.canonical(row)+b'\n');games.flush();os.fsync(games.fileno());completed.append({k:v for k,v in row.items() if k!='search_records'});out['actual_games']+=1;partial=None
      if out['actual_games']==4:
       projection=(time.monotonic()-start)/4*len(unique)*16;out['pilot_projection_seconds']=projection;save()
       if projection>1200:out['status']='PILOT_COST_LIMIT';break
      if out['actual_games']%8==0:save();print(name,out['actual_games'],out['actual_queries'],round(time.monotonic()-start,3),flush=True)
     if out.get('status')=='PILOT_COST_LIMIT':break
    if out.get('status')=='PILOT_COST_LIMIT':break
   out['complete']=out['actual_games']==len(unique)*16;save()
 except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
 print('COMPLETE',out['complete'],out['actual_games'],out['actual_queries'],out['seconds'],flush=True)
if __name__=='__main__':execute()