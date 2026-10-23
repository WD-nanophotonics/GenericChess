"""Exposed matched counterfactuals within PRIMARY's preexisting frozen families."""
from itertools import combinations
from copy import deepcopy
from collections import Counter,deque
from fractions import Fraction as F
from pathlib import Path
import json,time
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_design import state_sha,physical_action_key
from scripts.leaper_h6_e0 import graph
from scripts.research_record import record_value
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_from_dict
from scripts.leaper_cooperative_truth import cooperative_distances
from functools import lru_cache
from scripts.leaper_h6_initial_truth import Cap
from scripts.leaper_microgames import role_stop_requested


def physical_action(raw):
    return physical_action_key(action_from_dict(raw),{'K':'K','A':'A','B':'B'})


def analyze(directory):
    directory=Path(directory);inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz');rby={r['id']:r for r in truth['roots']};start=time.perf_counter();pairs=[]
    families=[f for f in inputs['families']if f['status']=='CLOSED']
    for left,right in combinations(families,2):
        delta=[a^b for a,b in zip(left['masks'],right['masks'],strict=True)]
        if sum(x.bit_count()for x in delta)!=1:continue
        changed_type='A'if delta[0]else'B'
        def dynamic(r):
            r=deepcopy(r);r.pop('initial_position');r.pop('initial_setup_options',None)
            for pc in r['piece_types']:
                if pc['type_id']==changed_type:pc['movement_atoms']=[]
            return r
        if dynamic(left['rule'])!=dynamic(right['rule']):raise ValueError('other dynamic rule field changed')
        li={tuple(r['placement']):r for r in inputs['rows']if r['family']==left['family']};ri={tuple(r['placement']):r for r in inputs['rows']if r['family']==right['family']}
        lc=admit(left,next(iter(li.values())));rc=admit(right,next(iter(ri.values())));rows=[];trans={k:Counter()for k in ('wdl','fork','cooperative')};action_trans=Counter()
        rightdomain=load(directory/f"domain{right['family']}.json.gz")
        from scripts.leaper_cooperative_certificate import decode_position
        rpositions=[decode_position(p,rc.initial_position)for p in rightdomain['positions']];rindices={p:i for i,p in enumerate(rpositions)}
        distances,_=cooperative_distances(rightdomain['edges'],{int(i)for i,w in rightdomain['terminals'].items()if w is not None})
        for placement in sorted(li.keys()&ri.keys()):
            l,r=li[placement],ri[placement];ls=GameSession.replay(lc,deserialize_game_record(json.dumps(l['full_record'])));rs=GameSession.replay(rc,deserialize_game_record(json.dumps(r['full_record'])))
            lp=record_value(ls.state.position);rp=record_value(rs.state.position);lp.pop('ruleset_fingerprint');rp.pop('ruleset_fingerprint')
            if lp!=rp or state_sha(ls.state)!=l['state_sha256']or state_sha(rs.state)!=r['state_sha256']or ls.state.ply_count or rs.state.ply_count:raise ValueError('not same legal fresh physical state')
            a,b=rby[l['state_sha256']],rby[r['state_sha256']]
            la={physical_action(x['action']):x['wdl_bounds'][0]for x in a['action_bounds']};ra={physical_action(x['action']):x['wdl_bounds'][0]for x in b['action_bounds']}
            oldbest={k for k,v in la.items()if v==a['wdl_bounds'][0]};newbest={k for k,v in ra.items()if v==b['wdl_bounds'][0]}
            unchanged=set(la)&set(ra)
            for action in unchanged:action_trans[str((la[action],ra[action]))]+=1
            trans['wdl'][str((a['wdl_bounds'][0],b['wdl_bounds'][0]))]+=1
            trans['fork'][str((a['wdl_fork'],b['wdl_fork']))]+=1
            trans['cooperative'][str((a['cooperative_decisive'],b['cooperative_decisive']))]+=1
            escapes=[]
            if a['wdl_bounds']!=b['wdl_bounds']:
                for rawaction in b['action_bounds']:
                    key=physical_action(rawaction['action'])
                    if key in newbest and key not in la:
                        child=GameSession.replay(rc,rs.to_record());child.submit(action_from_dict(rawaction['action']))
                        before=sum(pc is not None for pc in rs.state.position.board);after=sum(pc is not None for pc in child.state.position.board)
                        escapes.append(dict(action=rawaction['action'],child_record=record_value(child.to_record()),child_state_sha=state_sha(child.state),
                            captured=before-after,remaining_ordinary=[(pc.owner,pc.current_type_id)for pc in child.state.position.board if pc and pc.current_type_id!='K'],
                            closed_no_decisive_path=rindices[child.state.position]not in distances))
            rows.append(dict(placement=placement,left_id=a['id'],right_id=b['id'],left_record=l['full_record'],right_record=r['full_record'],
                left_WDL=a['wdl_bounds'][0],right_WDL=b['wdl_bounds'][0],left_fork=a['wdl_fork'],right_fork=b['wdl_fork'],
                left_cooperative=a['cooperative_decisive'],right_cooperative=b['cooperative_decisive'],
                common_actions=len(unchanged),added_actions=len(set(ra)-set(la)),removed_actions=len(set(la)-set(ra)),
                common_action_WDL_changes=sum(la[k]!=ra[k]for k in unchanged),best_set_changed=oldbest!=newbest,new_best_escapes=escapes))
        pairs.append(dict(left_family=left['family'],right_family=right['family'],left_masks=left['masks'],right_masks=right['masks'],
            left_fingerprint=left['fingerprint'],right_fingerprint=right['fingerprint'],
            delta_bits=delta,left_total=len(li),right_total=len(ri),common_roots=len(rows),
            left_only=[list(x)for x in sorted(li.keys()-ri.keys())],right_only=[list(x)for x in sorted(ri.keys()-li.keys())],
            common_mu_id=digest(sorted([list(x)for x in li.keys()&ri.keys()])),
            geometry_left=[graph(m)for m in left['masks']],geometry_right=[graph(m)for m in right['masks']],
            transitions={k:dict(v)for k,v in trans.items()},common_action_WDL_transitions=dict(action_trans),
            best_set_changed=sum(r['best_set_changed']for r in rows),rows=rows))
    return dict(format='leaper-H6-existing-adjacent-counterfactual-v1',truth_digest=digest(truth),pairs=pairs,seconds=time.perf_counter()-start,
        scope='All onebitadjacencies among already frozen ordered A/Bfamilies, not newrule/pair sampling or blindprediction. Uniform common admitted labelledfreshplacements. Fullfingerprints/records/setupkeys remain distinct; physicaltype/coordinates mapped explicitly. Not wholefamilyunequalmu or generic monotonicity/strength claim.')


