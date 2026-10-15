"""Actual closed-loop cost/W-L comparison for frozen ALL and SMALL policies."""
import json,random,collections
from pathlib import Path
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor,uci
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.core.position import count_entities
from scripts.generic_proof_study_audit import quantile,planned_bounds


def run(all_folder,small_folder,outfile):
    folders=[Path(all_folder),Path(small_folder)];plans=[json.loads((p/'plan.json').read_text()) for p in folders]
    for key in ('families','prices','binary_sha256','variant_sha256','model_sha256','candidate_nodes','opponents','H','tail_max_rank','step_seconds','solver_sha256','pn_sha256','player_sha256','study_sha256'):
        assert plans[0][key]==plans[1][key],key
    assert [p['proof_trigger'] for p in plans]==['ALL','SMALL'];plan=plans[0];c=compile_rnb(plan['width']);families={f['family']:f for f in plan['families']};allrows=[];policy_checks=[]
    for mode,p in zip(('ALL','SMALL'),folders):
        rows=[json.loads(x) for x in (p/'run/games.jsonl').read_text().splitlines()];allrows.append(rows);counts=collections.Counter()
        for row in rows:
            s=from_actor(c,families[row['family']]['roots'][row['color']])
            for ply,step in enumerate(row['trajectory']):
                z=step['decision'];entities=count_entities(s.position)
                if row['proof'] and ply<plan['H'] and z['source']!='PROOF_CONTINUATION':
                    if mode=='SMALL' and entities>4:
                        assert z['proof_nodes']==z['verification_nodes']==0 and z['proof_reason']=='trigger_skipped';counts['large_state_skipped']+=1
                    else:
                        assert z['proof_reason']!='trigger_skipped';counts['new_proof_attempts']+=1
                if z['source']=='PROOF':
                    assert mode=='ALL' or entities<=4;counts['new_verified_proofs']+=1
                if z['source']=='PROOF_CONTINUATION':counts['preserved_strategy_moves']+=1
                a=next(a for a in legal_actions(s,c) if uci(a)==z['action']);s=apply_action(s,a,c)
        policy_checks.append(dict(mode=mode,counts=dict(counts)))
    indexes=[{(r['family'],r['proof'],r['price_index'],r['color'],r['opponent']):r for r in rows} for rows in allrows];comparisons=[];rng=random.Random(20261015561)
    planned_n=2*len(plan['opponents'])*len(plan['families']);plain_checks=[]
    for price_index,price in enumerate(plan['prices']):
        values=[];missing=[]
        for family in families:
            diffs=[]
            for color in (0,1):
                for op in plan['opponents']:
                    key=(family,True,price_index,color,op['id']);left=indexes[0].get(key);right=indexes[1].get(key)
                    if left is not None and right is not None:diffs.append((right['payoff'] or 0)-(left['payoff'] or 0))
            if len(diffs)==2*len(plan['opponents']):values.append(sum(diffs)/len(diffs))
            else:missing.append(family)
        samples=[sum(rng.choice(values) for _ in values)/len(values) for _ in range(5000)] if values else []
        cells=[]
        for mode,rows in zip(('ALL','SMALL'),allrows):
            data=[r for r in rows if r['proof'] and r['price_index']==price_index];decisions=[z['decision'] for r in data for z in r['trajectory']]
            cells.append(dict(mode=mode,games=len(data),actual_WL_events=sum(r['payoff'] or 0 for r in data),UNKNOWN=sum(r['payoff'] is None for r in data),sum_game_seconds=sum(r['seconds'] for r in data),sum_decision_seconds=sum(z['seconds'] for z in decisions),proof_nodes=sum(z['proof_nodes'] for z in decisions),native_go=sum(z['source']=='EXTERNAL_SEARCH' for z in decisions),native_reported_nodes=sum(z['search_nodes'] for z in decisions),**planned_bounds(data,planned_n,plan)))
        comparisons.append(dict(price=price,cells=cells,complete_paired_families=len(values),missing_families=missing,SMALL_minus_ALL_event_difference=sum(values)/len(values) if values else None,family_bootstrap95=[quantile(samples,.025),quantile(samples,.975)] if samples else None,SMALL_to_ALL_game_cost_ratio=cells[1]['sum_game_seconds']/cells[0]['sum_game_seconds'] if cells[0]['sum_game_seconds'] else None,full_plan_difference_bounds=[cells[1]['planned_finite_event_bounds'][0]-cells[0]['planned_finite_event_bounds'][1],cells[1]['planned_finite_event_bounds'][1]-cells[0]['planned_finite_event_bounds'][0]]))
        identical=changed=missing_plain=0
        for key,left in indexes[0].items():
            if key[1] or key[2]!=price_index:continue
            right=indexes[1].get(key)
            if right is None:missing_plain+=1;continue
            path=lambda r:[(z['actor'],z['decision']['action']) for z in r['trajectory']]
            if path(left)==path(right) and left['payoff']==right['payoff'] and left['end']==right['end']:identical+=1
            else:changed+=1
        plain_checks.append(dict(price=price,identical_plain_paths=identical,changed_plain_paths=changed,missing=missing_plain))
    result=dict(status='PASS_FIXED_POLICY_CONDUCT_AND_PAIRED_COMPARISON',policy_checks=policy_checks,comparisons=comparisons,plain_reference_checks=plain_checks,scope='Fixed priorTRAIN prices, fresh paired roots. Real game cost includes public observe/transition work; study initialization/qualification separate. Visit units across engines differ. No prespecified noninferiority margin, so an interval crossing zero does NOT establish no loss, nor a new optimal price under SMALL. Ordinary concurrent machine load remains an interpretation limit.')
    Path(outfile).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':
    import sys;run(*sys.argv[1:])
