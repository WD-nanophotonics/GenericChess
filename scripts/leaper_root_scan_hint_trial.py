"""Prospective root-scan hint trial. Research copies only; no production edits."""
from __future__ import annotations
import argparse,hashlib,json,time,types,sys,gzip
from pathlib import Path
from datetime import datetime,timezone
from contextlib import contextmanager
from dataclasses import asdict
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.rules.schema import RuleSet,ruleset_to_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value,write_record
from tools.local_agent.common import write_json
import generic_chess.ai.alphabeta.player as player_module
import generic_chess.ai.alphabeta.search as search_module

BASE=Path(search_module.__file__)
MARK='    original_alpha = alpha\n'
INJECT='''    if (ply == 0 and ctx.use_ordering and ctx.root_scan_best_action is not None
            and (entry is None or entry.best_action is None)):
        ordered_actions = list(ordered_actions)
        hint = ctx.root_scan_best_action
        if hint in ordered_actions:
            ordered_actions.remove(hint)
            ordered_actions.insert(0, hint)
            RESEARCH_HINT_EVENTS.append({"depth": depth, "hint": str(hint),
                                         "legal_count": len(ordered_actions)})

'''

def candidate_source():
    original=BASE.read_bytes().decode('utf-8').replace('\r\n','\n')
    assert original.count(MARK)==1
    return original.replace(MARK,INJECT+MARK)

def candidate_module():
    name='generic_chess.ai.alphabeta._prospective_root_hint'
    mod=types.ModuleType(name);mod.__package__='generic_chess.ai.alphabeta'
    mod.__file__='<frozen-research-search-source>';mod.RESEARCH_HINT_EVENTS=[]
    sys.modules[name]=mod;exec(compile(candidate_source(),mod.__file__,'exec'),mod.__dict__)
    return mod

@contextmanager
def search_arm(arm,mod):
    original=player_module.run_root_search
    try:
        if arm=='scan_hint':player_module.run_root_search=mod.run_root_search
        yield
    finally:player_module.run_root_search=original

def signed(x,y):
    return sorted({(sx*a,sy*b) for a,b in [(x,y),(y,x)] for sx in (-1,1) for sy in (-1,1)}-{(0,0)})

def families():
    return [(signed(1,2),signed(0,1)),(signed(2,3),signed(1,1)),
            (signed(1,3),signed(0,2)),(signed(2,2),signed(1,2)),
            (signed(0,1)+signed(0,2),signed(1,1)+signed(2,2)),
            ([(1,0),(-1,0),(0,1),(1,2),(-1,2)],[(1,1),(-1,1),(2,0),(-2,0)])]

def definition(n,family):
    aa,bb=families()[family];kk=signed(0,1)+signed(1,1)
    types=tuple(PieceType(k,k,tuple(LeapAtom(tuple(v)) for v in moves),is_anchor=k=='K') for k,moves in [('K',kk),('A',aa),('B',bb)])
    board=[None]*(n*n)
    coords=[(0,0,0,'K'),(1,1,0,'A'),(2,0,0,'A'),(0,2,0,'B'),
            (n-1,n-1,1,'K'),(n-2,n-2,1,'A'),(n-3,n-1,1,'A'),(n-1,n-3,1,'B')]
    for x,y,owner,k in coords:
        assert board[x+n*y] is None;board[x+n*y]=Piece(owner,k,k)
    return RuleSet(board_size=n,piece_types=types,initial_position=tuple(tuple(board[y*n:y*n+n])for y in range(n)),
        capture_disposition='remove_from_game',drop_allowed={k:((False,)*(n*n),)*2 for k in ['A','B']},max_ply=96,repetition_limit=4)

def prefix(compiled,key,length):
    session=GameSession(compiled)
    for step in range(length):
        if session.state.terminal_status.is_terminal:break
        actions=sorted(session.legal_actions(),key=str)
        if not actions:break
        h=hashlib.sha256((key+':'+str(step)).encode()).digest()
        session.submit(actions[int.from_bytes(h[:8],'big')%len(actions)])
    return session

def prepare(output):
    assert not output.exists();output.mkdir(parents=True)
    rows=[];tick=time.perf_counter()
    for n in [5,6]:
      for f in range(6):
       rr=definition(n,f)
       for length in [2,3]:
        row={'id':f'n{n}-f{f}-h{length}','n':n,'family':f,'prefix_length':length,'RuleSet':ruleset_to_dict(rr,include_metadata=True),'fingerprint':compute_fingerprint(rr),'exposure':'prospective development, not independent holdout'}
        try:
            c=compile_legacy_ruleset_for_semantic_execution(rr);s=prefix(c,row['id'],length)
            row.update(status='PREPARED',record=record_value(s.to_record()),root=record_value(s.state),legal_actions=[record_value(a)for a in s.legal_actions()],terminal=s.state.terminal_status.is_terminal)
        except Exception as e:row.update(status='PREPARATION_FAILED',error_type=type(e).__name__,error=str(e))
        rows.append(row);write_record(output/'prepared-progress.json',rows)
    write_record(output/'inputs.json',{'rows':rows,'new_Player':0,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'prepare_seconds':time.perf_counter()-tick})
    print(json.dumps({'prepared':sum(r['status']=='PREPARED'for r in rows),'total':len(rows),'terminals':sum(r.get('terminal',False)for r in rows),'seconds':time.perf_counter()-tick}))

