"""Replay the four bounded, posthoc material-horizon diagnostics."""
from pathlib import Path
from copy import copy
import json,gzip
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import restore,source_documents,write
from scripts.leaper_cooperative_certificate import encode_position
from scripts.verify_leaper_frozen_learning import replay_query
from generic_chess.core.actions import action_to_dict


def verify(directory,output):
    cfg=json.loads((directory/'plan.json').read_bytes());result=json.loads((directory/'result.json').read_bytes())
    world=json.loads(source_documents()['contact/inputs.json']);c=L.compile_rule(L.ruleset_from_dict(world['rule']));root=restore(c,cfg['record'])
    assert L.state_sha(root.state)==cfg['state_sha256']
    graph=Path('docs/research/data/leaper_ab_learning_and_rank_20261024/domain-0.json.gz');assert L.sha(graph)==cfg['graph_sha256']
    g=json.loads(gzip.decompress(graph.read_bytes()));ix={tuple(p):i for i,p in enumerate(g['positions'])};rows=[];pvs=0
    expected=[(d,a)for d in cfg['depths']for a in cfg['weights']]
    assert len(result['rows'])==len(expected)==4
    for row,(depth,arm)in zip(result['rows'],expected):
        assert (row['depth'],row['arm'])==(depth,arm);r=row['receipt']
        assert r['completed_depth']<=depth and r['nodes']<=cfg['nodes']
        if r['complete']:
            action=L.match_action(root,r['action']['action']);pvs+=replay_query(root,cfg['weights'][arm],r,action_to_dict(action))
            ch=copy(root);ch.submit(action);i=ix[tuple(encode_position(ch.state.position,c.initial_position))]
            physical=g['relative_values'][str(i)]*(1 if ch.state.position.side_to_move==0 else-1)
            if physical==0:assert row['chosen_value']==0 and row['chosen_basis']=='physical_DRAW_safety'
            elif g['ranks'][str(i)]>64-ch.state.ply_count:
                assert row['chosen_value']==0 and row['chosen_basis']=='complete_rank_clock_cutoff_DRAW'
            else:assert row['chosen_value']is None and row['chosen_basis']=='positive_child_history_barrier_UNKNOWN'
        else:assert row['chosen_value']is None and r['action']is None
        rows.append(dict(requested=depth,arm=arm,completed=r['completed_depth'],usable=r['complete'],reason=r['reason'],nodes=r['nodes'],chosen_value=row['chosen_value'],chosen_basis=row['chosen_basis']))
    out=dict(verified=True,queries=4,PV_plies=pvs,rows=rows,scope='Posthoc actual barrier prefix; no oracle TRAIN, incomplete PVs remainUNKNOWN. Complete rootWIN needs separate compact strategy proof; clock-cut DRAW uses existing complete finite-clock qualification, not Uniform payoff.')
    write(output,out);return out