def couple_uniform_prefixes(directory,adjacency,plan):
    """A fixed one-step maximal coupling, stopped at its first divergence.

    The two marginals choose uniformly among their own actual legal actions.
    At a still common prefix each common physical action has joint mass
    min(1/m,1/n). This maximizes agreement at THIS decision, not over complete
    trajectories. No continuation after divergence, policy games or new graph.
    """
    tick=time.perf_counter();directory=Path(directory);source=load(directory/'inputs.json.gz')
    truth=load(directory/'truth.json.gz');rootmap={r['id']:r for r in truth['roots']}
    if plan['clock']!=6 or plan['repetition']!=2:raise ValueError('coupling scope requires H6/repeat2')
    pairs=[];wholecalls=0
    def guard():
        if role_stop_requested():raise Cap('USER_STOP')
        if time.perf_counter()-tick>=plan['whole_cap_seconds']:raise Cap('COUPLING_TIME_CAP_UNKNOWN')
        if wholecalls>=plan['history_context_cap']:raise Cap('COUPLING_CONTEXT_CAP_UNKNOWN')
    for pair in adjacency['pairs']:
        domains=[load(directory/f"domain{pair[k]}.json.gz")for k in('left_family','right_family')]
        # Domain encoding contains side and board, with the same admitted K/A/B
        # type/owner code. Fingerprints remain separate in all actual records.
        indices=[{digest(p):i for i,p in enumerate(d['positions'])}for d in domains]
        keysets=[set(m)for m in indices];common=sorted(set.intersection(*keysets));commonidx={k:i for i,k in enumerate(common)}
        edge_maps=[];term_maps=[]
        static_counts=Counter()
        for d,ix in zip(domains,indices,strict=True):
            em={};tm={}
            for key in common:
                i=ix[key]
                em[key]={physical_action(a):digest(d['positions'][j])for a,j in zip(d['actions'][i],d['edges'][i],strict=True)}
                if str(i)in d['terminals']:tm[key]=d['terminals'][str(i)]
            edge_maps.append(em);term_maps.append(tm)
        for key in common:
            l,r=[em[key]for em in edge_maps]
            for a in set(l)&set(r):
                if l[a]!=r[a]or l[a]not in commonidx:raise ValueError('common edge is not physically corresponding')
            for a in set(r)-set(l):static_counts['added_'+a[0]]+=1
            for a in set(l)-set(r):static_counts['removed_'+a[0]]+=1
            static_counts['terminal_authority_changed']+=((key in term_maps[0],term_maps[0].get(key))!=(key in term_maps[1],term_maps[1].get(key)))
        # Indexed vectors: first different action at0..5, first terminal
        # mismatch at0..6, and matching terminal at0..6; all are disjoint.
        zero=(F(0),)*20
        seen_keys=set()
        def terminal(key,remaining,visited,k):
            if key in term_maps[k]:
                winner=term_maps[k][key]
                return ('checkmate'if winner is not None else'stalemate',winner)
            if commonidx[key]in visited:return ('repetition',None)
            if remaining==0:return ('max_ply',None)
            return None
        @lru_cache(maxsize=plan['memo_entries'])
        def visit(key,remaining,visited):
            nonlocal wholecalls
            guard();wholecalls+=1;seen_keys.add(key);ply=6-remaining
            lt,rt=[terminal(key,remaining,visited,k)for k in(0,1)]
            out=list(zero)
            if lt is not None or rt is not None:
                out[(13 if lt==rt else 6)+ply]=F(1)
                return tuple(out)
            la,ra=[em[key]for em in edge_maps];m,n=len(la),len(ra)
            shared=sorted(set(la)&set(ra));den=max(m,n)
            if not m or not n:raise ValueError('ongoing context has no action')
            out[ply]=F(den-len(shared),den)
            seen=tuple(sorted((*visited,commonidx[key])))
            for a in shared:
                ch=visit(la[a],remaining-1,seen)
                for k in range(20):out[k]+=ch[k]/den
            if sum(out)!=1:raise ValueError('coupling mass lost')
            return tuple(out)
        rows=[]
        for root in pair['rows']:
            guard();ll=rootmap[root['left_id']];rr=rootmap[root['right_id']]
            lk=digest(domains[0]['positions'][ll['root_index']]);rk=digest(domains[1]['positions'][rr['root_index']])
            if lk!=rk:raise ValueError('initial physical roots differ')
            law=visit(lk,6,())
            rows.append(dict(left_id=root['left_id'],right_id=root['right_id'],placement=root['placement'],
                first_action_divergence_ply_mass=list(map(str,law[:6])),
                first_terminal_mismatch_ply_mass=list(map(str,law[6:13])),
                matching_terminal_ply_mass=list(map(str,law[13:])),
                matching_complete_history_probability=str(sum(law[13:]))))
        n=len(rows);mean=lambda name:[str(sum(F(r[name][k])for r in rows)/n)for k in range(len(rows[0][name]))]
        pairs.append(dict(left_family=pair['left_family'],right_family=pair['right_family'],common_mu_id=pair['common_mu_id'],
            common_physical_vertices=len(common),left_physical_vertices=len(keysets[0]),right_physical_vertices=len(keysets[1]),
            static_common_domain_difference=dict(static_counts),visited_common_vertices=len(seen_keys),
            first_action_divergence_ply_mass=mean('first_action_divergence_ply_mass'),
            first_terminal_mismatch_ply_mass=mean('first_terminal_mismatch_ply_mass'),
            matching_terminal_ply_mass=mean('matching_terminal_ply_mass'),
            matching_complete_history_probability=str(sum(F(r['matching_complete_history_probability'])for r in rows)/n),
            rows=rows,memo=visit.cache_info()._asdict()))
    return dict(format='leaper-H6-uniform-common-prefix-coupling-v1',adjacency_digest=digest(adjacency),
        source_digest=digest(source),truth_digest=digest(truth),plan=plan,pairs=pairs,
        history_contexts=wholecalls,seconds=time.perf_counter()-tick,
        scope='ExactFraction law for specified recursive one-step maximal coupling on128existing commonfreshroots. Fullvisitedsets/clock retained for repeat2. Conditional sameprefix coverage is not globaloptimal coupling, gameequivalence, learnedtransfer, policybenefit or independentrule sampling. Static domain counts are separately labelled, not history occupation.')


