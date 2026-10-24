"""One explicit DEFAULT-versus-UNIT complete contact game; no frozen panel replay."""
from pathlib import Path
from dataclasses import replace
from scripts.semantic_probe_cost import unit_evaluator
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_two_type_forward import player,now
from generic_chess.ai.alphabeta.tuning import SearchTuning
from tools.local_agent import session
from tools.local_agent.common import write_json

def run(inputs,registration,output):
    caller_tick=time.perf_counter()
    assert not output.exists()
    reg=L.load(registration);world=L.load(inputs)
    assert L.sha(inputs)==reg['input_sha256'] and L.sha(Path(__file__))==reg['source_sha256']
    assert reg['expected_total_seconds']<7200 and reg['controller'] in ('DEFAULT','UNIT','STATIC_FIXED','DYNAMIC_FIXED','FULL_FIXED')
    c=L.compile_rule(L.ruleset_from_dict(world['rule']));root=world['roots'][reg['root']]
    s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(root['record'])))
    default=L.AlphaBetaPlayer(c,tuning=SearchTuning(),use_disk_cache=False,use_native_semantic_legality=True,use_native_semantic_availability=False,use_native_semantic_check=False)
    assert L.record_value(default.evaluation_profile)==reg['profile']
    attacker=default if reg['controller']=='DEFAULT' else player(c,1000)
    if reg['controller'] in ('STATIC_FIXED','DYNAMIC_FIXED','FULL_FIXED'):
        unit=unit_evaluator(c)
        profile=default.evaluation_profile if reg['controller']!='DYNAMIC_FIXED' else unit._profile
        config=EvaluationConfig() if reg['controller']!='STATIC_FIXED' else unit._config
        adapter=L.LeafOrderAdapter(Evaluator(c,profile,config),unit)
        attacker=L.AlphaBetaPlayer(c,evaluator_override=adapter,tuning=SearchTuning(),use_disk_cache=False,use_native_semantic_legality=True,use_native_semantic_availability=False,use_native_semantic_check=False)
        assert reg['actual_leaf_profile']==L.record_value(profile) and reg['actual_leaf_config']==L.record_value(config)
    metadata_unit=unit_evaluator(c)
    leaf_profile=default.evaluation_profile if reg['controller']=='DEFAULT' else metadata_unit._profile
    leaf_config=EvaluationConfig() if reg['controller']=='DEFAULT' else metadata_unit._config
    if reg['controller'] in ('STATIC_FIXED','DYNAMIC_FIXED','FULL_FIXED'):
        leaf_profile,leaf_config=profile,config
    order_profile=default.evaluation_profile if reg['controller']=='DEFAULT' else metadata_unit._profile
    order_config=EvaluationConfig() if reg['controller']=='DEFAULT' else metadata_unit._config
    players={0:attacker,1:player(c,1000)};started=now();tick=time.perf_counter();queries=[];censor=None
    while not s.state.terminal_status.is_terminal:
        if session.stopped():censor='user_stop';break
        if time.perf_counter()-tick>=reg['cap_seconds']:censor='whole_cap';break
        side=s.state.position.side_to_move;legal=s.legal_actions();t=time.perf_counter()
        d=players[side].choose_action(s,L.SearchLimits(max_depth=64,max_nodes=reg['nodes'],max_time_seconds=3,quiescence_max_depth=0,quiescence_hard_max_depth=8))
        queries.append(dict(actor=side,controller=reg['controller'] if side==0 else 'UNIT',root_ply=s.state.ply_count,state_sha256=L.state_sha(s.state),legal_count=len(legal),decision=L.record_value(d),action=L.record_value(d.action),seconds=time.perf_counter()-t))
        write_json(output,dict(status='RUNNING',started_at=started,queries=queries,current_record=L.record_value(s.to_record())))
        if d.action is None:censor='no_action';break
        assert d.action in legal
        executed=d.action
        if len(queries)==1 and reg.get('first_action_override') is not None:
            executed=L.match_action(s,reg['first_action_override'])
        queries[-1]['executed_action']=L.record_value(executed)
        s.submit(executed)
        print('PLY',s.state.ply_count,d.completed_depth,d.score,flush=True)
    row=dict(status='CLOSED',slot=dict(root=reg['root'],policy=reg['controller']),controller=reg['controller'],first_action_override=reg.get('first_action_override'),started_at=started,ended_at=now(),seconds=time.perf_counter()-tick,initial_record=root['record'],queries=queries,final_record=L.record_value(s.to_record()),final_state=L.record_value(s.state),terminal=L.record_value(s.result),censor=censor,value=L.outcome_value(s.result,0,censor),nodes_limit=reg['nodes'],generated_default_profile=reg['profile'],actual_leaf_profile=L.record_value(leaf_profile),actual_leaf_config=L.record_value(leaf_config),ordering_profile=L.record_value(order_profile),ordering_config=L.record_value(order_config))
    row.update(setup_seconds=tick-caller_tick,caller_seconds_before_final_write=time.perf_counter()-caller_tick,cost_scope='seconds=game_loop; caller includes setup before final serialization; module imports excluded')
    write_json(output,row);print('CLOSED',row['terminal']['status'],row['value'],len(queries),row['seconds'],flush=True)
    return row
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--registration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.input,a.registration,a.output)
