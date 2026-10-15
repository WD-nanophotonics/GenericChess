"""Independent horizon/prefix attribution from actual public transitions.

No new engine queries, reclassification as theoretical win, or refitting on DEV.
"""
import collections,json,time
from pathlib import Path
from generic_chess.core.transition import apply_action
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor,actor_state,uci
from generic_chess.core.movegen import legal_actions


def audit(folder):
    p=Path(folder);plan=json.loads((p/'plan.json').read_text());c=compile_rnb(plan.get("width",4))
    rows=[json.loads(x) for x in (p/'run/games.jsonl').read_text().splitlines()]
    families={f['family']:f for f in plan['families']};stats=collections.Counter();cells={};train={};start=time.perf_counter()
    for row in rows:
        s=from_actor(c,families[row['family']]['roots'][row['color']]);path=row['trajectory'];tail=row.get('tail_admission');H=plan['H']
        assert len(path)<=H+plan.get('tail_max_rank',64)
        prefix_pay=None;owner=None;last_rank=None
        for ply,step in enumerate(path):
            assert not s.terminal_status.is_terminal
            if ply==H:
                assert tail is not None and row['proof'] and plan['certified_tail']
                snap=row['horizon_snapshot'];assert tuple(snap['end'])==actor_state(s) and snap['payoff'] is None and snap['terminal']=='ongoing'
                assert type(tail['rank']) is int and 0<tail['rank']<=plan['tail_max_rank']
                owner=tail['owner'];last_rank=tail['rank'];stats['admissions']+=1
            z=step['decision']
            if ply>=H:
                assert tail is not None and z['source']!='PROOF'
                assert z['proof_nodes']==z['verification_nodes']==0
                if s.position.side_to_move==owner:
                    assert z['source']=='PROOF_CONTINUATION'
                    assert 0<z['proof_rank']<=last_rank
                    last_rank=z['proof_rank']-1
                else:last_rank-=1
                stats['tail_steps']+=1;stats['tail_native_go']+=z['source']=='EXTERNAL_SEARCH'
            actions={uci(a):a for a in legal_actions(s,c)}
            s=apply_action(s,actions[z['action']],c)
            if ply+1<=H and s.terminal_status.is_terminal:
                prefix_pay=0 if s.terminal_status.winner is None else (1 if s.terminal_status.winner==row['color'] else -1)
        if len(path)>H:
            assert len(path)-H<=tail['rank']
            if s.terminal_status.is_terminal:
                assert s.terminal_status.winner==owner and tail['remaining_rank']==0
                stats['actual_tail_wins']+=1
                stats['tail_candidate_wins' if owner==row['color'] else 'tail_opponent_wins']+=1
            else:
                assert row['payoff'] is None and tail['remaining_rank']>0
                stats['incomplete_tail_unknown']+=1
        if tail is not None:assert len(path)>H or row['payoff'] is None
        key=(row['phase'],row['proof'],row['price_index']);cell=cells.setdefault(key,collections.Counter())
        cell['n']+=1;cell['H16_WL']+=prefix_pay or 0;cell['tail_policy_WL']+=row['payoff'] or 0
        cell['H16_unknown']+=prefix_pay is None;cell['final_unknown']+=row['payoff'] is None
        cell['new_tail_events']+=prefix_pay is None and row['payoff'] is not None
        if row['phase']=='TRAIN':
            x=train.setdefault(row['price_index'],dict(H16=0,tail=0))
            x['H16']+=prefix_pay or 0;x['tail']+=row['payoff'] or 0
    result=dict(status='PASS_ACTUAL_TAIL_AND_PREFIX_AUDIT',counts=dict(stats),
                cells=[dict(phase=k[0],proof=k[1],price_index=k[2],**v) for k,v in sorted(cells.items())],
                TRAIN_scores=train,scope='Same trajectories prefix versus physical tail; H16 score is descriptive counterfactual prefix, not retrained H16 policy or independent DEV.',seconds=time.perf_counter()-start)
    if train:
        result['TRAIN_full_grid_prefix_choice']=min(train,key=lambda i:(-train[i]['H16'],plan['prices'][i]))
        result['TRAIN_full_grid_tail_choice']=min(train,key=lambda i:(-train[i]['tail'],plan['prices'][i]))
    (p/'tail_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':
    import sys;audit(sys.argv[1])
