import json,time,sys,copy,hashlib,importlib.util,os,dataclasses
from pathlib import Path
R=Path.cwd();S=R/'.local_agent/pinned/f1ea1d38';sys.path.insert(0,str(S));sys.path.insert(1,str(R));O=R/'results/dev_aux/task310';O.mkdir(exist_ok=False)
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
old=json.loads((R/'results/dev_aux/task289/declaration.json').read_bytes());D=dict(task_id='310',question='Does integratedsparse append recording preserveallactualscientificfields andfixobservedgrowing-prefix IOcost?',roots=old['roots'][:2],profiles={k:old['profiles'][k] for k in ('semantic','unit')},cells=[dict(root=i,opponent='unit',color=color) for i in range(2) for color in (True,False)],cap=48,depth=3,repetition_limit=5,binary_sha256=old['binary_sha256'],source_commit=old['source_commit'],whole_fuse_seconds=240,scope='Resume3remaininggames fromfailed309;1completedgame/31queries carriedandoneactualpendingqueryreusedwithoutsearch; 107newqueriesexpected. Legacycodecbugfixed bydecodebeforeconstantencode; rawfailure/sourcepreserved. Initialcopy32oldqueryentriesexcludedfrompairedIOmetrics, includedcurrentbatchwall. Fourlogicalsame-input matchedgames versusqualified289cells, allnon-timefields mustmatch. Onephysicalsearchpermove; twoIOformats sameactualrecord, alternatingIOorder: constant-codec wholeprefix versus sparse-codec appendperquery/fsync. Legacyreplay bounded4gamesonly; nocausalold297wall speedup/machineexclusiveclaim. Allfields/typedzeros retained, no product/default/UI oroldresultwrites.')
(O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8');assert Path(native.__file__).resolve().is_relative_to(S.resolve()) and hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest()==D['binary_sha256']
def load(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
P=load('p',R/'results/dev_aux/task166/run.py');C=load('codec',R/'results/dev_aux/task308/codec.py');P.stop();start=time.monotonic();deadline=start+240;c=compile_semantic_ruleset(dataclasses.replace(build_western_chess_ruleset(),repetition_limit=5));n=compile_native_semantic_rules(c);cache={};rows=[];bytes_={'legacy_prefix':0,'sparse_append':0};io={k:0. for k in bytes_};querycount=31;actualnew=0;prior=json.loads((R/'results/dev_aux/task309/result.json').read_bytes());rows.extend(prior['calls']);bytes_.update(prior['total_write_bytes']);io.update(prior['record_io_seconds']);oldlines=(R/'results/dev_aux/task309/queries.jsonl').read_bytes().splitlines();assert len(oldlines)==32;pending=json.loads(oldlines[-1]);assert hashlib.sha256(C.canonical(C.decode(pending['record']))).hexdigest()==pending['raw_sha256'];baseline=C.decode(json.loads((R/'results/dev_aux/task289/result.json').read_bytes()))
def sig(ss,b):return ss.state,ss.history,ss.result,ss._search_witnesses,b.fen(),tuple(m.uci() for m in b.move_stack)
def strip(v):
 if isinstance(v,dict):return {k:strip(z) for k,z in v.items() if 'elapsed' not in k and k not in ('wall_seconds','seconds')}
 if isinstance(v,list):return [strip(z) for z in v]
 return v
out=dict(complete=False,calls=rows)
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
try:
 for i,f in enumerate(D['roots']):
  ss=GameSession(c);b=P.board(f)
  for t in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==t))
  cache[i]=ss,b,sig(ss,b)
 with (O/'queries.jsonl').open('xb') as journal:
  journal.write(b'\n'.join(oldlines)+b'\n');journal.flush();os.fsync(journal.fileno())
  for cell in D['cells'][1:]:
   ss0,b0,signature=cache[cell['root']];ss=copy.copy(ss0);b=b0.copy(stack=True);actions=[];searches=[];ts=time.monotonic()
   for ply in range(48):
    P.A.guard(deadline,P.stop)
    if b.is_game_over(claim_draw=False):break
    aa={uci(a):a for a in ss.legal_actions()};assert sorted(aa)==sorted(m.uci() for m in b.legal_moves);name='semantic' if b.turn==cell['color'] else 'unit';w=D['profiles'][name];e=SemanticSearchEngine(c,n,board_values=w,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=1);before=sig(ss,b);vt=time.monotonic();borrowed=cell==pending['game'] and ply==0
    if borrowed:
     rr=C.decode(pending['record']);assert rr['root_fen']==b.fen() and rr['full_history']==[m.uci() for m in b.move_stack] and rr['weights']==w
    else:
     v=e.search(ss,SearchLimits(max_depth=3,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=True);actualnew+=1;assert sig(ss,b)==before;rr=dict(ply=ply,profile=name,weights=w,root_fen=b.fen(),full_history=[m.uci() for m in b.move_stack],result=record_value(v),wall_seconds=time.monotonic()-vt)
    searches.append(rr)
    # Save actualquerybeforeanycompletionassert; no hugegrowingprefix in productionappendpath.
    def legacy():
     q=dict(completed_games=C.C.encode(C.decode(rows)),active_game=dict(cell=cell,actions=actions,search_records=C.C.encode(searches),current_fen=b.fen()));P.A.atomic_json(O/'legacy_prefix.json',q);bytes_['legacy_prefix']+=(O/'legacy_prefix.json').stat().st_size
    def append():
     entry=dict(sequence=querycount,game=cell,record=C.encode(rr),raw_sha256=hashlib.sha256(C.canonical(rr)).hexdigest());line=C.canonical(entry)+b'\n';journal.write(line);journal.flush();os.fsync(journal.fileno());bytes_['sparse_append']+=len(line)
    for key,fn in ([('legacy_prefix',legacy),('sparse_append',append)] if querycount%2==0 else [('sparse_append',append),('legacy_prefix',legacy)]):
     if borrowed and key=='sparse_append':continue
     xt=time.monotonic();fn();io[key]+=time.monotonic()-xt
    querycount+=1;raw=rr['result'];assert raw['completed_depth']==3 and not raw['used_fallback'];a=raw['action'];fr=a['from_square'];to=a['to_square'];text=chess.square_name(chess.square(fr['file'],fr['rank']))+chess.square_name(chess.square(to['file'],to['rank']))+(a.get('promotion_target_id') or '').lower();ss.submit(aa[text]);b.push_uci(text);actions.append(text)
   assert sig(ss0,b0)==signature;oo=b.outcome(claim_draw=False);tag='unknown' if oo is None else 'draw' if oo.winner is None else 'win' if oo.winner==cell['color'] else 'loss';row=dict(**cell,actions=actions,search_records=searches,final_fen=b.fen(),score=P.G.score(b,cell['color'],len(actions),48),outcome=tag,terminal=record_value(ss.result),wall_seconds=time.monotonic()-ts);ref=next(z for z in baseline['calls'] if z['root']==cell['root'] and z['opponent']=='unit' and z['color']==cell['color']);assert strip(row)==strip(ref);rows.append(C.encode(row));save();print(cell,tag,len(actions),round(time.monotonic()-ts,3),flush=True)
 for i,line in enumerate((O/'queries.jsonl').read_bytes().splitlines()):z=json.loads(line);assert z['sequence']==i and hashlib.sha256(C.canonical(C.decode(z['record']))).hexdigest()==z['raw_sha256']
 out.update(complete=True,actual_games=3,logical_completed_games=len(rows),actual_new_queries=actualnew,actual_total_queries=querycount,carried_completed_queries=31,reused_pending_queries=1,all_non_time_equal_to_289=True,all_query_hashes_verified=True,total_write_bytes=bytes_,record_io_seconds=io);save();print('COMPLETE',querycount,bytes_,io,out['seconds'])
except BaseException as ex:out.update(failure=dict(type=type(ex).__name__,message=str(ex)),actual_queries=querycount,total_write_bytes=bytes_,record_io_seconds=io);save();raise