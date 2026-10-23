"""Portable evidence reader for the bounded scope/headroom continuation.

No Player, experimental learning or source capsules are executed. Complete
Core closure/safety frontiers, real full histories/PVs and exact rational
nominal controls have separate receipts and interpretation limits.
"""
from collections import Counter
from copy import copy
from pathlib import Path
import argparse,hashlib,json,time
from scripts.leaper_explorer_truth import load,digest
from scripts.verify_leaper_twoa_graph import verify as graph_verify
from scripts.verify_leaper_twoa_safety import verify as safety_verify,SOURCE
from scripts.leaper_clock_rebinding import verify_history_draw_safety
from scripts.leaper_design import compile_rule,ruleset_from_dict,state_sha,match_action
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.leaper_h6_headroom import analyze as headroom
from scripts.leaper_h6_policy_bounds import analyze as policy_bounds
from scripts.leaper_material_trade_cells import examples as trade_cells
from scripts.leaper_twoa_exposure_bounds import analyze as exposure_bounds
from scripts.leaper_static_capacity_scope import analyze as capacity_scope
from scripts.verify_leaper_stalemate_control import verify as stalemate_control
from scripts.research_record import record_value
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict,action_from_dict
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE


def verify_panel(panel,g):
    counts=Counter();c=compile_rule(ruleset_from_dict(g['rule']));contexts={r['vertex']:r for r in panel['contexts']}
    required={i for i,r in g['ranks'].items()if r==3 and g['positions'][i][0]==0}
    if set(contexts)!=required or len(contexts)!=48:raise ValueError('rank3 census differs')
    seen=set()
    from scripts.leaper_cooperative_certificate import encode_position
    for row in panel['rows']:
        i=row['vertex'];depth=row['depth'];key=i,depth
        if key in seen or depth not in(1,2,3):raise ValueError('duplicate/unplanned query')
        seen.add(key);source=contexts[i];s=GameSession.replay(c,deserialize_game_record(json.dumps(source['record'])));r=row['receipt']
        if state_sha(s.state)!=source['state_sha']or encode_position(s.state.position,c.initial_position)!=g['positions'][i]:raise ValueError('actual source history differs')
        if s.result.status.value!='ongoing'or max(n for _,n in s.state.repetition_counts)>2 or s.state.ply_count+3>64:raise ValueError('history rank lift not admitted')
        if not r['complete']or r['completed_depth']!=depth or not r['pv_choices']or r['pv_choices'][0]!=r['action']:raise ValueError('query/PV incomplete')
        typed=action_from_dict(row['action'])
        if typed not in s.legal_actions():raise ValueError('reported action is illegal')
        action=action_to_dict(typed)
        if record_value(typed)!=r['action']['action']:raise ValueError('reported action differs')
        k=g['actions'][i].index(action);j=g['edges'][i][k];value=g['values'][j]if g['positions'][j][0]==0 else-g['values'][j]
        if value!=row['exact_WDL_for0']:raise ValueError('actual action quality differs')
        for choice in r['pv_choices']:
            if choice['kind']!='ACTION':raise ValueError('unsupported PV choice')
            s.submit(match_action(s,choice['action']));counts['PV_Core_edges']+=1
        env=FixedScaleSessionEnv(s,unit_type='A');terminal=env.terminal();phi=None if terminal is not None else list(env.features());model=Model([1.]*len(env.names))
        if r['pv_terminal']!=(terminal is not None)or r['pv_phi']!=phi:raise ValueError('actual PV terminal/feature differs')
        score=MATE*terminal if terminal is not None else model.raw(phi)
        if score!=r['value']:raise ValueError('literal PV value differs')
        counts['Player_queries_retained']+=1;counts['nodes_retained']+=r['nodes'];counts[f'D{depth}_inferior']+=value<1
    if seen!={(i,d)for i in required for d in(1,2,3)}:raise ValueError('query census incomplete')
    if counts['nodes_retained']!=panel['counts']['nodes']or counts['Player_queries_retained']!=144:raise ValueError('paid accounting differs')
    return dict(verified=True,counts=dict(counts),scope='144existingactualqueriesandPVsreplayed;0newPlayer. Rank3truth-selecteddiagnostics,notpopulationerror/occupation/trainingstartsorutility.')