def decompose_uniform_gain(directory,adjacency,coupling,plan):
    """Attribute payoff difference at the first physical/terminal divergence.

    For this observed pair, each newly enabled A action either captures the
    last B or moves after B is already absent. Removed King actions and new
    stalemates occur only after B is absent. Both saved closed no-B domains
    have no winning terminals, so all these continuations give payoff0.
    At a B-capture divergence the right payoff is0; the left residual uniform
    marginal has expected payoff V_left of the still-common context. Thus its
    contribution is -V_left/max(m,n), weighted by common-prefix reach mass.
    No prices, learner interventions or actual Player outcomes are inferred.
    """
    tick=time.perf_counter();directory=Path(directory);inputs=load(directory/'inputs.json.gz')
    truth=load(directory/'truth.json.gz');occup={r['id']:r for r in load(directory/'occupation.json.gz')['rows']}
    rootmap={r['id']:r for r in truth['roots']};whole=0;output=[]
    if coupling['adjacency_digest']!=digest(adjacency):raise ValueError('coupling source mismatch')
    def guard():
        nonlocal whole
        whole+=1
        if whole>plan['history_context_cap']or time.perf_counter()-tick>=plan['whole_cap_seconds']:raise Cap('GAIN_DECOMPOSITION_CAP_UNKNOWN')
        if whole%64==0 and role_stop_requested():raise Cap('USER_STOP')
    for pair in adjacency['pairs']:
        ds=[load(directory/f"domain{pair[k]}.json.gz")for k in('left_family','right_family')]
        maps=[];terms=[];position_maps=[];bare_counts=[]
        for d in ds:
            pmap={digest(p):p for p in d['positions']};position_maps.append(pmap)
            em={digest(p):{physical_action(a):digest(d['positions'][j])for a,j in zip(d['actions'][i],d['edges'][i],strict=True)}for i,p in enumerate(d['positions'])}
            tm={digest(d['positions'][int(i)]):w for i,w in d['terminals'].items()}
            bare={k for k,p in pmap.items()if '6'not in p[1]}
            if any(w==0 for w in tm.values()):raise ValueError('seat0 win makes the nonpositive-risk argument unavailable')
            if any(j not in bare for k in bare for j in em[k].values())or any(tm[k]is not None for k in bare&tm.keys()):raise ValueError('no-B domain is not closed universal draw')
            maps.append(em);terms.append(tm);bare_counts.append(len(bare))
        @lru_cache(maxsize=plan['memo_entries'])
        def risk(key,remaining,visited):
            guard()
            if key in terms[0]:return F(-1 if terms[0][key]==1 else 0)
            if not remaining or key in visited:return F(0)
            children=list(maps[0][key].values());seen=tuple(sorted((*visited,key)))
            return sum((risk(j,remaining-1,seen)for j in children),F(0))/len(children)
        @lru_cache(maxsize=plan['memo_entries'])
        def effect(key,remaining,visited):
            guard();out=[F(0)]*12;ply=6-remaining
            lterm=key in terms[0]or not remaining or key in visited
            rterm=key in terms[1]or not remaining or key in visited
            if lterm or rterm:
                if lterm!=rterm and '6'in position_maps[0][key][1]:raise ValueError('new terminal with B is outside attribution theorem')
                return tuple(out)
            l,r=[em[key]for em in maps];added=set(r)-set(l);removed=set(l)-set(r);hasB='6'in position_maps[0][key][1]
            den=max(len(l),len(r));seen=tuple(sorted((*visited,key)))
            if added:
                if removed or len(added)!=1 or len(r)!=len(l)+1 or any(a[0]!='A'for a in added):raise ValueError('not one additional A action')
                if hasB:
                    if any('6'in position_maps[1][r[a]][1]for a in added):raise ValueError('new A action does not capture last B')
                    out[ply]=F(1,den)
                    out[6+ply]=-risk(key,remaining,visited)/den
            if removed and hasB:raise ValueError('removed action with B is outside attribution theorem')
            for a in set(l)&set(r):
                if l[a]!=r[a]:raise ValueError('common successor differs')
                ch=effect(l[a],remaining-1,seen)
                for k in range(12):out[k]+=ch[k]/den
            return tuple(out)
        rows=[]
        for r in pair['rows']:
            key=digest(ds[0]['positions'][rootmap[r['left_id']]['root_index']]);v=effect(key,6,())
            left,right=[occup[r[k]]for k in('left_id','right_id')]
            utility=lambda row:F(row['uniform_terminal_LDW'][2])-F(row['uniform_terminal_LDW'][0])
            gain=utility(right)-utility(left)
            if gain!=sum(v[6:])or any(x<0 for x in v):raise ValueError('first-divergence effects do not reproduce original exact occupation gain')
            rows.append(dict(left_id=r['left_id'],right_id=r['right_id'],placement=r['placement'],
                first_capture_divergence_ply_mass=list(map(str,v[:6])),gain_by_first_divergence_ply=list(map(str,v[6:])),
                uniform_utility_gain=str(gain),minimax_WDL_change=r['right_WDL']-r['left_WDL']))
        n=len(rows);capture=sum(sum(map(F,r['first_capture_divergence_ply_mass']))for r in rows)/n
        gain=sum(F(r['uniform_utility_gain'])for r in rows)/n
        output.append(dict(left_family=pair['left_family'],right_family=pair['right_family'],common_mu_id=pair['common_mu_id'],
            closed_no_B_vertices=bare_counts,first_capture_divergence_probability=str(capture),uniform_utility_gain=str(gain),
            old_uniform_loss_probability_given_capture_divergence=str(gain/capture),
            gain_by_first_divergence_ply=[str(sum(F(r['gain_by_first_divergence_ply'][k])for r in rows)/n)for k in range(6)],
            payoff_change_from_removed_K_or_terminal_mismatch='0',
            root_gain_signs=dict(Counter('positive'if F(r['uniform_utility_gain'])>0 else'negative'if F(r['uniform_utility_gain'])<0 else'zero'for r in rows)),rows=rows))
    return dict(format='leaper-H6-uniform-payoff-mechanism-v1',adjacency_digest=digest(adjacency),coupling_digest=digest(coupling),
        source_digest=digest(inputs),truth_digest=digest(truth),plan=plan,pairs=output,history_calls=whole,
        seconds=time.perf_counter()-tick,scope='Exact first-divergence decomposition of same128uniform-policy outcomes, with closed no-B zero-payoff theorem and old-history conditional risk. Finite retrospective known pair, not learnedpolicy/search benefit, causal intervention on a fixed rule, newindependent tests or a general material price.')


