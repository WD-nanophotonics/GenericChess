"""Finite TT reuse after interrupted iteration, no timing claim."""
import sys,json,time,collections,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from scripts import search_backend_comparison as b
from scripts.research_record import record_value
from scripts.reserve_refresh_diagnostic import stopped
from generic_chess.ai.alphabeta import search as sm,player as pm
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable as TT
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession
from generic_chess.core.search_runtime import SearchPathRuntime as R
oldng=sm.negamax;oldpush=R._push_impl;oldstore=TT.store;oldprobe=TT.probe;oldfactory=pm.SearchStatistics
iteration=0;mode=None;token=None;success2=0;trigger=None;stores=[];probes=[];captured=[];failed=0
class Token:
    flag=False
    def is_cancelled(self):return self.flag
def negamax(*args,**kwargs):
    global iteration
    previous=iteration
    if args[4]==0:iteration=args[1]
    try:return oldng(*args,**kwargs)
    finally:iteration=previous
def pushed(self,*args,**kwargs):
    global success2,trigger,failed
    if mode=='interrupted' and iteration==2 and success2==64 and trigger is None:
        trigger={'iteration':iteration,'successful_iteration_pushes':success2};token.flag=True
    try:result=oldpush(self,*args,**kwargs)
    except BaseException:failed+=1;raise
    if mode=='interrupted' and iteration==2:success2+=1
    return result
def stored(self,key,depth,score,bound,best_action):
    result=oldstore(self,key,depth,score,bound,best_action)
    stores.append((iteration,key,depth,score,bound,best_action))
    return result
def probed(self,key):
    entry=oldprobe(self,key)
    probes.append((iteration,key,None if entry is None else (entry.depth,entry.score,entry.bound,entry.best_action)))
    return entry
def factory():
    stats=SearchStatistics();captured.append(stats);return stats
def entry_tuple(entry):return (entry.depth,entry.score,entry.bound,entry.best_action)
def run(player,board,newmode):
    global mode,captured,probes,stores,failed
    mode=newmode;captured=[];probes=[];stores=[];failed=0
    stopped()
    session=GameSession(board.compiled);session._state=board.initial;session._search_history_witnesses=board.witnesses
    before=(session.state,session._search_history_witnesses)
    decision=player.choose_action(session,SearchLimits(max_depth=2,max_nodes=4096,max_time_seconds=10,quiescence_max_depth=0,quiescence_hard_max_depth=0),cancel_token=token if newmode=='interrupted' else None)
    assert session.state is before[0] and session._search_history_witnesses==before[1]
    stats=bclean(record_value(captured[0]));assert stats['runtime_pushes']==stats['runtime_pops']
    return {'decision':bclean(record_value(decision)),'stats':stats,'failed_pushes':failed}
def bclean(value):
    if isinstance(value,dict):return {k:bclean(v) for k,v in value.items() if 'seconds' not in k and not k.startswith('time_')}
    if isinstance(value,list):return [bclean(v) for v in value]
    return value
rows=[];start=time.monotonic();compiled=b.compile_ruleset_for_execution(b.build_builtin_ruleset('western_chess'))
try:
    sm.negamax=negamax;R._push_impl=pushed;TT.store=stored;TT.probe=probed;pm.SearchStatistics=factory
    for case in b.CASES[:4]:
        for order in range(2):
            assert time.monotonic()-start<120
            board=b.CoreBoard(case,compiled);e=b.Material('chess')
            def make():return AlphaBetaPlayer(compiled,evaluator_override=e,use_disk_cache=False,use_native_semantic_legality=True,tuning=SearchTuning(use_root_tactical=False))
            warm_player=make();token=Token();success2=0;trigger=None
            interrupted=run(warm_player,board,'interrupted');interrupted_stores=list(stores)
            retained={key:entry_tuple(entry) for key,entry in warm_player._tt._data.items() if interrupted['decision']['completed_depth']<2 and any(i==2 and k==key and (depth,score,bound,action)==entry_tuple(entry) for i,k,depth,score,bound,action in interrupted_stores)}
            store_summary=collections.Counter((i,depth,bound.name) for i,key,depth,score,bound,action in interrupted_stores)
            results={}
            for kind in (('warm','cold') if order==0 else ('cold','warm')):
                result=run(warm_player if kind=='warm' else make(),board,kind)
                matched=[(i,entry) for i,key,entry in probes if key in retained and entry==retained[key]]
                result['retained_aborted_entry_probe_matches']=len(matched)
                result['matched_depth_bound_counts']=[{'iteration':i,'entry_depth':depth,'bound':bound,'count':count} for (i,depth,bound),count in sorted(collections.Counter((i,entry[0],entry[2].name) for i,entry in matched).items())]
                results[kind]=result
            assert results['warm']['decision']['completed_depth']==results['cold']['decision']['completed_depth']==2
            assert results['warm']['decision']['score']==results['cold']['decision']['score']
            rows.append({'case':case['id'],'order':order,'trigger':trigger,'successful_iteration2_pushes':success2,'interrupted':interrupted,'retained_aborted_entries':len(retained),'interrupted_store_summary':[{'iteration':i,'depth':depth,'bound':bound,'count':count} for (i,depth,bound),count in sorted(store_summary.items())],**results})
finally:
    sm.negamax=oldng;R._push_impl=oldpush;TT.store=oldstore;TT.probe=oldprobe;pm.SearchStatistics=oldfactory
report={'complete':True,'scope':'material q0 rootOFF finite interrupted TT reuse; probe match proves access, not standalone bound sufficiency or speed benefit','source_sha256':hashlib.sha256((ROOT/'generic_chess/ai/alphabeta/search.py').read_bytes()).hexdigest(),'rows':rows}
(Path(__file__).parent/'reuse.json').write_text(json.dumps(report,indent=2)+'\n')
for row in rows:print(row['case'],row['order'],'trigger',row['trigger'],'retained',row['retained_aborted_entries'],'warm matches',row['warm']['retained_aborted_entry_probe_matches'],'scores',row['warm']['decision']['score'],row['cold']['decision']['score'],'nodes',row['warm']['decision']['nodes'],row['cold']['decision']['nodes'])