def run(inputs,plan_path,output):
    assert not output.exists();output.mkdir(parents=True)
    plan=json.loads(plan_path.read_bytes());rows=json.loads(inputs.read_bytes())['rows'];start=datetime.now(timezone.utc).isoformat();tick=time.perf_counter();results=[];mod=candidate_module();attempts=0;halt=None
    write_record(output/'executed-source.json',{'driver':Path(__file__).read_bytes().decode(),'base_source':BASE.read_bytes().decode(),'candidate_source':candidate_source(),'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'inputs_sha256':hashlib.sha256(inputs.read_bytes()).hexdigest()})
    for i,row in enumerate(rows):
     for depth in [1,4]:
      arms=['baseline','scan_hint'] if (i+depth)%2 else ['scan_hint','baseline'];pair=[]
      for arm in arms:
        result={'case_id':row['id'],'requested_depth':depth,'arm':arm,'slot':len(results),'input_fingerprint':row['fingerprint']}
        if halt or time.perf_counter()-tick>=1200 or attempts>=96:
            result.update(status='NOT_RUN',reason=halt or 'batch_cap');results.append(result);continue
        if row['status']!='PREPARED' or row.get('terminal'):
            result.update(status='INELIGIBLE_RETAINED',reason=row['status'] if row['status']!='PREPARED' else 'terminal');results.append(result);continue
        attempts+=1;t0=time.perf_counter();cpu=time.process_time();utc0=datetime.now(timezone.utc).isoformat()
        try:
            from generic_chess.rules.schema import ruleset_from_dict
            rr=ruleset_from_dict(row['RuleSet']);c=compile_legacy_ruleset_for_semantic_execution(rr)
            s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));before=s.to_record()
            setup=time.perf_counter()-t0;tuning=SearchTuning(use_pvs=True)
            player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=tuning,use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
            constructor=time.perf_counter()-t0-setup;mod.RESEARCH_HINT_EVENTS.clear()
            with search_arm(arm,mod):decision=player.choose_action(s,SearchLimits(max_depth=depth,max_nodes=200000,max_time_seconds=10,quiescence_max_depth=4,quiescence_hard_max_depth=8))
            # Save actual decision before contracts or interpretation.
            result.update(status='RETURNED',decision=record_value(decision),hint_events=list(mod.RESEARCH_HINT_EVENTS),started_at=utc0,ended_at=datetime.now(timezone.utc).isoformat(),outer_seconds=time.perf_counter()-t0,cpu_seconds=time.process_time()-cpu,setup_seconds=setup,constructor_seconds=constructor)
            write_record(output/f'return-{result["slot"]:03d}.json',result)
            assert s.to_record()==before,'root mutation'
            if decision.action is not None:assert decision.action in s.legal_actions(),'illegal returned action'
            pv=GameSession.replay(c,before)
            for a in decision.principal_variation:pv.submit(a)
            result['root_unchanged']=True;result['pv_legal']=True
        except Exception as e:
            result.update(status='FAILED',error_type=type(e).__name__,error=str(e),ended_at=datetime.now(timezone.utc).isoformat(),outer_seconds=time.perf_counter()-t0,cpu_seconds=time.process_time()-cpu);halt='execution_or_recording_failure'
        results.append(result);pair.append(result);write_record(output/'queries.json',results)
      if len(pair)==2 and all(x['status']=='RETURNED' and x['decision']['completed_depth']==depth for x in pair):
        if pair[0]['decision']['score']!=pair[1]['decision']['score']:
            halt='complete_value_mismatch';write_record(output/'mismatch.json',pair)
      write_record(output/'progress.json',{'attempts':attempts,'slots':len(results),'seconds':time.perf_counter()-tick,'halt':halt})
    write_record(output/'summary.json',{'started_at':start,'ended_at':datetime.now(timezone.utc).isoformat(),'seconds':time.perf_counter()-tick,'slots':len(results),'attempts':attempts,'halt':halt,'statuses':{s:sum(r['status']==s for r in results) for s in sorted({r['status'] for r in results})},'new_solver':0,'games':0})
    print((output/'summary.json').read_text())

if __name__=='__main__':
 p=argparse.ArgumentParser(__doc__);p.add_argument('--prepare',type=Path);p.add_argument('--inputs',type=Path);p.add_argument('--plan',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.prepare:prepare(a.prepare)
 else:run(a.inputs,a.plan,a.output)
