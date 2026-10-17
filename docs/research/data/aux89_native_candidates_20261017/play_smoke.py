"""Compatibility smoke for all fixed candidate models, not a strength experiment."""
from pathlib import Path
import sys,json,time,random,hashlib,traceback
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value

def smoke(out):
    out=Path(out);out.mkdir(exist_ok=False);directory=Path(__file__).resolve().parent
    index=json.loads((directory/'index.json').read_text(encoding='utf8'))
    slots=[(e['generator_seed'],e['seed'],owner,e['path'])for e in index['models']if e['label']=='trained'for owner in(0,1)]
    random.Random(2026101703).shuffle(slots)
    plan=dict(question='Do ALL eight portable learned candidates actually play lawful complete-state games through the existing backend, beyond source-root query checks?',slots=slots,depth=2,nodes_per_query=8192,seconds_per_query=2.,horizon=64,tt_megabytes=0,forecast_seconds=60,cap_seconds=300,scope='Compatibility smoke ONLY, allfourTRAIN-exposedrules/eightmodels/bothroles versusfixedUnit on freshinitialstates. No initial-model comparator/newlearning/seedselection or strength/winner/gain estimate. H64UNKNOWN distinct from actual rule512; allpartial/failed/unstarted slots retained. NoAUXimports/default/champion/UIchange.')
    (out/'plan.json').write_bytes((json.dumps(plan,indent=2)+'\n').encode());began=time.monotonic();compiled={};native={};games=[];status='COMPLETE';reason=None
    def poll():
        if time.monotonic()-began>=plan['cap_seconds']:raise TimeoutError('FROZEN_GLOBAL_CAP')
        for name in('rollout','advisor','slack'):
            path=ROOT/'.local_agent'/(name+'.json')
            if path.exists():
                flags=json.loads(path.read_bytes())
                if flags.get('stopped')or flags.get('user_paused'):raise InterruptedError('EXPLICIT_STOP')
    try:
        with(out/'queries.jsonl').open('x',encoding='utf8')as qlog:
            for slot,(gs,seed,owner,filename)in enumerate(slots):
                poll()
                if gs not in compiled:
                    rule=ruleset_from_dict(json.loads((directory/f'rule-{gs}.json').read_text(encoding='utf8')))
                    compiled[gs]=compile_legacy_ruleset_for_semantic_execution(rule);native[gs]=compile_native_semantic_rules(compiled[gs])
                c=compiled[gs];n=native[gs];candidate=LearnableMaterialCheckpoint.from_dict(json.loads((directory/filename).read_text(encoding='utf8')))
                unit=LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,board_weights={t:1. for t in candidate.board_weights},hand_weights={t:1. for t in candidate.hand_weights},material_scale=256,value_scale=10.,reference_median=1.)
                engines={owner:SemanticSearchEngine(c,n,checkpoint=candidate,tt_megabytes=0),1-owner:SemanticSearchEngine(c,n,checkpoint=unit,tt_megabytes=0)}
                s=GameSession(c);nodes=queries=0;ending='HORIZON_UNKNOWN'
                for ply in range(plan['horizon']):
                    poll()
                    if s.result.status.value!='ongoing':ending='ACTUAL_TERMINAL';break
                    before=(s.state,s.to_record(),s.history,s._search_witnesses);side=s.state.position.side_to_move;stamp=time.perf_counter()
                    wall_limit=min(2.,plan['cap_seconds']-(time.monotonic()-began))
                    r=engines[side].search(s,SearchLimits(max_depth=2,max_nodes=8192,max_time_seconds=wall_limit,quiescence_max_depth=0),root_window_pruning=False)
                    elapsed=time.perf_counter()-stamp;assert before==(s.state,s.to_record(),s.history,s._search_witnesses);nodes+=r.nodes;queries+=1
                    if r.declaration_id is not None:s.declare(r.declaration_id)
                    elif r.action is not None:
                        assert r.action in s.legal_actions();s.submit(r.action)
                    else:ending='NO_RETURNED_ACTION_UNKNOWN'
                    qlog.write(json.dumps(dict(slot=slot,ply=ply,actor=side,record_before=json.loads(serialize_game_record(before[1])),record_after=json.loads(serialize_game_record(s.to_record())),requested_depth=2,effective_nodes=8192,effective_seconds=wall_limit,completed_depth=r.completed_depth,used_fallback=r.used_fallback,cause=r.termination_reason,nodes=r.nodes,kernel_seconds=r.elapsed_seconds,caller_seconds=elapsed,action=record_value(r.action),declaration_id=r.declaration_id),separators=(',',':'))+'\n');qlog.flush()
                    if ending=='NO_RETURNED_ACTION_UNKNOWN':break
                if s.result.status.value!='ongoing':ending='ACTUAL_TERMINAL'
                record=json.loads(serialize_game_record(s.to_record()));fresh=GameSession.replay(c,deserialize_game_record(json.dumps(record)));assert (fresh.state,fresh.history,fresh._search_witnesses,fresh.result)==(s.state,s.history,s._search_witnesses,s.result)
                row=dict(slot=slot,rule=gs,seed=seed,candidate_owner=owner,checkpoint_id=candidate.checkpoint_id,ending=ending,result=record_value(s.result),record=record,nodes=nodes,queries=queries,full_replay_equal=True);games.append(row)
                (out/f'game-{slot}.json').write_bytes((json.dumps(row,indent=2)+'\n').encode());print('GAME',slot,gs,seed,owner,ending,s.state.ply_count,flush=True)
    except Exception as e:status='ERROR';reason=repr(e);traceback.print_exc()
    result=dict(status=status,reason=reason,planned=len(slots),returned=len(games),unstarted=len(slots)-len(games),games=games,seconds=time.monotonic()-began,queries=sum(g['queries']for g in games),nodes=sum(g['nodes']for g in games),scope=plan['scope'])
    (out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print('CLOSED',status,len(games),round(result['seconds'],3),reason,flush=True)
    return result

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Pass a NEW output directory; existing evidence is never replaced.')
    smoke(sys.argv[1])
