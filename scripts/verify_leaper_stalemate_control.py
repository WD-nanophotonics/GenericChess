"""Independently rebind only the stated stalemate-loss counterfactual.

This is not admission to the original frozen DRAW rule or a default change.
Every physical frontier is checked under the changed compiled RuleSet, and
finite ranks are lifted only with the explicit one-sided scoring premise.
"""
from collections import Counter
import json,time
from scripts.leaper_design import compile_rule,ruleset_from_dict,state_sha
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_retrograde import fresh_state,attractor
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record


def verify(saved,original,source_roots,*,seconds=300):
    tick=time.perf_counter();expected=json.loads(json.dumps(original['rule']));expected['stalemate_result']='loss'
    if saved['plan']['rule']!=expected:raise ValueError('counterfactual changed more than stalemate result')
    c=compile_rule(ruleset_from_dict(expected));positions=[decode_position(z,c.initial_position)for z in original['positions']];indices={p:i for i,p in enumerate(positions)}
    terms={};edges=[];counts=Counter()
    for i,pos in enumerate(positions):
        if i%128==0:
            if role_stop_requested():raise RuntimeError('USER_STOP')
            if time.perf_counter()-tick>=seconds:raise RuntimeError('STALEMATE_COUNTERFACTUAL_READER_CAP_UNKNOWN')
        s=fresh_state(pos,c);counts['Core_vertices']+=1
        if s.terminal_status.is_terminal:
            winner=s.terminal_status.winner
            if winner!=0:raise ValueError('one-sided scoring premise failed')
            terms[i]=1 if pos.side_to_move==0 else-1;edges.append([]);counts['terminal_'+s.terminal_status.status.value+':'+str(winner)]+=1
        else:
            ee=[];aa=[]
            for a,ch in legal_successors(s,c):
                if ch.position not in indices:raise ValueError('counterfactual closure differs')
                ee.append(indices[ch.position]);aa.append(action_to_dict(a));counts['Core_edges']+=1
            if ee!=original['edges'][i]or aa!=original['actions'][i]:raise ValueError('physical move frontier changed')
            edges.append(ee)
    values,ranks=attractor(edges,terms)
    if len(saved['rows'])!=len(source_roots):raise ValueError('counterfactual root coverage differs')
    rows=[]
    for sr,row in zip(source_roots,saved['rows'],strict=True):
        expected_record=dict(sr['record'],ruleset_fingerprint=c.ruleset_fingerprint)
        if row['original_record']!=sr['record']or row['counterfactual_record']!=expected_record:raise ValueError('counterfactual source record differs')
        s=GameSession.replay(c,deserialize_game_record(json.dumps(expected_record)));i=indices[s.state.position];remaining=64-s.state.ply_count
        if s.result.status.value!='ongoing'or max(n for _,n in s.state.repetition_counts)>2:raise ValueError('counterfactual history lift not admitted')
        value=values[i]if values[i]and ranks[i]<=remaining else 0
        if row['counterfactual_state_sha']!=state_sha(s.state)or row['graph_value']!=values[i]or row['rank']!=ranks.get(i)or row['value']!=value:raise ValueError('counterfactual rank/history label differs')
        rows.append(dict(value=value,rank=ranks.get(i),remaining=remaining,state_sha=state_sha(s.state)))
    if dict(counts)!=saved['counts']or max(ranks.values(),default=0)!=saved['maximum_rank']:raise ValueError('counterfactual accounting differs')
    return dict(verified=True,counts=dict(counts),rows=rows,seconds=time.perf_counter()-tick,
        scope='Explicitchangedterminalauthorityonly. Currentoriginalstalemate-DRAWrootsremainDRAW; counterfactualWINisnotactualpolicygainorprojectdefault. FullCorefrontiersandcompleteincomingrecordsreread; strictone-sidedrankpreconditionschecked.')