def paired_coordinates(directory,adjacency):
    """Separate physical size, complete-history count, mu shifts and forecasts."""
    directory=Path(directory);inputs=load(directory/'inputs.json.gz')
    truth={r['id']:r for r in load(directory/'truth.json.gz')['roots']}
    occupation={r['id']:r for r in load(directory/'occupation.json.gz')['rows']}
    forecasts=load(directory/'forecasts.json.gz');out=[]
    for pair in adjacency['pairs']:
        trees=[]
        for family,key in[(pair['left_family'],'left_id'),(pair['right_family'],'right_id')]:
            d=load(directory/f'domain{family}.json.gz');terms={int(i):w for i,w in d['terminals'].items()}
            @lru_cache(maxsize=100000)
            def count(i,remaining,prior):
                if i in terms or not remaining or i in prior:
                    status='checkmate'if i in terms and terms[i]is not None else'stalemate'if i in terms else'repetition'if i in prior else'max_ply'
                    return (1,0,(1,)+(0,)*remaining,((status,1),))
                seen=tuple(sorted((*prior,i)));children=[count(j,remaining-1,seen)for j in d['edges'][i]];cc=Counter()
                for ch in children:cc.update(dict(ch[3]))
                return(1+sum(ch[0]for ch in children),len(children)+sum(ch[1]for ch in children),
                    (1,)+tuple(sum(ch[2][k]for ch in children)for k in range(remaining)),tuple(sorted(cc.items())))
            total=Counter();layers=[0]*7
            reachable={truth[root[key]]['root_index']for root in pair['rows']};pending=deque(reachable)
            while pending:
                for j in d['edges'][pending.popleft()]:
                    if j not in reachable:reachable.add(j);pending.append(j)
            for root in pair['rows']:
                v=count(truth[root[key]]['root_index'],6,());total['contexts']+=v[0];total['edges']+=v[1]
                total.update(dict(v[3]));layers=[a+b for a,b in zip(layers,v[2],strict=True)]
            trees.append(dict(family=family,physical_vertices=len(d['positions']),physical_edges=sum(map(len,d['edges'])),
                common_mu_closed_vertices=len(reachable),common_mu_closed_edges=sum(len(d['edges'][i])for i in reachable),
                common_mu_roots=len(pair['rows']),complete_history_counts=dict(total),history_layer_counts=layers))
        left_all=[r['state_sha256']for r in inputs['rows']if r['family']==pair['left_family']]
        left_common=[r['left_id']for r in pair['rows']];right_common=[r['right_id']for r in pair['rows']]
        if set(right_common)!={r['state_sha256']for r in inputs['rows']if r['family']==pair['right_family']}:raise ValueError('mu decomposition requires no right-only roots')
        metrics={
            'minimax_U0':lambda h:F(truth[h]['wdl_bounds'][0]),
            'initial_fork':lambda h:F(truth[h]['wdl_fork']),
            'cooperative':lambda h:F(truth[h]['cooperative_decisive']),
            'uniform_U0':lambda h:F(occupation[h]['uniform_terminal_LDW'][2])-F(occupation[h]['uniform_terminal_LDW'][0]),
            'expected_uniform_decisions':lambda h:F(occupation[h]['expected_decisions'])}
        mu={}
        for label,fn in metrics.items():
            mean=lambda ids:sum(map(fn,ids))/len(ids)
            la,lc,rc=map(mean,(left_all,left_common,right_common))
            mu[label]=dict(old_full=str(la),old_common=str(lc),new_common_and_full=str(rc),
                common_mu_rule_difference=str(rc-lc),old_mu_selection_difference=str(lc-la),different_mu_total_difference=str(rc-la))
        contrast=[]
        for name,forecast in forecasts['history_forecasts'].items():
            by={r['id']:r for r in forecast['predictions']};deltas=[];observed=[]
            for row in pair['rows']:
                a,b=[by[row[k]]for k in('left_id','right_id')]
                if a['property']!=b['property']:raise ValueError('forecast property differs')
                prop=a['property'];deltas.append(F(str(b['probability']))-F(str(a['probability'])))
                observed.append(F(truth[row['right_id']][prop])-F(truth[row['left_id']][prop]))
            n=len(deltas);delta=sum(deltas)/n;target=sum(observed)/n
            contrast.append(dict(method=name,property=prop,predicted_common_mu_change=str(delta),actual_common_mu_change=str(target),
                nonzero_predicted_root_changes=sum(d!=0 for d in deltas),nonzero_actual_root_changes=sum(d!=0 for d in observed),
                mean_squared_root_contrast_error=str(sum((a-b)**2 for a,b in zip(deltas,observed,strict=True))/n),
                squared_mean_rate_contrast_error=str((delta-target)**2)))
        out.append(dict(left_family=pair['left_family'],right_family=pair['right_family'],common_mu_id=pair['common_mu_id'],
            trees=trees,mu_decomposition=mu,actual_frozen_forecast_contrasts=contrast,
            source_only_placements=pair['left_only']))
    return dict(format='leaper-H6-pair-distinct-coordinates-v1',adjacency_digest=digest(adjacency),pairs=out,
        forecast_execution_sha=forecasts['execution_sha'],scope='History counts and common_mu_closed counts use the same128roots. Stored physical_vertices/edges came from respective full admitted families and include32old-only closure vertices. Mu shifts are separate. Unpruned history counts are not measured search work. Forecast contrasts are exposed retrospective diagnostics,not a preregistered headline,refit or new heldout experiment.')


if __name__=='__main__':
    import argparse
    cli=argparse.ArgumentParser();cli.add_argument('--directory',required=True);cli.add_argument('--output',required=True);cli.add_argument('--coupling-plan');cli.add_argument('--adjacency');a=cli.parse_args()
    r=couple_uniform_prefixes(a.directory,load(a.adjacency),load(a.coupling_plan)) if a.coupling_plan else analyze(a.directory);save(a.output,r)
    print(json.dumps({**r,'pairs':[{k:v for k,v in q.items()if k!='rows'}for q in r['pairs']]}))
