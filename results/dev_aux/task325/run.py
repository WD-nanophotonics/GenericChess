"""Frozen complete-D3 deployment transfer of all randommate endpoints, no new fitting."""
import json,time,sys,os,copy,dataclasses,hashlib,importlib.util,random
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
P=load('p325',R/'results/dev_aux/task166/run.py');C=load('sparse325',R/'results/dev_aux/task308/codec.py');O=R/'results/dev_aux/task325'
def sig(ss,b):return ss.state,ss.history,ss.result,ss._search_witnesses,b.fen(),tuple(m.uci() for m in b.move_stack)
def execute():
 O.mkdir(exist_ok=False);P.stop();E=json.loads((R/'results/dev_aux/task322/endpoints.json').read_bytes());assert E['complete'];D0=json.loads((R/'results/dev_aux/task322/declaration.json').read_bytes());old=json.loads((R/'results/dev_aux/task267/declaration.json').read_bytes());roots=old['roots'];build=json.loads((R/'results/dev_aux/task279/build.json').read_bytes());profiles={**{f'initial-{k}':w for k,w in D0['initials'].items()},**{f'endpoint-{k}':v['weights'] for k,v in E['endpoints'].items()}};unique={};aliases={}
 for name,w in profiles.items():
  kk=tuple(w[k] for k in 'PNBRQK')
  if kk not in unique:unique[kk]=name
  aliases[name]=unique[kk]
 cells=[dict(root=ri,color=color,seed=seed,phase='train_deployment') for ri in (0,1) for color in (True,False) for seed in D0['random_seeds']]+[dict(root=ri,color=color,seed=seed,phase='exposed_development') for ri in (2,3) for color in (True,False) for seed in range(2026102391,2026102395)]
 D=dict(task_id='325',question='Do ALLfrozenfastmatelearnedprices transfer to completeq0D3 withoutmatureselectiveheuristics andtootheroldroots?',roots=roots,profiles=profiles,aliases=aliases,unique_profiles=list(unique.values()),cells=cells,cap=48,depth=3,per_call_seconds=3,tt_megabytes=1,root_window_pruning=True,quiescence_max_depth=0,repetition_limit=5,binary_sha256=build['binary_sha256'],source_commit=build['source_commit'],endpoint_sha256=hashlib.sha256((R/'results/dev_aux/task322/endpoints.json').read_bytes()).hexdigest(),whole_fuse_seconds=2400,pilot='First8unittrainroot0/color/seedcells; sharedwithwholepanelnotextra. If pilot projects>1500s forwhole uniqueprofiles*80cells, stopcostpanelwithoutrescue; noexpectedhourrun.',estimated_cost='289matchedpureD3pricegames32/103.6s =>atmost480games~1554s butuniformrandomtypicallyshorter; costpilotdefinesfeasibility beforewholepanel. Fixedcap48notlonggames. FirstincompleteD3 =>retainactualquery/counters andstop; nomissingpartialrepeat/deeperlimit.',scope='No fitting/adoption: allendpoints frozen322; NativefullD3/coldTT1 versusFairy1024nodes isoverall deploymentreference, not samework/equivalentpruningcausality. Experimentalrepetition5; no-progress/insufficientmaterial search exclusions declared, externalFIDEoutcome retained. Goal unchanged truefastmate; nohumanparameters orbestendpoint selection.')
 (O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8');assert Path(native.__file__).resolve().is_relative_to(S.resolve()) and hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest()==D['binary_sha256'];start=time.monotonic();deadline=start+2400;c=compile_semantic_ruleset(dataclasses.replace(build_western_chess_ruleset(),repetition_limit=5));n=compile_native_semantic_rules(c);cache={};completed=[];out=dict(complete=False,actual_games=0,actual_queries=0,rows=completed);partial=None
 def save():out.update(seconds=time.monotonic()-start,partial_game=partial);P.A.atomic_json(O/'result.json',out)
 try:
  for ri,f in enumerate(roots):
   ss=GameSession(c);b=chess.Board(f['initial_fen'])
   for t in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==t));b.push_uci(t)
   assert b.fen()==f['expected_fen'];cache[ri]=(ss,b,sig(ss,b))
  with (O/'queries.jsonl').open('xb') as journal,(O/'games.jsonl').open('xb') as games:
   for name in unique.values():
    w=profiles[name]
    for cell in cells:
     ss0,b0,signature=cache[cell['root']];ss=copy.copy(ss0);b=b0.copy(stack=True);rng=random.Random(cell['seed']);actions=[];rr=[];randoms=[];ts=time.monotonic();partial=dict(profile=name,**cell,actions=actions,search_records=rr,random_choices=randoms)
     for ply in range(48):
      P.A.guard(deadline,P.stop)
      if b.is_game_over(claim_draw=False):break
      aa={uci(a):a for a in ss.legal_actions()};assert sorted(aa)==sorted(m.uci() for m in b.legal_moves)
      if b.turn==cell['color']:
       e=SemanticSearchEngine(c,n,board_values=w,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=1);before=sig(ss,b);vt=time.monotonic();v=e.search(ss,SearchLimits(max_depth=3,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=True);raw=record_value(v);assert sig(ss,b)==before;record=dict(ply=ply,profile=name,weights=w,root_fen=b.fen(),full_history=[m.uci() for m in b.move_stack],result=C.encode(raw),raw_sha256=hashlib.sha256(C.canonical(raw)).hexdigest(),wall_seconds=time.monotonic()-vt);rr.append(record);out['actual_queries']+=1;journal.write(C.canonical(dict(sequence=out['actual_queries'],game=out['actual_games'],cell=cell,record=record))+b'\n');journal.flush();os.fsync(journal.fileno());assert v.completed_depth==3 and not v.used_fallback,(v.completed_depth,v.termination_reason);text=uci(v.action);assert text in aa
      else:
       legal=sorted(b.legal_moves,key=lambda m:m.uci());ix=rng.randrange(len(legal));text=legal[ix].uci();randoms.append(dict(ply=ply,index=ix,legal_count=len(legal),move=text))
      ss.submit(aa[text]);b.push_uci(text);actions.append(text)
     assert sig(ss0,b0)==signature;oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if oo is None or oo.winner is None else 1 if oo.winner==cell['color'] else -1;goal=F(49-len(actions),48) if kind=='CHECKMATE' and sign==1 else F(-1) if kind=='CHECKMATE' and sign==-1 else F(0);row=dict(profile=name,weights=w,**cell,actions=actions,search_records=rr,random_choices=randoms,final_fen=b.fen(),termination=kind,finite_mate_sign=sign if kind=='CHECKMATE' else 0,fitness=str(goal),core_result=record_value(ss.result),seconds=time.monotonic()-ts);games.write(C.canonical(row)+b'\n');games.flush();os.fsync(games.fileno());completed.append({k:v for k,v in row.items() if k!='search_records'});out['actual_games']+=1;partial=None
     if out['actual_games']==8:
      projected=(time.monotonic()-start)/8*len(unique)*len(cells);out['pilot_projection_seconds']=projected;save()
      if projected>1500:out['status']='PILOT_COST_LIMIT';break
     if out['actual_games']%16==0:save();print(name,out['actual_games'],out['actual_queries'],round(time.monotonic()-start,3),flush=True)
    if out.get('status')=='PILOT_COST_LIMIT':break
   out['complete']=out['actual_games']==len(unique)*len(cells);save()
 except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
 print('COMPLETE',out['complete'],out['actual_games'],out['actual_queries'],out['seconds'])
if __name__=='__main__':execute()