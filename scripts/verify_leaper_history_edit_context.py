"""Literal full-GameState verification of retained history-coordinate witnesses."""
from copy import copy
from pathlib import Path
import argparse,json,time,hashlib
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_history_edit_context import SOURCE
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_h6_pair_certificates import physical_position,repetition_partition
from scripts.leaper_microgames import ExactTree,role_stop_requested
from scripts.research_record import record_value
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.core.actions import action_to_dict,action_from_dict
from generic_chess.core.identity import search_state_identity

def verify(census_path,output):
    tick=time.perf_counter();data=load(census_path);inputs=load(SOURCE/'inputs.json.gz');adj=load(SOURCE/'adjacent-pairs.json.gz');pair=adj['pairs'][0]
    if data['status']!='COMPLETE' or data['plan']['adjacency_digest']!=digest(adj):raise ValueError('unbound census')
    assert data['plan']['source_sha256']==hashlib.sha256(Path('scripts/leaper_history_edit_context.py').read_bytes()).hexdigest()
    cases=[];allnodes=0
    for label,twins in data['witnesses'].items():
        rows=[]
        for wi,witness in enumerate(twins):
            arms=[]
            for arm,tag,key in ((0,'left_family','left_record'),(1,'right_family','right_record')):
                if role_stop_requested():raise RuntimeError('USER_STOP')
                family=next(f for f in inputs['families']if f['family']==pair[tag]);source=next(r for r in inputs['rows']if r['family']==family['family']);c=admit(family,source)
                d=load(SOURCE/f"domain{family['family']}.json.gz");s=GameSession.replay(c,deserialize_game_record(json.dumps(pair['rows'][witness['origin']][key])))
                frames=[dict(record=record_value(s.to_record()),state=record_value(s.state),terminal=record_value(s.result))]
                v=next(r for r in load(SOURCE/'truth.json.gz')['roots']if r['id']==pair['rows'][witness['origin']]['left_id'if arm==0 else'right_id'])['root_index']
                prior=0
                for offsets in witness['path_offsets']:
                    if s.result.status.value!='ongoing':raise ValueError('prefix traverses terminal')
                    actual=s.legal_actions();expected=d['actions'][v]
                    if [action_to_dict(a)for a in actual]!=expected:raise ValueError('actual frontier differs')
                    j=offsets[arm];prior|=1<<v;s.submit(actual[j]);v=d['edges'][v][j]
                    frames.append(dict(record=record_value(s.to_record()),state=record_value(s.state),terminal=record_value(s.result)))
                if (v!=witness['left_vertex'if arm==0 else'right_vertex']or 6-s.state.ply_count!=witness['remaining']or hex(prior)!=witness['prior_left'if arm==0 else'prior_right']or (s.result.status.value!='ongoing')!=witness['ended'][arm]):raise ValueError('literal witness context differs')
                wire=serialize_game_record(s.to_record());replay=GameSession.replay(c,deserialize_game_record(wire))
                if replay.state!=s.state or replay.result!=s.result:raise ValueError('full-record replay differs')
                tree=ExactTree(c,max_states=100000,seconds=30);value=tree.solve(s.state)
                if value!=witness['values'][arm]:raise ValueError('full-GameState truth refutes compact witness')
                tree_rows=[]
                for state,vv in tree.values.items():
                    tree_rows.append(dict(state=record_value(state),value=vv,children=[dict(action=action_to_dict(a),state=record_value(ch),value=tree.values[ch])for a,ch in tree.edges[state]]))
                allnodes+=len(tree_rows)
                actions=[dict(action=action_to_dict(a),value=tree.values[ch])for a,ch in tree.edges[s.state]]
                arms.append(dict(fingerprint=c.ruleset_fingerprint,source_record=pair['rows'][witness['origin']][key],frames=frames,
                    final_record=record_value(s.to_record()),final_state=record_value(s.state),final_terminal=record_value(s.result),
                    physical_position=physical_position(s.state.position),value=value,actions=actions,
                    repetition_partition=repetition_partition(s),search_identity=record_value(search_state_identity(s.state,c)),
                    tree_summary=tree.summary(),complete_tree=tree_rows))
            if arms[0]['physical_position']!=arms[1]['physical_position']:raise ValueError('crossrule physical mismatch')
            rows.append(dict(origin=witness['origin'],placement=witness['placement'],arms=arms))
        contrasts=[]
        for arm in(0,1):
            a,b=[r['arms'][arm]for r in rows]
            if a['fingerprint']!=b['fingerprint']or a['physical_position']!=b['physical_position']or a['final_state']['ply_count']!=b['final_state']['ply_count']:raise ValueError('twins mismatch')
            contrasts.append(a['value']!=b['value'])
            if a['search_identity']==b['search_identity']:raise ValueError('complete search identity merged differing history')
        if not any(contrasts):raise ValueError('no actual WDL contrast in either arm')
        cases.append(dict(label=label,arm_value_contrast=contrasts,rows=rows))
    result=dict(verified=True,census_digest=digest(data),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=cases,
        literal_full_tree_nodes=allnodes,seconds=time.perf_counter()-tick,
        scope='Every retained BFS witness arm and complete remaining actual-Core tree; independent full GameState recurrence, shared rules/Core. No Player, altered clock, invented history or policy gain. Equal Position/clock is insufficient for score-bound reuse even when both current nodes are ongoing; position-only legal move hints are a different intervention.')
    Path(output).write_text(json.dumps(result,indent=2));print({k:v for k,v in result.items()if k!='cases'});return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--census',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.census,a.output)
