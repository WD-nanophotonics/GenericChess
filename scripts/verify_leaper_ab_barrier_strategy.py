"""Finite strict-rank strategy certificate, distinct from capped history tree.

All admitted strategy positions have unique repetition identities. Every future
position occurs at most once because rank strictly decreases. Incoming counts
of every non-root strategy key are <=2; repeat4 therefore cannot fire. A strict
clock margin and literal terminal wins finish the history lift.
"""
from pathlib import Path
from collections import Counter
import argparse,gzip,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import restore,source_documents,write
from scripts.leaper_cooperative_certificate import encode_position,decode_position
from scripts.leaper_retrograde import fresh_state
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action


def verify(directory,output):
    tick=time.perf_counter();spec=json.loads((directory/'spec.json').read_bytes());saved=json.loads((directory/'policy.json').read_bytes())
    graph=Path('docs/research/data/leaper_ab_learning_and_rank_20261024/domain-0.json.gz');assert L.sha(graph)==spec['graph_sha256']
    g=json.loads(gzip.decompress(graph.read_bytes()));world=json.loads(source_documents()['contact/inputs.json']);assert g['rule']==world['rule']
    c=L.compile_rule(L.ruleset_from_dict(world['rule']))
    assert c.ruleset_fingerprint=='da92b6a1c814795b455875a48540227f34c94807932a559d309c67ccc6a520e5'
    root=restore(c,spec['record']);assert not root.state.terminal_status.is_terminal and L.state_sha(root.state)==spec['state_sha256']
    assert root.state.ply_count==36 and 64-root.state.ply_count==spec['remaining']
    ranks={int(k):v for k,v in g['ranks'].items()};policy={int(k):v for k,v in saved['policy'].items()};index=spec['index']
    assert list(encode_position(root.state.position,c.initial_position))==g['positions'][index]
    assert ranks[index]==spec['original_rank']<spec['remaining']
    ix={tuple(p):i for i,p in enumerate(g['positions'])};incoming=dict(root.state.repetition_counts);seen=set();identities={};stack=[index];frontiers=[];terminals=[];counts=Counter()
    while stack:
        if role_stop_requested():raise RuntimeError('USER_STOP')
        i=stack.pop()
        if i in seen:continue
        seen.add(i);p=decode_position(g['positions'][i],c.initial_position);key=repetition_identity_key(p,c)
        assert key not in identities or identities[key]==i
        identities[key]=i
        assert i==index or incoming.get(key,0)<=2
        state=fresh_state(p,c)
        if state.terminal_status.is_terminal:
            assert state.terminal_status.winner==0 and ranks[i]==0 and i not in policy
            terminals.append(dict(index=i,rank=0,winner=0));continue
        assert i in policy and policy[i]
        actual=[];actions=[]
        for a in legal_actions(state,c):
            child=apply_action(state,a,c);j=ix[tuple(encode_position(child.position,c.initial_position))];actual.append(j)
            if j in policy[i]:actions.append(dict(action=L.record_value(a),child=j))
        if p.side_to_move==1:assert Counter(actual)==Counter(policy[i])
        else:assert len(policy[i])==1 and policy[i][0]in actual
        assert all(j in ranks and ranks[j]<ranks[i]for j in policy[i])
        frontiers.append(dict(index=i,rank=ranks[i],actor=p.side_to_move,legal_count=len(actual),selected_children=policy[i],selected_actions=actions,incoming_count=incoming.get(key,0)))
        stack.extend(policy[i]);counts['actual_legal_edges']+=len(actual);counts['selected_graph_edges']+=len(policy[i])
    assert set(policy)=={r['index']for r in frontiers}
    assert len(identities)==len(seen)
    out=dict(verified=True,status='WIN0',root_state_sha256=spec['state_sha256'],root_record=spec['record'],graph_sha256=L.sha(graph),strategy_sha256=L.sha(directory/'policy.json'),spec_sha256=L.sha(directory/'spec.json'),
        root_original_rank=ranks[index],remaining=spec['remaining'],strict_clock_margin=spec['remaining']-ranks[index],strategy_positions=len(seen),nonterminal_strategy_positions=len(frontiers),actual_winning_terminals=len(terminals),injective_strategy_repetition_keys=len(identities),counts=dict(counts),frontiers=frontiers,terminals=terminals,
        seconds=time.perf_counter()-tick,Player_queries=0,training_updates=0,
        scope='ONE actual exposed contact history. Every chosen winner edge and every defender legal edge checked through Core; strict rank, actual complete root and repetition-identity injection with incoming counts<=2 on future keys, strict clock margin. New compact strategy proof, NOT extension/completion of the old20k history-tree cap. Shared Core, no generic quotient, oracle TRAIN or default policy. Other barriers stayUNKNOWN.')
    write(output,out);print({k:v for k,v in out.items()if k not in('root_record','frontiers','terminals')},flush=True);return out


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();verify(a.directory,a.output)
