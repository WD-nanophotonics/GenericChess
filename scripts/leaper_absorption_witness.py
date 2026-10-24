"""Literal small action/defense and scoring counterfactual; no WDL solver."""
from pathlib import Path
from dataclasses import replace
from collections import Counter
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_rule_coordinates import physical_action
from tools.local_agent.common import write_json
from scripts.leaper_structural_counterfactual import load_document

def tree(rule,record,action_key):
    c=L.compile_rule(rule);s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(record)));assert not s.state.terminal_status.is_terminal
    actions={physical_action(L.record_value(a),rule.board_size):a for a in s.legal_actions()};assert tuple(action_key)in actions
    initial=L.record_value(s.state);s.submit(actions[tuple(action_key)]);defenses=[]
    for a in s.legal_actions():
        z=L.GameSession.replay(c,s.to_record());z.submit(a);defenses.append(dict(action=L.record_value(a),record=L.record_value(z.to_record()),state=L.record_value(z.state),result=L.record_value(z.result)))
    return dict(rule=L.ruleset_to_dict(rule,include_metadata=True),initial_record=record,initial_state=initial,action_key=action_key,child_record=L.record_value(s.to_record()),child_state=L.record_value(s.state),child_result=L.record_value(s.result),defenses=defenses)

def analyze(aux,paired):
    roots={(g['n'],g['mask'],r['rank']):r for g in aux['graphs']for r in g['roots']};events=[];drawing=[];first={}
    for row in paired['rows']:
        if row['H']!=64 or row['static_capacity'][0]!=row['static_capacity'][1]:continue
        for item in row['shared_value_mechanisms']:
            a,b=[roots[row['n'],mask,row['rank']]for mask in row['masks']];copies=[tree(L.ruleset_from_dict(r['rule']),r['record'],item['action'])for r in(a,b)]
            assert copies[0]['initial_state']['position']['board']==copies[1]['initial_state']['position']['board'];assert copies[0]['child_state']['position']['board']==copies[1]['child_state']['position']['board']
            assert [x['child_result']['status']for x in copies]==item['immediate_terminals'];key=tuple(item['immediate_terminals']);entry=dict(n=row['n'],masks=row['masks'],rank=row['rank'],action=item['action'],published_action_values=item['values'],trees=copies);events.append(entry);first.setdefault(key,entry)
        if row['fork'][0]!=row['fork'][1]and not row['shared_value_mechanisms']:
            assert row['fork']==[False,True]and row['WDL']==[1,1];r=roots[row['n'],row['masks'][1],row['rank']]
            for item in row['added_action_mechanisms']:
                if item['value']!=0:continue
                t=tree(L.ruleset_from_dict(r['rule']),r['record'],item['action']);capture=[d for d in t['defenses']if not any(p and p['current_type_id']=='A'for p in d['state']['position']['board'])]
                assert t['child_result']['status']=='stalemate'or capture
                drawing.append(dict(n=row['n'],masks=row['masks'],rank=row['rank'],tree=t,capture_A_defense_indices=[t['defenses'].index(d)for d in capture],scope='The published DRAW label is attributed. Literal capture reply leaves bare kings, not an independent all-history solver.'))
    # Preselected first instance of each class, then change only scoring.
    scoring=[]
    for mechanism,entry in first.items():
        for old in entry['trees']:
            base=L.ruleset_from_dict(old['rule']);assert base.stalemate_result=='draw';new=replace(base,stalemate_result='loss');record=L.deserialize_game_record(json.dumps(old['initial_record']));assert not record.actions
            c=L.compile_rule(new);s=L.GameSession(c);new_record=L.record_value(s.to_record());t=tree(new,new_record,entry['action']);assert t['child_state']['position']['board']==old['child_state']['position']['board'];assert [d['action']for d in t['defenses']]==[d['action']for d in old['defenses']]
            status=old['child_result']['status'];assert t['child_result']['status']==status
            if status=='stalemate':assert old['child_result']['winner']is None and t['child_result']['winner']==0
            elif status=='checkmate':assert old['child_result']['winner']==t['child_result']['winner']==0
            else:assert status=='ongoing'and t['child_result']['winner']is None
            scoring.append(dict(mechanism=list(mechanism),n=entry['n'],A_movement_atoms=next(p['movement_atoms']for p in old['rule']['piece_types']if p['type_id']=='A'),draw=old,loss=t))
    return dict(status='PASS',shared_revaluation_action_occurrences=len(events),shared_revaluation_witnesses=events,added_draw_actions=len(drawing),added_draw_witnesses=drawing,scoring_counterfactual_pairs=scoring,new_scoring_rule_children=len(scoring),original_scoring_reference_children=len(scoring),new_Player_queries=0,new_solver_calls=0,scope='Shared Core full-root/oneply/all-defender children; original WDL labels are AUX published evidence, not independently solved. Scoring changes immediate terminal payoff only, not an asserted new root WDL or all-domain theorem.')

def run(aux,paired,output):
    assert not output.exists();tick=time.perf_counter();r=analyze(load_document(aux),load_document(paired));r['seconds']=time.perf_counter()-tick;write_json(output,r);print('PASS',r['shared_revaluation_action_occurrences'],r['added_draw_actions'],r['new_scoring_rule_children'],r['seconds']);return r
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--aux-roots',type=Path,required=True);p.add_argument('--paired',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.aux_roots,a.paired,a.output)
