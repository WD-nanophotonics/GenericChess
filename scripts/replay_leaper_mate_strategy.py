"""Replay a supplied finite all-defense mate strategy; never search for one."""
from __future__ import annotations
import argparse,json,time
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_rule_coordinates import physical_action
from tools.local_agent.common import write_json


def replay(raw_rule, raw_record):
    c=L.compile_rule(L.ruleset_from_dict(raw_rule))
    return c,L.GameSession.replay(c,L.deserialize_game_record(json.dumps(raw_record)))


def key(record):
    return json.dumps(record,sort_keys=True,separators=(',',':'))


def proposed_strategy(handoff):
    """Only supplied PV, two closed leaves, and Chat's explicit three moves."""
    c,root=replay(handoff['full_rule'],handoff['full_initial_record']);choices={}
    if c.board_size!=4:raise ValueError('literal strategy requires4x4')
    if L.state_sha(root.state)!=handoff['root_state_sha256']:raise ValueError('root state hash mismatch')
    for rec in [handoff['cooperative_mate7_complete_record']]+[r['literal_mate_record'] for r in handoff['already_closed_branches']]:
        ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(handoff['full_initial_record'])))
        for saved in L.deserialize_game_record(json.dumps(rec)).actions:
            raw=L.record_value(saved)
            if ss.state.position.side_to_move==0:
                k=key(L.record_value(ss.to_record()));p=physical_action(L.record_value(L.match_action(ss,raw)),4)
                if k in choices and choices[k]!=p:raise ValueError('supplied policy conflicts')
                choices[k]=p
            ss.submit(L.match_action(ss,raw))
    # Finite literal policy supplied in reply1792775120, not a choice optimizer.
    _,branch=replay(handoff['full_rule'],handoff['remaining_branch']['full_record'])
    if L.record_value(branch.state)!=handoff['remaining_branch']['full_state']:raise ValueError('remaining full history mismatch')
    def extend(ss,stage):
        if stage==3:return
        p=(('A',4,9,None),('K',0,5,None),('A',9,6,None))[stage]
        choices[key(L.record_value(ss.to_record()))]=p
        matches=[a for a in ss.legal_actions() if physical_action(L.record_value(a),4)==p]
        if len(matches)!=1:raise ValueError('supplied physical move is not uniquely legal')
        ss.submit(matches[0])
        if stage==2:return
        for defense in ss.legal_actions():
            child=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(L.record_value(ss.to_record()))))
            child.submit(defense);extend(child,stage+1)
    extend(branch,0)
    return choices


def verify(handoff,choices,max_plies=7,journal=None):
    """Check every legal defender child, exactly ONE supplied attacker choice."""
    tick=time.perf_counter();c,root=replay(handoff['full_rule'],handoff['full_initial_record']);nodes=[];leaves=[]
    def visit(ss):
        record=L.record_value(ss.to_record());state=ss.state
        row={'record':record,'state_sha256':L.state_sha(state),'full_state':L.record_value(state),'side':state.position.side_to_move,
             'terminal':L.record_value(state.terminal_status),'legal_actions':L.record_value(ss.legal_actions())}
        nodes.append(row)
        if journal is not None:
            with Path(journal).open('a',encoding='utf-8') as log:log.write(json.dumps(row,sort_keys=True)+'\n')
        if state.terminal_status.is_terminal:
            if state.terminal_status.winner!=0:raise ValueError('strategy has a nonwinning terminal')
            leaves.append(state.ply_count);return
        if state.ply_count>=max_plies:raise ValueError('strategy exceeds claimed mate bound')
        legal=ss.legal_actions()
        if state.position.side_to_move==0:
            chosen=choices.get(key(record))
            matching=[a for a in legal if physical_action(L.record_value(a),4)==chosen]
            if len(matching)!=1:raise ValueError('missing or nonunique legal attacker choice')
            row['chosen_physical_action']=chosen;actions=matching
        else:actions=legal
        if not actions:raise ValueError('nonterminal node has no continuation')
        row['checked_child_actions']=L.record_value(actions)
        for a in actions:
            child=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(record)))
            child.submit(a);visit(child)
    visit(root)
    return {'status':'PASS','input_rule_sha256':L.compute_fingerprint(L.ruleset_from_dict(handoff['full_rule'])),
            'source_root_state_sha256':L.state_sha(root.state),'nodes':nodes,'node_count':len(nodes),'leaf_count':len(leaves),
            'terminal_absolute_plies':leaves,'maximum_absolute_plies':max(leaves),'claimed_max_plies':max_plies,
            'root_WDL_for0':1,'seconds':time.perf_counter()-tick,'Player_calls':0,'solver_calls':0,
            'scope':'Finite supplied attacker policy, ALL literal Core defender legal actions on complete histories. No shortest-distance claim or other-root/general-rule solver. Shared Core is not independent engine.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if any(q.exists() for q in (a.output,a.output.with_suffix('.policy.json'),a.output.with_suffix('.returns.jsonl'))):raise FileExistsError('fresh certificate output required')
    h=json.loads(a.input.read_text(encoding='utf-8'));choices=proposed_strategy(h)
    write_json(a.output.with_suffix('.policy.json'),{'schema':'finite_record_keyed_attacker_policy_v1','choices':[{'record':json.loads(k),'physical_action':v} for k,v in choices.items()]})
    result=verify(h,choices,journal=a.output.with_suffix('.returns.jsonl'));result['source_handoff_sha256']=L.sha(a.input);write_json(a.output,result);print(json.dumps({k:v for k,v in result.items() if k!='nodes'}))

if __name__=='__main__':main()
