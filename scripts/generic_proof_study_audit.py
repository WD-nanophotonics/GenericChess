"""Independent public replay, protocol/budget audit, and family paired contrasts."""
import collections,hashlib,json,random,statistics,time
from pathlib import Path
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor,actor_state,uci,orbit
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.core.terminal import terminal_result
from scripts.generic_proof_roles import roles,row_role,row_target


def quantile(x,q):return sorted(x)[int((len(x)-1)*q)]


def incomplete(row,plan):
    return row['payoff'] is None and (len(row['trajectory'])<plan['H'] or row.get('tail_admission') is not None)


def planned_bounds(rows,planned_n,plan):
    if planned_n<=0 or len(rows)>planned_n:raise ValueError('invalid planned denominator')
    missing=planned_n-len(rows);early=sum(incomplete(r,plan) for r in rows)
    net=sum(r['payoff'] or 0 for r in rows);unknown=sum(r['payoff'] is None for r in rows)
    return dict(planned_n=planned_n,missing_games=missing,early_incomplete=early,
                planned_finite_event_bounds=[(net-missing-early)/planned_n,(net+missing+early)/planned_n],
                planned_infinite_outcome_bounds=[(net-missing-unknown)/planned_n,(net+missing+unknown)/planned_n])


def audit(folder):
    p=Path(folder);plan=json.loads((p/'plan.json').read_text());start=time.perf_counter();c=compile_rnb(plan.get("width",4))
    rows=[json.loads(x) for x in (p/'run/games.jsonl').read_text().splitlines()]
    choices=[json.loads(x) for x in (p/'run/choices.jsonl').read_text().splitlines()]
    acks=[json.loads(x) for x in (p/'run/acks.jsonl').read_text().splitlines()]
    families={f['family']:f for f in plan['families']};seen=set();root_orbits=set();steps=0;proofcalls=0;continuations=0;overruns=0;early_unknown=0;over_time=0;max_time=0.
    for f in plan['families']:
        key=orbit(tuple(f['roots'][0]));assert not key&root_orbits;root_orbits.update(key)
    choice_index=0;conversion=collections.Counter()
    for row in rows:
        key=(row['family'],row['proof'],row['price_index'],row['color'],row['opponent'],row_role(row));assert row_role(row) in roles(plan);assert key not in seen;seen.add(key)
        f=families[row['family']];state=from_actor(c,f['roots'][row['color']]);target=row_target(row,state.position.side_to_move)
        assert row['phase']==f['phase'] and row['price']==plan['prices'][row['price_index']]
        assert type(row.get('candidate_side',target)) is int
        if len(roles(plan))>1:assert 'candidate_role' in row and 'candidate_side' in row
        assert type(row.get('opponent_proof',row['proof'])) is bool
        assert row.get('opponent_proof',row['proof'])==plan.get('opponent_proof',row['proof'])
        op=next(o for o in plan['opponents'] if o['id']==row['opponent'])
        for step in row['trajectory']:
            assert actor_state(state)==tuple(step['actor']);z=step['decision'];actions={uci(a):a for a in legal_actions(state,c)};assert z['action'] in actions
            cap=plan['candidate_nodes'] if state.position.side_to_move==target else op['nodes']
            max_time=max(max_time,z['seconds']);over_time+=z['seconds']>plan['step_seconds']
            assert z['nodes']==z['proof_nodes']+z['verification_nodes']+z['search_nodes']
            assert z['proof_nodes']<=cap//4 and z['verification_nodes']<=cap//4
            enabled=row['proof'] if state.position.side_to_move==target else row.get('opponent_proof',row['proof'])
            assert enabled or z['proof_nodes']==z['verification_nodes']==0
            if z['source']=='EXTERNAL_SEARCH':
                receipt=choices[choice_index];ack=acks[choice_index];choice_index+=1
                assert tuple(receipt['state'])==actor_state(state) and receipt['raw'][-1].split()[1]==z['action']
                assert receipt['reported_nodes']==z['search_nodes']
                assert receipt['requested_nodes']==cap-z['proof_nodes']-z['verification_nodes']
                price=row['price'] if state.position.side_to_move==target else plan['prices'][plan.get('baseline_index',0)]
                assert receipt['price']==price and ack['price']==price and ack['explicit_clear_commands']==1
                if ack['variant_ack']:
                    expected='info string DEV_AUX leafRNBP '+' '.join(map(str,price))+f' nativeP {price[3]} nativeR {price[0]} nativeN {price[1]} nativeB {price[2]} captureP {price[3]} captureR {price[0]} captureN {price[1]} captureB {price[2]}'
                    assert expected in ack['ack']
                overruns+=receipt['reported_nodes']>receipt['requested_nodes']
            elif z['source']=='PROOF':
                assert enabled and z['proof_nodes']>0 and z['verification_nodes']>0;proofcalls+=1
            elif z['source']=='PROOF_CONTINUATION':
                assert enabled and z['nodes']==0;continuations+=1
            else:assert z['source']=='LEGAL_FALLBACK'
            state=apply_action(state,actions[z['action']],c);steps+=1
        assert actor_state(state)==tuple(row['end']) and terminal_result(state,c).status.value==row['terminal']
        proved_owners={step['actor'][-1] for step in row['trajectory'] if step['decision']['source']=='PROOF'}
        assert len(proved_owners)<=1, 'opposite forced-win certificates in one played game'
        if proved_owners:
            owner=next(iter(proved_owners));who='candidate' if owner==target else 'opponent'
            conversion[who+'_proved_games']+=1
            if state.terminal_status.is_terminal:
                assert state.terminal_status.winner==owner, 'proved strategy failed to execute to a win'
                conversion[who+'_physically_redeemed']+=1
            else:conversion[who+'_censored']+=1
        actual=None if not state.terminal_status.is_terminal else 0 if state.terminal_status.winner is None else 1 if state.terminal_status.winner==target else -1
        early_unknown+=incomplete(row,plan)
        assert actual==row['payoff'] and row['lower']==(-1 if actual is None else actual) and row['upper']==(1 if actual is None else actual)
    selection=json.loads((p/'selection.json').read_text()) if (p/'selection.json').exists() else None
    baseline=plan.get('baseline_index',0);selected=selection['selected_index'] if selection else 1
    if selection:
        assert not any(incomplete(r,plan) for r in rows if r['phase']=='TRAIN'), 'incomplete finite TRAIN objective cannot select prices'
        expected_train=2*len(roles(plan))*len(plan['opponents'])*sum(f['phase']=='TRAIN' for f in plan['families'])
        assert all(sum(r['phase']=='TRAIN' and r['price_index']==i for r in rows)==expected_train for i in range(len(plan['prices']))), 'missing TRAIN slots'
        scores={i:sum(r['payoff'] or 0 for r in rows if r['phase']=='TRAIN' and r['price_index']==i) for i in range(len(plan['prices']))}
        assert str(selection['integer_scores'])==str({str(k):v for k,v in scores.items()})
        assert selected==min(scores,key=lambda i:(-scores[i],plan['prices'][i]))
        assert [x['initial'] for x in selection['paths']]==plan['initial_prices']
        for path in selection['paths']:
            assert path['path'][0]==path['initial'] and path['path'][-1]==path['endpoint']
            for left,right in zip(path['path'],path['path'][1:]):
                different=[i for i in range(4) if left[i]!=right[i]]
                assert len(different)==1 and different[0] in plan.get('active_coordinates',[0,2])
                coord=different[0];levels=[360,720,1440]
                assert abs(levels.index(left[coord])-levels.index(right[coord]))==1
                assert scores[plan['prices'].index(right)]>scores[plan['prices'].index(left)]
    dev=[r for r in rows if families[r['family']]['phase']=='DEV'];groups={}
    for q,j,label in [(False,baseline,'A'),(True,baseline,'B'),(False,selected,'C'),(True,selected,'D')]:
        data=[r for r in dev if r['proof']==q and r['price_index']==j]
        groups[label]=dict(n=len(data),known_net=sum(r['payoff'] or 0 for r in data)/len(data) if data else None,
                           lower=sum(r['lower'] for r in data)/len(data) if data else None,
                           upper=sum(r['upper'] for r in data)/len(data) if data else None,
                           outcomes=dict(collections.Counter(str(r['payoff']) for r in data)))
    planned_n=2*len(roles(plan))*len(plan['opponents'])*sum(f['phase']=='DEV' for f in plan['families'])
    for label,(q,j) in dict(A=(False,baseline),B=(True,baseline),C=(False,selected),D=(True,selected)).items():
        data=[r for r in dev if r['proof']==q and r['price_index']==j]
        groups[label].update(planned_bounds(data,planned_n,plan))
    full_contrast=dict(finite_event_bounds=[groups['D']['planned_finite_event_bounds'][0]-groups['B']['planned_finite_event_bounds'][1],groups['D']['planned_finite_event_bounds'][1]-groups['B']['planned_finite_event_bounds'][0]],
                       infinite_outcome_bounds=[groups['D']['planned_infinite_outcome_bounds'][0]-groups['B']['planned_infinite_outcome_bounds'][1],groups['D']['planned_infinite_outcome_bounds'][1]-groups['B']['planned_infinite_outcome_bounds'][0]],
                       meaning='All frozen planned DEV cases; missing/early games remain uncertain. These are missing-data bounds, not sampling confidence intervals.')
    paired={};rng=random.Random(2026101554)
    for lhs,rhs,label in [('A','B','solver_unit'),('A','C','price_plain'),('B','D','price_with_solver')]:
        spec={'A':(False,baseline),'B':(True,baseline),'C':(False,selected),'D':(True,selected)}
        by={}
        for r in dev:by[r['family'],r['proof'],r['price_index'],r['color'],r['opponent'],row_role(r)]=r
        values=[];missing=[]
        for f in [f for f in plan['families'] if f['phase']=='DEV']:
            pairs=[]
            for color in (0,1):
                for op in plan['opponents']:
                    for role in roles(plan):
                        a=by.get((f['family'],*spec[lhs],color,op['id'],role));b=by.get((f['family'],*spec[rhs],color,op['id'],role))
                        if a is not None and b is not None:pairs.append((b['payoff'] or 0)-(a['payoff'] or 0))
            if len(pairs)==2*len(roles(plan))*len(plan['opponents']):values.append(sum(pairs)/len(pairs))
            else:missing.append(f['family'])
        if values:
            samples=[sum(rng.choice(values) for _ in values)/len(values) for _ in range(4000)]
            paired[label]=dict(observed_complete_families=len(values),missing_families=missing,
                               finite_event_difference=sum(values)/len(values),family_bootstrap95=[quantile(samples,.025),quantile(samples,.975)],
                               interpretation=('Horizon plus admitted existing-certificate physical completion W-L events; same policy both prices. Solver contrast includes tail policy.' if plan.get('certified_tail') else 'Fixed-horizon W-L event difference.')+' Not infinite WDL; incomplete capped prefixes descriptive only.')
    out=dict(status='PASS_PUBLIC_REPLAY_AND_RECEIPTS',games=len(rows),actual_steps=steps,matched_native_receipts=choice_index,
             native_receipts_total=len(choices),unassigned_native_receipts=len(choices)-choice_index,
             proof_calls=proofcalls,proof_continuations=continuations,native_node_overruns=overruns,step_time_overruns=over_time,max_step_seconds=max_time,early_unknown_before_H=early_unknown,
             cells_DEV_only=groups,contrasts=paired,selected_equals_baseline=selected==baseline,full_planned_B_to_D=full_contrast,seconds=time.perf_counter()-start,
             proof_conversion=dict(conversion),raw_games_sha256=hashlib.sha256((p/'run/games.jsonl').read_bytes()).hexdigest())
    (p/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))

if __name__=='__main__':
    import sys;audit(sys.argv[1])