def verify(directory,output,*,full_h6=False):
    directory=Path(directory);output=Path(output);output.mkdir(exist_ok=False);tick=time.perf_counter()
    manifest=load(directory/'manifest.json')
    for name,sha in manifest['files_sha256'].items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=sha:raise ValueError('data bytes differ:'+name)
    result=dict(source_checks=len(manifest['files_sha256']),source_capsules_executed=False,new_Player_calls=0,new_experimental_training=0)
    packet=load(directory/'twoa-graph.json.gz');source=load(SOURCE)
    receipt,g=graph_verify(packet,source,return_graph=True);result['twoa_graph']=receipt
    result['twoa_roots']=safety_verify(load(directory/'twoa-safety.json.gz'),source)
    result['twoa_barrier']=safety_verify(load(directory/'twoa-barrier-safety.json.gz'),source)
    pair=load(directory/'twoa-equalclock.json');barrier=load(directory/'twoa-barrier-safety.json.gz');c=compile_rule(ruleset_from_dict(packet['rule']))
    win=GameSession.replay(c,deserialize_game_record(json.dumps(pair['record'])));draw=GameSession.replay(c,deserialize_game_record(json.dumps(barrier['roots'][0]['record'])))
    if win.state.position!=draw.state.position or win.state.ply_count!=draw.state.ply_count or state_sha(win.state)!=pair['state_sha']:raise ValueError('controlled history pair differs')
    decoded,cert=decode_session_certificate(c,pair['proof'])
    if decoded.state!=win.state:raise ValueError('decoded certificate root differs')
    result['equalclock_win']=verify_session_certificate(win,cert,max_nodes=10000,seconds=30)
    if not result['equalclock_win']['verified']:raise ValueError('literal all-defense win certificate failed')
    result['actual_panel']=verify_panel(load(directory/'twoa-actual-panel.json.gz'),g)
    result['stalemate_control']=stalemate_control(load(directory/'stalemate-control.json'),g,packet['roots'])
    singles=load(directory/'singletons.json.gz');sr=[]
    for row in singles['rows']:
        r=verify_history_draw_safety(row['safety_certificate'],row['rule'],row['record'],row['safety'],seconds=60,frozen_singleton=dict(n=row['n'],mask=row['mask']))
        s=GameSession.replay(compile_rule(ruleset_from_dict(row['rule'])),deserialize_game_record(json.dumps(row['record'])))
        if state_sha(s.state)!=row['state_sha']:raise ValueError('singleton history differs')
        b=row['position'][1];a=b.index('2');v=b.index('3');n=row['n']
        if max(abs(a%n-v%n),abs(a//n-v//n))<3:raise ValueError('not union-safe')
        for ac in row['cooperative_path']:s.submit(action_from_dict(ac))
        if s.result.winner!=0 or s.result.status.value!='checkmate':raise ValueError('singleton cooperative path differs')
        sr.append(r)
    result['singletons']=sr
    oldbase=Path('docs/research/data/leaper_h6_initial_truth_20261023')
    h=headroom(oldbase,output/'h6-headroom');saved=load(directory/'h6-headroom.json')
    if h['rows']!=saved['rows']or h['counts']!=saved['counts']:raise ValueError('headroom reproduction differs')
    models=load(directory/'models.json')['models'];p=policy_bounds(oldbase,output/'h6-policies',models);saved=load(directory/'h6-policy-bounds.json.gz')
    if p['rows']!=saved['rows']:raise ValueError('nominal chance policy reproduction differs')
    result['h6_reproduced']=dict(headroom_counts=h['counts'],policy_rows=len(p['rows']))
    if digest(trade_cells())!=digest(load(directory/'material-trade-cells.json')):raise ValueError('material cell derivation differs')
    # Reuse the just rebuilt graph to reproduce the rational shadow bounds.
    gg=dict(g,roots=packet['roots'],values=[g['values'][i]for i in range(len(g['positions']))],ranks=[g['ranks'].get(i)for i in range(len(g['positions']))])
    ex=exposure_bounds(gg,output/'twoa-exposure');saved=load(directory/'twoa-exposure.json')
    if ex['rows']!=saved['rows']:raise ValueError('exact exposure bound differs')
    result['exposure_reproduced']=dict(rows=len(ex['rows']))
    cs=capacity_scope(Path('docs/research/data/leaper_frozen_pair_truth_20261024/packet.json.gz'),output/'capacity-scope')
    if cs['rows']!=load(directory/'capacity-scope.json')['rows']:raise ValueError('all-placement capacity scope differs')
    result['capacity_scope_reproduced']=dict(graphs=len(cs['rows']))
    if full_h6:
        from scripts.verify_leaper_h6_history_classes import verify as classes
        result['h6_actual_classes']=classes(oldbase,output/'h6-classes')
    result.update(verified=True,seconds=time.perf_counter()-tick)
    (output/'result.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--full-h6',action='store_true');a=p.parse_args();verify(a.directory,a.output,full_h6=a.full_h6)
