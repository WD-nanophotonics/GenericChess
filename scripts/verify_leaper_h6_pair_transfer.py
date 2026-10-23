"""Direct complete-GameSession control of cross-rule common-prefix probability.

Uses no compact domain edges or visited-set memo: propagates exact probability
mass over literal paired Session paths until the first action/terminal mismatch.
This is a finite analytical policy control, not sampled forward Player games.
"""
from copy import copy
from pathlib import Path
from fractions import Fraction as F
from collections import Counter,deque
from functools import lru_cache
import argparse,json,time,hashlib
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_h6_pair_certificates import physical_actions,physical_position,repetition_partition
from scripts.leaper_microgames import role_stop_requested
from scripts.leaper_design import state_sha
from scripts.research_record import record_value
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from generic_chess.core.transition import legal_successors
from scripts.leaper_retrograde import fresh_state
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_h6_adjacent_pairs import physical_action
from scripts.leaper_h6_initial_truth import blocked_clock_attractor
from generic_chess.core.identity import repetition_identity_key
from math import isclose


def verify_pair_order(directory,adjacency):
    """Check a scoped finite-history value preorder through actual Core edges.

    Seat0 maximizes its WDL. On the common domain, old seat0 choices are a
    subset of new choices; new seat1 choices are a subset of old choices.
    A common choice has the identical physical successor. Static terminals
    agree except new DRAW replacing old ongoing; the complete old domain has
    no seat0-win terminal, so its value can never exceed DRAW. Equal-prefix
    repeat2 and remaining-clock draws preserve the inequality by induction.
    This certificate is a paired relation, NOT a Position-only scalar label.
    """
    tick=time.perf_counter();directory=Path(directory);source=load(directory/'inputs.json.gz');summary=load(directory/'summary.json')
    counts=Counter();pairs=[]
    for pair in adjacency['pairs']:
        domains=[];indices=[];terms=[];maps=[]
        for tag in('left_family','right_family'):
            family=next(f for f in source['families']if f['family']==pair[tag])
            first=next(r for r in source['rows']if r['family']==pair[tag]);c=admit(family,first)
            d=load(directory/f"domain{pair[tag]}.json.gz")
            receipt=next(f for f in summary['families']if f['family']==pair[tag])
            if digest(d)!=receipt['domain_digest']:raise ValueError('domain provenance differs')
            positions=[decode_position(p,c.initial_position)for p in d['positions']];ix={p:i for i,p in enumerate(positions)}
            if len(ix)!=len(positions):raise ValueError('duplicate domain position')
            for i,pos in enumerate(positions):
                if counts['Core_vertices']%64==0 and role_stop_requested():raise RuntimeError('USER_STOP')
                s=fresh_state(pos,c);counts['Core_vertices']+=1
                if s.terminal_status.is_terminal:
                    if str(i)not in d['terminals']or d['terminals'][str(i)]!=s.terminal_status.winner or d['edges'][i]or d['actions'][i]:raise ValueError('static terminal differs')
                else:
                    actual=list(legal_successors(s,c));counts['Core_edges']+=len(actual)
                    if any(ch.position not in ix for a,ch in actual):raise ValueError('domain not closed')
                    if str(i)in d['terminals']or [ix[ch.position]for a,ch in actual]!=d['edges'][i]or[action_to_dict(a)for a,ch in actual]!=d['actions'][i]:raise ValueError('domain actual Core edges differ')
            domains.append(d);indices.append({digest(p):i for i,p in enumerate(d['positions'])})
            terms.append({digest(d['positions'][int(i)]):w for i,w in d['terminals'].items()})
            maps.append({digest(p):{physical_action(a):digest(d['positions'][j])for a,j in zip(d['actions'][i],d['edges'][i],strict=True)}for i,p in enumerate(d['positions'])})
        if any(w==0 for w in terms[0].values()):raise ValueError('old domain has seat0 winning terminal; draw bound unavailable')
        left,right=maps
        if not set(right)<=set(left):raise ValueError('target not physically contained in source domain')
        changed_terminal=0;added=Counter();removed=Counter()
        for key in right:
            li,ri=[ix[key]for ix in indices];side=domains[0]['positions'][li][0]
            if domains[1]['positions'][ri][0]!=side:raise ValueError('turn differs')
            lt=(key in terms[0],terms[0].get(key));rt=(key in terms[1],terms[1].get(key))
            if lt!=rt:
                if lt[0]or rt!=(True,None):raise ValueError('terminal difference does not preserve value ordering')
                changed_terminal+=1
            if lt[0]or rt[0]:continue
            l,r=left[key],right[key]
            if side==0 and not set(l)<=set(r):raise ValueError('new rule removes maximizing-seat choice')
            if side==1 and not set(r)<=set(l):raise ValueError('new rule adds minimizing-seat choice')
            for a in set(l)&set(r):
                if l[a]!=r[a]:raise ValueError('common choice successor differs')
            for a in set(r)-set(l):added[a[0]]+=1
            for a in set(l)-set(r):removed[a[0]]+=1
        pairs.append(dict(left_family=pair['left_family'],right_family=pair['right_family'],
            source_domain_digest=digest(domains[0]),target_domain_digest=digest(domains[1]),
            common_physical_vertices=len(right),old_domain_has_no_seat0_winning_terminal=True,
            order='new seat0 WDL >= old seat0 WDL',same_physical_prefix_required=True,
            scope_clock=6,scope_repetition=2,changed_terminal_to_draw=changed_terminal,
            ongoing_added_actions=dict(added),ongoing_removed_actions=dict(removed),
            theorem='Backward induction in remaining plies, with same ordered physical prehistory/repetition equality partition; preserve both full rule identities. Closed-domain terminal upper bound0 justifies ongoing->DRAW. Not a scalar label copied across rules, unbounded-clock equivalence or a general capability monotonicity theorem.'))
    return dict(verified=True,adjacency_digest=digest(adjacency),counts=dict(counts),pairs=pairs,seconds=time.perf_counter()-tick)


def verify_fresh_rank(directory,plan):
    """All supplied roots/actions, using the existing rank attractor instead
    of the compact remaining-clock/full-visited-set recurrence.
    """
    tick=time.perf_counter();directory=Path(directory);inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz')
    by={r['id']:r for r in truth['roots']};counts=Counter();families=[]
    for f in inputs['families']:
        if f['status']=='MU_UNAVAILABLE':continue
        began=time.perf_counter();source=[r for r in inputs['rows']if r['family']==f['family']];c=admit(f,source[0])
        d=load(directory/f"domain{f['family']}.json.gz");positions=[decode_position(p,c.initial_position)for p in d['positions']]
        terms={int(i):w for i,w in d['terminals'].items()};sides=[p.side_to_move for p in positions]
        for sr in source:
            if role_stop_requested():raise RuntimeError('USER_STOP')
            if (time.perf_counter()-tick>=plan['whole_cap_seconds']or time.perf_counter()-began>=plan['family_cap_seconds']or
                counts['attractor_calls']>=plan['attractor_calls_cap']):raise RuntimeError('BLOCKED_CLOCK_CHECK_CAP_UNKNOWN')
            row=by[sr['state_sha256']];s=GameSession.replay(c,deserialize_game_record(json.dumps(sr['full_record'])))
            if state_sha(s.state)!=row['id']or len(s.state.history)!=1 or s.state.ply_count!=0:raise ValueError('rank root not bound to fresh history')
            i=row['root_index'];value,*_=blocked_clock_attractor(d['edges'],terms,sides,{i});counts['attractor_calls']+=1
            if [value(i,6)]*2!=row['wdl_bounds']:raise ValueError('blocked rank root disagrees')
            for j,b in zip(d['edges'][i],row['action_bounds'],strict=True):
                if [value(j,5,arriving=True)]*2!=b['wdl_bounds']:raise ValueError('blocked rank action disagrees')
                counts['actions']+=1
            counts['roots']+=1
        families.append(dict(family=f['family'],roots=len(source),seconds=time.perf_counter()-began))
    return dict(verified=True,plan=plan,counts=dict(counts),families=families,source_digest=digest(inputs),truth_digest=digest(truth),
        seconds=time.perf_counter()-tick,scope='All3616frozen H6repeat2 roots/actions match existing fullGameState-verified truth through prefix-blocked existingattractor plus finiteclock threshold. No newgraph,Player,training or generalhistory quotient; retrospective alternative,not blinded forecast.')


def verify_history_counterexamples(directory,receipt):
    """Literal short suffixes of actual equal-Position/equal-clock histories."""
    from scripts.leaper_microgames import ExactTree
    directory=Path(directory);inputs=load(directory/'inputs.json.gz');results=[]
    for family in receipt['families']:
        f=next(f for f in inputs['families']if f['family']==family['family']);source=next(r for r in inputs['rows']if r['family']==f['family']);c=admit(f,source)
        for pair in family['same_Position_clock_counterexample']:
            sessions=[];values=[];count=0
            for side in('left','right'):
                row=pair[side];s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
                if state_sha(s.state)!=row['state_sha']or s.result.status.value!='ongoing':raise ValueError('counterexample source history differs')
                tree=ExactTree(c,max_states=1000,seconds=10);v=tree.solve(s.state);count+=len(tree.values)
                if v!=row['value']or c.max_ply-s.state.ply_count!=row['remaining']:raise ValueError('counterexample literal value differs')
                sessions.append(s);values.append(v)
            left,right=sessions
            if left.state.position!=right.state.position or left.state.ply_count!=right.state.ply_count or values[0]==values[1]:raise ValueError('not same Position/clock with different history WDL')
            current=repetition_identity_key(left.state.position,c)
            if dict(left.state.repetition_counts)[current]!=dict(right.state.repetition_counts)[current]:raise ValueError('current occurrence count differs')
            la,ra=map(physical_actions,sessions)
            if la.keys()!=ra.keys():raise ValueError('current action legality differs')
            terminal_differences=[]
            for a in sorted(la):
                ll=copy(left);rr=copy(right);ll.submit(la[a]);rr.submit(ra[a])
                if ll.result!=rr.result:terminal_differences.append(dict(action=list(a),left=ll.result.status.value,right=rr.result.status.value))
            if not terminal_differences:raise ValueError('no literal repetition consequence')
            results.append(dict(family=f['family'],values=values,ply=left.state.ply_count,current_occurrences=dict(left.state.repetition_counts)[current],
                literal_contexts=count,terminal_differences=terminal_differences))
    return dict(verified=True,cases=results,scope='Two actual histories per existingrule, same current physical Position,ply,current-count andlegal action set; prehistory andWDL differ. Counts are correlated diagnostics,not independent rule experiments.')


def verify_depth_receipts(worlds,truth,inputs,results,*,support='proof'):
    """Verify retained decisions/PVs/labels. NEVER rerun a closed query batch."""
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,SessionChoice,MATE
    from scripts.leaper_single_parity_truth import admit as admit_single,bare_opponent_bound
    selected=[s for s in truth['certificate_decisions']if s['actor']==0 and s['fork']and not s['immediate_win']]
    if inputs['source_truth_digest']!=digest(truth)or inputs['rows']!=selected or inputs['selection_digest']!=digest([s['id']for s in selected]):raise ValueError('depth diagnostic selection differs')
    by={s['id']:s for s in selected};plan=inputs['plan']
    expected={(s['id'],d)for s in selected for d in plan['depths']}
    actual=[(r['id'],r['requested_depth'])for r in results['rows']]
    if len(actual)!=len(set(actual))or set(actual)!=expected or results['missing']!=0:raise ValueError('depth receipt support differs')
    nodes=0;pv_edges=0;bad_controls=[];summaries=[];nonzero_free_PV_gradients=0
    for row in results['rows']:
        root=by[row['id']];world=next(w for w in worlds if w['world']==root['world']);_,c,_=admit_single(world['rule'],require_parity=False)
        s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
        if state_sha(s.state)!=row['id']:raise ValueError('depth root history mismatch')
        env=FixedScaleSessionEnv(s,unit_type='A');model=Model(row['weights']);receipt=row['receipt'];nodes+=receipt['nodes']
        nonzero_free_PV_gradients+=int(not receipt['pv_terminal']and any(model.gradient(receipt['pv_phi'])))
        if record_value(env.names)!=row['names']or row['weights']!=[1.]*len(env.names):raise ValueError('unit material differs')
        if receipt['nodes']>plan['query_nodes']or receipt['seconds']>plan['query_seconds']+.25:raise ValueError('query exceeded declared budget')
        action=receipt['action']
        if not action or action['kind']!='ACTION':raise ValueError('expected completed board action')
        candidates=[a for a in s.legal_actions()if record_value(a)==action['action']]
        if len(candidates)!=1:raise ValueError('retained chosen public action not legal/unique')
        chosen=candidates[0];branch=next(b for b in root['actions']if b['action']==action_to_dict(chosen))
        if row['chosen_WDL']!=branch['wdl']or row['optimal']!=(branch['wdl']==root['value']):raise ValueError('depth exact action score differs')
        if row['requested_complete']!=bool(receipt['complete']and receipt['completed_depth']==row['requested_depth']):raise ValueError('shallower result relabelled')
        if not receipt['pv_choices']or receipt['pv_choices'][0]!=action:raise ValueError('chosen action not first PV edge')
        for raw in receipt['pv_choices']:
            if raw['kind']!='ACTION':raise ValueError('out-of-scope PV declaration')
            legal=[a for a in env.session.legal_actions()if record_value(a)==raw['action']]
            if len(legal)!=1:raise ValueError('literal PV action mismatch')
            env.push(SessionChoice('ACTION',action=legal[0]));pv_edges+=1
        terminal=env.terminal()
        if receipt['pv_terminal']:
            if terminal is None or receipt['value']!=MATE*terminal:raise ValueError('terminal PV value mismatch')
        else:
            if terminal is not None or list(env.features())!=receipt['pv_phi']or not isclose(model.raw(env.features()),receipt['value'],abs_tol=1e-10):raise ValueError('material PV value mismatch')
        if row['optimal']is False:
            bad=copy(s);bad.submit(chosen);captures=[]
            for a in bad.legal_actions():
                ch=copy(bad);ch.submit(a)
                if not any(pc and pc.current_type_id=='A'for pc in ch.state.position.board):
                    capture=dict(action=action_to_dict(a),record=record_value(ch.to_record()),state_sha=state_sha(ch.state))
                    if support=='onset':
                        if bare_opponent_bound(ch.state.position)!=[0,0]:raise ValueError('capture did not enter bare-King draw domain')
                        capture['all_continuations_draw_bound']=[0,0]
                        capture['actual_status']=ch.result.status.value
                    captures.append(capture)
            bad_controls.append(dict(id=row['id'],depth=row['requested_depth'],chosen_action=action_to_dict(chosen),
                immediate_capture_A_draw_replies=captures))
    for depth in plan['depths']:
        rows=[r for r in results['rows']if r['requested_depth']==depth]
        summaries.append(dict(depth=depth,queries=len(rows),requested_complete=sum(r['requested_complete']for r in rows),
            known_actions=sum(r['chosen_WDL']is not None for r in rows),inferior=sum(r['optimal']is False for r in rows),
            UNKNOWN=sum(r['chosen_WDL']is None for r in rows),nodes=sum(r['receipt']['nodes']for r in rows),
            seconds=sum(r['receipt']['seconds']for r in rows)))
    if summaries!=results['by_depth']or nodes!=results['nodes']or nodes>plan['whole_node_cap']:raise ValueError('depth aggregate differs')
    critical=selected
    floor=sum(F(sum(a['wdl']<r['value']for a in r['actions']),len(r['actions']))for r in critical)/len(critical)
    if support in('first_fork','onset'):
        return dict(verified=True,queries=len(actual),contexts=len(selected),nodes=nodes,literal_PV_edges=pv_edges,
            nonzero_free_PV_gradients=nonzero_free_PV_gradients,
            uniform_legal_lowering_probability=str(floor),bad_choice_capture_controls=bad_controls,
            scope=(f'Retained{len(actual)}actualmainline one-decision receipts at{len(selected)}nominal-D2unsafe firstforkhistories, all disjoint from the closed teacher batch. 'if support=='first_fork'else
                f'Retained{len(actual)}D1/D2receipts cover ALL{len(selected)}firstforkhistories throughply4, including32explicitlyreused queries and356newqueries. ')+
                'AllpublicPV replayed and joined to actual full-history action truth. Uniformprefixarrival is separate from uniformweighting over these correlatedcontexts. No newPlayerquery,training ordefaultchange bythisreader.')
    if support!='proof':raise ValueError('unknown depth support')
    return dict(verified=True,queries=len(actual),nodes=nodes,literal_PV_edges=pv_edges,
        FLOOR_lowering_probability_under_uniform_12_proof_contexts=str(floor),bad_choice_capture_controls=bad_controls,
        scope='Retained36actualmainline one-decision receipts at12teacher-selected correlatedprefixes; allpublic PVs replayed andjoined to exacttruth. Conditional FLOOR probability isnotnaturaloccupation orpolicystrength. No newPlayerquery,training ordefaultchange bythisreader.')


def shallow_material_mechanisms(worlds,truth,results,*,max_edges=5000):
    """Post-hoc literal 1/2-ply material sets; no new Player call or fitting."""
    from scripts.leaper_single_parity_truth import admit as admit_single
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
    tick=time.perf_counter();source={r['id']:r for r in truth['certificate_decisions']};groups={}
    for row in results['rows']:groups.setdefault(row['id'],{})[row['requested_depth']]=row
    counts=Counter();rows=[]
    def evaluate(session):
        env=FixedScaleSessionEnv(session,unit_type='A');terminal=env.terminal()
        return MATE*terminal if terminal is not None else Model([1.]*len(env.names)).raw(env.features())
    for hid,receipts in groups.items():
        root=source[hid];w=next(w for w in worlds if w['world']==root['world']);_,c,_=admit_single(w['rule'],require_parity=False)
        s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
        if s.state.position.side_to_move!=0:raise ValueError('diagnostic root is not maximizing seat')
        actions=[]
        for action in s.legal_actions():
            child=copy(s);child.submit(action);counts['Core_edges']+=1;one=evaluate(child);two=one
            if child.result.status.value=='ongoing':
                replies=[]
                for reply in child.legal_actions():
                    cc=copy(child);cc.submit(reply);counts['Core_edges']+=1;replies.append(evaluate(cc))
                two=min(replies)
            if counts['Core_edges']>max_edges or time.perf_counter()-tick>30:raise RuntimeError('SHALLOW_MATERIAL_CONTROL_CAP_UNKNOWN')
            raw=action_to_dict(action);label=next(b['wdl']for b in root['actions']if b['action']==raw)
            actions.append(dict(action=raw,exact_WDL=label,nominal_D1_material=one,nominal_D2_material=two))
        best={d:max(a[f'nominal_D{d}_material']for a in actions)for d in(1,2)}
        selected={}
        for depth in(1,2):
            raw=receipts[depth]['receipt']['action']['action']
            action=next(a for a in s.legal_actions()if record_value(a)==raw)
            row=next(a for a in actions if a['action']==action_to_dict(action));selected[str(depth)]=row
            if row[f'nominal_D{depth}_material']!=best[depth]:raise ValueError('actual shallow choice outside nominal material maximizers')
        rows.append(dict(id=hid,actions=actions,D1_maximizers=sum(a['nominal_D1_material']==best[1]for a in actions),
            D1_maximizers_with_inferior_WDL=sum(a['nominal_D1_material']==best[1]and a['exact_WDL']<1 for a in actions),
            D2_maximizers=sum(a['nominal_D2_material']==best[2]for a in actions),
            D2_maximizers_with_inferior_WDL=sum(a['nominal_D2_material']==best[2]and a['exact_WDL']<1 for a in actions),actual_choices=selected))
    return dict(verified=True,counts=dict(counts),rows=rows,seconds=time.perf_counter()-tick,
        scope='Post-hoc literal nominal1/2ply material maximizer sets on same12teacherselected histories; no additionalPlayercalls,depthgrid,training,policygames orclaimthatnominalplyalwaysmatchesallmainlineextensions. ActualchosenD1/D2actions liein respective materialmaximizers.')


def material_feature_support(certificate,worlds):
    """Actual learner channels on the certified domain; no training or labels."""
    from scripts.leaper_single_parity_truth import admit as admit_single
    from scripts.leaper_clock_rebinding import expand
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,_material_features
    _,c,_=admit_single(certificate['target_rule'],require_parity=False)
    env=FixedScaleSessionEnv(GameSession(c),unit_type='A');model=Model([1.]*len(env.names))
    counts=Counter();nonzero=[False]*len(env.names)
    for raw in certificate['positions']:
        position=expand(raw,c.initial_position);phi=_material_features(position,c,env.names)
        counts[str(tuple(phi))]+=1
        for i,v in enumerate(phi):nonzero[i]|=v!=0
    active=[record_value(name)for i,name in enumerate(env.names)if i!=model.fixed and nonzero[i]]
    return dict(channels=record_value(env.names),fixed_index=model.fixed,domain_positions=len(certificate['positions']),
        observed_feature_counts=dict(counts),active_trainable_material_channels=active,
        scope='Exactfeature support on supplied3952Position closure,not a trainingdataset orWDLfit. OneordinarytypeA withfixedscale andremove/nohands leaves noactivefree materialparameter. Search/positional learning and multi-type rosters are different questions; no claimthat absence ofafreeparameter makessearchtrivial.')


def comment_scope_review():
    """Independent arithmetic check of one received mathematical claim."""
    from scripts.leaper_design import offsets
    single={m:len({(x+y)%2 for x,y in offsets(m)})==1 for m in range(1,32)}
    edges=[(a,b)for a in range(1,32)for b in range(a+1,32)if (a^b).bit_count()==1]
    counts=Counter('both_single'if single[a]and single[b]else'boundary'if single[a]!=single[b]else'both_mixed'for a,b in edges)
    return dict(comment_ts='1792766992.946839',single_parity_masks=[m for m,v in single.items()if v],edge_classes=dict(counts),
        scope='Independent arithmetic review of the existing encoding, not a rule producer or new game campaign. The single-parity theorem certifies 11 both-single edges; 23 boundary edges have an UNKNOWN mixed side; 41 mixed-to-mixed edges are not certified unchanged by that theorem. Mixedness does not guarantee mate. Proposed campaign cost is not measured cost.')


def verify_pair_policy_laws(directory,adjacency,laws,plan):
    """All512 root-mode laws through direct literal path-mass propagation."""
    from scripts.leaper_microgames import ExactTree
    import gc
    directory=Path(directory);inputs=load(directory/'inputs.json.gz');source={r['state_sha256']:r for r in inputs['rows']}
    by={(r['id'],r['opponent']):r for r in laws['rows']};tick=time.perf_counter();cases=[];contexts=0
    for pair in adjacency['pairs']:
        for family,key in[(pair['left_family'],'left_id'),(pair['right_family'],'right_id')]:
            f=next(f for f in inputs['families']if f['family']==family);c=admit(f,source[pair['rows'][0][key]])
            tree=ExactTree(c,max_states=plan['literal_contexts_per_family'],seconds=plan['family_cap_seconds']);roots=[]
            for root in pair['rows']:
                if role_stop_requested()or time.perf_counter()-tick>=plan['whole_cap_seconds']:raise RuntimeError('PAIR_POLICY_LITERAL_CAP_UNKNOWN')
                s=GameSession.replay(c,deserialize_game_record(json.dumps(source[root[key]]['full_record'])));tree.solve(s.state);roots.append((root[key],s.state))
            for opponent in('UNIFORM','FLOOR'):
                for hid,initial in roots:
                    counts=Counter();terminal=[F(0)]*3;firstfork=[F(0)]*6;firstloss=[F(0)]*6
                    def walk(state,mass,sawfork=False,sawloss=False):
                        children=tree.edges[state]
                        if not children:
                            winner=state.terminal_status.winner;value=0 if winner is None else 1 if winner==0 else-1;terminal[value+1]+=mass;return
                        counts['expected_decisions']+=mass;fork=len({tree.values[ch]for a,ch in children})>1
                        if fork:
                            counts['expected_fork_visits']+=mass
                            if not sawfork:firstfork[state.ply_count]+=mass
                        winning=[(a,ch)for a,ch in children if ch.terminal_status.is_terminal and ch.terminal_status.winner==state.position.side_to_move]
                        selected=winning[:1]if opponent=='FLOOR'and state.position.side_to_move==1 and winning else children
                        for a,ch in selected:
                            m=mass/len(selected);bad=tree.values[ch]!=tree.values[state]
                            if bad:
                                counts['expected_guarantee_lowering_decisions']+=m
                                if not sawloss:firstloss[state.ply_count]+=m
                            walk(ch,m,sawfork or fork,sawloss or bad)
                    walk(initial,F(1));r=by[hid,opponent]
                    if list(map(F,r['uniform_terminal_LDW']))!=terminal or list(map(F,r['first_fork_ply_mass']))!=firstfork or list(map(F,r['first_lowering_ply_mass']))!=firstloss:raise ValueError('literal policy law mismatch')
                    if any(F(r[k])!=counts[k]for k in('expected_decisions','expected_fork_visits','expected_guarantee_lowering_decisions')):raise ValueError('literal policy occupation mismatch')
                    cases.append((hid,opponent))
            contexts+=len(tree.values);del tree;gc.collect()
    return dict(verified=True,law_digest=digest(laws),cases=len(cases),full_history_contexts=contexts,seconds=time.perf_counter()-tick,
        scope='All128commonroots inbothrules andbothopponentpolicies,fullGameState ExactTree plus direct rationalmass traversal. No compact policy recurrence inthiscontrol,newPlayercall,PRNGgame,training orrule sampling.')


def verify_prefix_ranks(directory,adjacency,plan):
    """Slow complete-GameState minimax control, including every action."""
    from scripts.leaper_microgames import ExactTree
    import gc
    directory=Path(directory);inputs=load(directory/'inputs.json.gz');by={r['state_sha256']:r for r in inputs['rows']}
    tick=time.perf_counter();total=Counter();families=[]
    for pair in adjacency['pairs']:
        for family,key in[(pair['left_family'],'left_id'),(pair['right_family'],'right_id')]:
            began=time.perf_counter();f=next(f for f in inputs['families']if f['family']==family)
            rows=[by[r[key]]for r in pair['rows']];c=admit(f,rows[0]);d=load(directory/f'domain{family}.json.gz')
            positions=[decode_position(p,c.initial_position)for p in d['positions']];indices={pos:i for i,pos in enumerate(positions)}
            keys={repetition_identity_key(pos,c):i for i,pos in enumerate(positions)}
            sides=[pos.side_to_move for pos in positions];terms={int(i):w for i,w in d['terminals'].items()}
            tree=ExactTree(c,max_states=plan['literal_contexts_per_family'],seconds=plan['family_cap_seconds']);rootkeys={}
            def guard():
                if role_stop_requested():raise RuntimeError('USER_STOP')
                if (time.perf_counter()-tick>=plan['whole_cap_seconds']or time.perf_counter()-began>=plan['family_cap_seconds']or
                    total['attractor_calls']>=plan['attractor_calls_cap']):raise RuntimeError('PREFIX_CLOCK_CAP_UNKNOWN')
            for row in rows:
                guard();s=GameSession.replay(c,deserialize_game_record(json.dumps(row['full_record'])))
                rootkeys[s.state.history[0].position_key]=row;tree.solve(s.state)
            literal_seconds=time.perf_counter()-began;counts=Counter();collisions=[];grouped={}
            @lru_cache(maxsize=32)
            def reducer(blocked):
                total['attractor_calls']+=1
                return blocked_clock_attractor(d['edges'],terms,sides,set(blocked))[0]
            def replay(state):
                row=rootkeys[state.history[0].position_key];s=GameSession.replay(c,deserialize_game_record(json.dumps(row['full_record'])))
                for a in tree.paths[state]:s.submit(a)
                if s.state!=state:raise ValueError('literal saved path binding mismatch')
                return dict(record=record_value(s.to_record()),state_sha=state_sha(state),value=tree.values[state],
                    remaining=6-state.ply_count,repetition_counts=record_value(state.repetition_counts))
            for state,actual in tree.values.items():
                counts['contexts']+=1
                if state.terminal_status.is_terminal:continue
                if counts['contexts']%64==0:guard()
                blocked=tuple(sorted(keys[k]for k,n in state.repetition_counts if n>=1));value=reducer(blocked)
                i=indices[state.position];remaining=6-state.ply_count
                if value(i,remaining)!=actual:raise ValueError('prefix WDL mismatch')
                for a,ch in tree.edges[state]:
                    if value(indices[ch.position],remaining-1,arriving=True)!=tree.values[ch]:raise ValueError('prefix action WDL mismatch')
                    counts['actions']+=1
                counts['ongoing_contexts']+=1
                label=(state.position,state.ply_count)
                if label in grouped:
                    old=grouped[label]
                    if tree.values[old]!=actual:
                        counts['different_history_WDL_pairs']+=1
                        if not collisions:collisions.append(dict(left=replay(old),right=replay(state)))
                else:grouped[label]=state
            families.append(dict(family=family,counts=dict(counts),same_Position_clock_counterexample=collisions,
                literal_tree_seconds=literal_seconds,total_seconds=time.perf_counter()-began,cache=reducer.cache_info()._asdict()))
            total.update(counts);del tree,positions,grouped;reducer.cache_clear();gc.collect()
    return dict(verified=True,plan=plan,source_digest=digest(inputs),families=families,total=dict(total),seconds=time.perf_counter()-tick,
        scope='ALLactualorderedfullGameState continuations ofsame128commonroots perrule. ExactTree actualCore minimax versus existingprefix-blockedattractor/rank+remainingclock; compareongoing matchedPosition/ply only. No scalarPosition transfer,Player,training,newrule orstart selection.')


def verify_literal(directory,adjacency,coupling,plan,gain=None):
    tick=time.perf_counter();directory=Path(directory);inputs=load(directory/'inputs.json.gz')
    sources={r['state_sha256']:r for r in inputs['rows']};families={f['family']:f for f in inputs['families']}
    if coupling['adjacency_digest']!=digest(adjacency):raise ValueError('coupling source mismatch')
    cases=[];counts=Counter();witnesses={};risk_cache={}
    gainby={r['left_id']:r for p in gain['pairs']for r in p['rows']}if gain is not None else None
    occupation={r['id']:r for r in load(directory/'occupation.json.gz')['rows']}if gain is not None else None
    def literal_risk(s):
        # Full authoritative GameState including ordered history is the key.
        # This scope has no Session-only claims/resignation or hidden state.
        if s.state in risk_cache:return risk_cache[s.state]
        counts['full_history_risk_contexts']+=1
        if (counts['full_history_risk_contexts']>plan.get('literal_risk_context_cap',0)or
            time.perf_counter()-tick>=plan['whole_cap_seconds']):raise RuntimeError('LITERAL_RISK_CAP_UNKNOWN')
        if counts['full_history_risk_contexts']%256==0 and role_stop_requested():raise RuntimeError('USER_STOP')
        if s.result.status.value!='ongoing':
            value=F(0 if s.result.winner is None else 1 if s.result.winner==0 else-1)
        else:
            actions=s.legal_actions();value=F(0)
            for a in actions:
                ch=copy(s);ch.submit(a);counts['full_history_risk_transitions']+=1
                value+=literal_risk(ch)/len(actions)
        risk_cache[s.state]=value
        return value
    def literal_risk_child(s,a):
        child=copy(s);child.submit(a)
        return literal_risk(child)
    for pair,law in zip(adjacency['pairs'],coupling['pairs'],strict=True):
        configs=[admit(families[pair[k]],next(r for r in inputs['rows']if r['family']==pair[k]))for k in('left_family','right_family')]
        predicted={r['left_id']:r for r in law['rows']}
        for root in pair['rows']:
            if role_stop_requested():raise RuntimeError('USER_STOP')
            masses={k:[F(0)]*n for k,n in [('first_action_divergence_ply_mass',6),('first_terminal_mismatch_ply_mass',7),('matching_terminal_ply_mass',7)]}
            initial=[GameSession.replay(c,deserialize_game_record(json.dumps(sources[root[k]]['full_record'])))for c,k in zip(configs,('left_id','right_id'))]
            if [state_sha(s.state)for s in initial]!=[root['left_id'],root['right_id']]:raise ValueError('literal roots differ')
            gain_mass=[F(0)]*6;capture_mass=[F(0)]*6
            if gain is not None:
                initial_utilities=list(map(literal_risk,initial))
                for name,u in zip(('left_id','right_id'),initial_utilities):
                    o=occupation[root[name]]
                    if u!=F(o['uniform_terminal_LDW'][2])-F(o['uniform_terminal_LDW'][0]):raise ValueError('literal root uniform utility differs')
            queue=deque([(*initial,F(1),[])])
            while queue:
                ls,rs,mass,prefix=queue.pop();counts['full_session_pair_contexts']+=1
                if (time.perf_counter()-tick>=plan['whole_cap_seconds']or
                    counts['full_session_pair_contexts']>plan['literal_pair_context_cap']):raise RuntimeError('LITERAL_COUPLING_CAP_UNKNOWN')
                if counts['full_session_pair_contexts']%256==0 and role_stop_requested():raise RuntimeError('USER_STOP')
                if physical_position(ls.state.position)!=physical_position(rs.state.position):raise ValueError('literal physical prefixes differ')
                if repetition_partition(ls)!=repetition_partition(rs)or ls.state.ply_count!=rs.state.ply_count:raise ValueError('literal history/clock correspondence fails')
                ply=ls.state.ply_count;terminal=[s.result.status.value!='ongoing'for s in(ls,rs)]
                if any(terminal):
                    name='matching_terminal_ply_mass'if ls.result==rs.result else'first_terminal_mismatch_ply_mass'
                    masses[name][ply]+=mass
                    if gain is not None and ls.result!=rs.result and literal_risk(ls)!=literal_risk(rs):raise ValueError('terminal mismatch carries nonzero payoff effect')
                    if name=='first_terminal_mismatch_ply_mass':
                        key=('terminal',ls.result.status.value,rs.result.status.value)
                        witnesses.setdefault(str(key),dict(left_root_id=root['left_id'],right_root_id=root['right_id'],prefix=prefix,
                            left_record=record_value(ls.to_record()),right_record=record_value(rs.to_record()),
                            left_result=record_value(ls.result),right_result=record_value(rs.result),
                            left_state_sha=state_sha(ls.state),right_state_sha=state_sha(rs.state)))
                    continue
                la,ra=physical_actions(ls),physical_actions(rs);common=set(la)&set(ra);den=max(len(la),len(ra))
                masses['first_action_divergence_ply_mass'][ply]+=mass*F(den-len(common),den)
                for side,only in [('left',set(la)-set(ra)),('right',set(ra)-set(la))]:
                    for a in sorted(only):
                        key=('legal_action',side,a[0])
                        witnesses.setdefault(str(key),dict(left_root_id=root['left_id'],right_root_id=root['right_id'],prefix=prefix,
                            left_record=record_value(ls.to_record()),right_record=record_value(rs.to_record()),
                            left_state_sha=state_sha(ls.state),right_state_sha=state_sha(rs.state),
                            differing_action=action_to_dict((la if side=='left'else ra)[a])))
                if gain is not None:
                    residual_right=sum((literal_risk_child(rs,a)*(F(1,len(ra))-(F(1,den)if k in common else 0))for k,a in ra.items()),F(0))
                    residual_left=sum((literal_risk_child(ls,a)*(F(1,len(la))-(F(1,den)if k in common else 0))for k,a in la.items()),F(0))
                    # Independently evaluate the two entire residual marginals,
                    # rather than assuming their zero-payoff mechanism.
                    gain_mass[ply]+=mass*(residual_right-residual_left)
                    if set(ra)-set(la) and any(pc and pc.owner==1 and pc.current_type_id=='B'for pc in ls.state.position.board):
                        capture_mass[ply]+=mass*F(den-len(common),den)
                for a in sorted(common):
                    ll=copy(ls);rr=copy(rs);ll.submit(la[a]);rr.submit(ra[a]);counts['public_session_transitions']+=2
                    queue.append((ll,rr,mass/den,prefix+[list(a)]))
            expected=predicted[root['left_id']]
            if any(list(map(F,expected[k]))!=v for k,v in masses.items()):raise ValueError('literal path-mass law disagrees with compact coupling')
            if sum(sum(v)for v in masses.values())!=1:raise ValueError('literal mass is incomplete')
            if gain is not None:
                g=gainby[root['left_id']]
                if gain_mass!=list(map(F,g['gain_by_first_divergence_ply']))or capture_mass!=list(map(F,g['first_capture_divergence_ply_mass'])):raise ValueError('literal risk contributions differ')
                if sum(gain_mass)!=initial_utilities[1]-initial_utilities[0]:raise ValueError('literal gain telescoping fails')
            cases.append(dict(left_id=root['left_id'],right_id=root['right_id']))
    return dict(verified=True,coupling_digest=digest(coupling),adjacency_digest=digest(adjacency),cases=cases,
        counts=dict(counts),first_literal_witness_by_mechanism=witnesses,gain_digest=digest(gain)if gain is not None else None,seconds=time.perf_counter()-tick,
        scope='ALL128existing commonroots, direct paired fullGameSession paths and Fraction mass. No graph/compact repetition evaluator; eachside actuallegal actions,terminal precedence,fullhistory authoritative. SharedCore is not an independent engine; exact coupling law is not policy strength/learned transfer.')


def stable(value):
    """Only recomputation timing differs; caps, labels and costs stay bound."""
    if isinstance(value,dict):return {k:stable(v)for k,v in value.items()if k not in('seconds','generation_seconds','literal_tree_seconds','total_seconds')}
    if isinstance(value,list):return [stable(v)for v in value]
    return value


def verify_material_escape_receipts(control, directory):
    """Literally validate saved price/depth diagnostics, never rerun Players."""
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,SessionChoice,MATE
    directory=Path(directory);inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz')
    adjacency=load(directory/'adjacent-pairs.json.gz');pair=adjacency['pairs'][0];plan=control['plan']
    ids=[r['right_id']for r in pair['rows']if r['new_best_escapes']]
    if plan['selected_ids']!=ids or len(ids)!=16 or plan['ratios']!=[.5,1.,2.]or plan['depths']!=[1,2]:
        raise ValueError('material control selection differs')
    if plan['source_inputs_digest']!=digest(inputs)or plan['source_truth_digest']!=digest(truth):
        raise ValueError('material source digest differs')
    expected={(hid,q,d)for hid in ids for q in plan['ratios']for d in plan['depths']}
    actual=[(r['id'],r['ratio'],r['depth'])for r in control['rows']]
    if len(actual)!=len(set(actual))or set(actual)!=expected:raise ValueError('missing or duplicate material receipt')
    source=next(r for r in inputs['rows']if r['family']==pair['right_family'])
    family=next(f for f in inputs['families']if f['family']==pair['right_family']);c=admit(family,source)
    roots={r['id']:r for r in truth['roots']};nominal={};counts=Counter();chosen={}
    def evaluate(session,model):
        env=FixedScaleSessionEnv(session,unit_type='A');terminal=env.terminal()
        return MATE*terminal if terminal is not None else model.raw(env.features())
    for row in control['nominal']:
        hid,q=row['id'],row['ratio'];key=(hid,q)
        if key in nominal or hid not in ids or q not in plan['ratios']:raise ValueError('invalid nominal support')
        root=roots[hid];s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
        env=FixedScaleSessionEnv(s,unit_type='A');weights=[q if name==('board','B')else 1. for name in env.names]
        if row['names']!=record_value(env.names)or row['weights']!=weights:raise ValueError('actual active B weight differs')
        model=Model(weights);actions=[]
        for action in s.legal_actions():
            child=copy(s);child.submit(action);counts['nominal_Core_edges']+=1
            one=evaluate(child,model);two=one
            if child.result.status.value=='ongoing':
                replies=[]
                for reply in child.legal_actions():
                    cc=copy(child);cc.submit(reply);counts['nominal_Core_edges']+=1;replies.append(evaluate(cc,model))
                two=min(replies)
            raw=action_to_dict(action);labels=[v['wdl_bounds']for v in root['action_bounds']if v['action']==raw]
            if len(labels)!=1 or labels[0][0]!=labels[0][1]:raise ValueError('missing exact H6 action label')
            actions.append(dict(action=raw,D1=one,D2=two,exact_WDL=labels[0][0],immediate_terminal=child.result.status.value))
        if row['actions']!=actions:raise ValueError('literal nominal frontier differs')
        nominal[key]=actions
    if set(nominal)!={(hid,q)for hid in ids for q in plan['ratios']}:raise ValueError('nominal matrix incomplete')
    for row in control['rows']:
        hid,q,depth=row['id'],row['ratio'],row['depth'];root=roots[hid]
        s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
        env=FixedScaleSessionEnv(s,unit_type='A');model=Model(row['weights']);receipt=row['receipt']
        counts['nonzero_root_free_gradients']+=int(any(model.gradient(env.features())))
        pv_gradient=(0.,)*len(model.weights)if receipt['pv_terminal']else model.gradient(receipt['pv_phi'])
        counts['nonzero_PV_free_gradients']+=int(any(pv_gradient))
        if row['names']!=record_value(env.names)or row['weights']!=[q if n==('board','B')else 1. for n in env.names]:
            raise ValueError('receipt weights differ')
        if receipt['nodes']>plan['query_nodes']or receipt['seconds']>plan['query_seconds']+.25:
            raise ValueError('material query allowance exceeded')
        actions=nominal[hid,q];best=max(a[f'D{depth}']for a in actions);maxima=[a for a in actions if a[f'D{depth}']==best]
        raw=receipt['action']
        if raw is None or raw['kind']!='ACTION':raise ValueError('material receipt has no completed action')
        ac=[a for a in s.legal_actions()if record_value(a)==raw['action']]
        if len(ac)!=1:raise ValueError('saved material choice not legal')
        picked=next(a for a in actions if a['action']==action_to_dict(ac[0]))
        if (row['chosen_WDL']!=picked['exact_WDL']or row['chosen_nominal']!=picked[f'D{depth}']or
            picked[f'D{depth}']!=best or row['nominal_best']!=best or row['nominal_maximizers']!=len(maxima)or
            row['nominal_inferior_maximizers']!=sum(a['exact_WDL']<0 for a in maxima)or
            row['uniform_tie_error']!=str(F(sum(a['exact_WDL']<0 for a in maxima),len(maxima)))):
            raise ValueError('material maximizer/quality annotation differs')
        if row['requested_complete']!=bool(receipt['complete']and receipt['completed_depth']==depth):
            raise ValueError('shallower material result relabelled')
        if not receipt['pv_choices']or receipt['pv_choices'][0]!=raw:raise ValueError('material PV root differs')
        for step in receipt['pv_choices']:
            aa=[a for a in env.session.legal_actions()if record_value(a)==step['action']]
            if step['kind']!='ACTION'or len(aa)!=1:raise ValueError('material PV illegal')
            env.push(SessionChoice('ACTION',action=aa[0]));counts['literal_PV_edges']+=1
        terminal=env.terminal()
        if receipt['pv_terminal']:
            if terminal is None or receipt['value']!=MATE*terminal:raise ValueError('material PV terminal differs')
        elif terminal is not None or list(env.features())!=receipt['pv_phi']or not isclose(model.raw(env.features()),receipt['value'],abs_tol=1e-10):
            raise ValueError('material PV feature/value differs')
        counts['queries']+=1;counts['nodes']+=receipt['nodes']
        chosen.setdefault(hid,set()).add(digest(action_to_dict(ac[0])))
    if counts['nodes']!=control['counts']['nodes']or counts['queries']!=96:raise ValueError('material cost differs')
    return dict(verified=True,counts=dict(counts),same_action_across_all_six_settings=sum(len(v)==1 for v in chosen.values()),
        inferior=sum(r['chosen_WDL']<0 for r in control['rows']),
        scope='Saved96mainlinequeries at16exposed existingdirectescapes, completeD1/D2 underthreepositiveBweights. AllliteralPVandnominaledges checked, no newPlayercalls. PositiveBsign is enough here. All96PV gradients arezero although rootBfeatures areactive; this is localnewgradient only, not a denial of earliereligibilitytrace credit. Not pricelearning or policystrength evidence.')


def first_fork_nominal_material(certificate, worlds, prefix, *, seconds=60,max_edges=50000):
    """Nominal unit-material ties under an explicit first-fork arrival law.

    Uniform policies supply the incoming prefix distribution. At the first
    fork only, uniformly select a nominal D1/D2 material maximizer and score
    its true action WDL. This switched diagnostic is not an actual Player or
    a strength test. No oracle-selected experiential starts or fitting occur.
    """
    from dataclasses import replace
    from scripts.leaper_single_parity_truth import admit as admit_single
    from scripts.leaper_clock_rebinding import expand
    from scripts.leaper_retrograde import attractor
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
    tick=time.perf_counter();_,c,_=admit_single(certificate['target_rule'],require_parity=False)
    ps=[expand(p,c.initial_position)for p in certificate['positions']];ix={p:i for i,p in enumerate(ps)}
    edges=[];terms={};counts=Counter();compiled={};results=[]
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if counts['Core_edges']>max_edges or time.perf_counter()-tick>=seconds:raise RuntimeError('FIRST_FORK_MATERIAL_CAP_UNKNOWN')
    for i,p in enumerate(ps):
        guard();s=fresh_state(p,c)
        if s.terminal_status.is_terminal:
            w=s.terminal_status.winner;terms[i]=0 if w is None else 1 if w==p.side_to_move else-1;edges.append(())
        else:
            cs=legal_successors(s,c);counts['Core_edges']+=len(cs)
            if any(ch.position not in ix for _,ch in cs):raise ValueError('nominal source graph not closed')
            edges.append(tuple(ix[ch.position]for _,ch in cs))
    values,ranks=attractor(edges,terms)
    for worldlaw in prefix['rows']:
        world=next(w for w in worlds if w['world']==worldlaw['world'])
        _,tc,_=admit_single(world['rule'],require_parity=False);compiled[world['world']]=tc
        rows=[]
        for item in worldlaw['details']:
            if not item['fork']:continue
            guard();s=GameSession.replay(tc,deserialize_game_record(json.dumps(item['record'])))
            if state_sha(s.state)!=item['id']or s.state.position.side_to_move!=0 or s.state.ply_count>4:
                raise ValueError('first fork context not matched')
            if any(n>=3 for _,n in s.state.repetition_counts):raise ValueError('prefix beyond count-safe scope')
            env=FixedScaleSessionEnv(s,unit_type='A');model=Model([1.]*len(env.names))
            def evaluate(state):
                ee=FixedScaleSessionEnv(state,unit_type='A');terminal=ee.terminal()
                return MATE*terminal if terminal is not None else model.raw(ee.features())
            actions=[]
            for action in s.legal_actions():
                child=copy(s);child.submit(action);counts['Core_edges']+=1;one=evaluate(child);two=one
                if child.result.status.value!='ongoing':
                    label=0 if child.result.winner is None else 1 if child.result.winner==0 else-1
                else:
                    j=ix[replace(child.state.position,ruleset_fingerprint=c.ruleset_fingerprint)]
                    rel=values[j]if values[j]and ranks[j]<=tc.max_ply-child.state.ply_count else 0
                    label=rel if ps[j].side_to_move==0 else-rel
                    replies=[]
                    for reply in child.legal_actions():
                        cc=copy(child);cc.submit(reply);counts['Core_edges']+=1;replies.append(evaluate(cc))
                    two=min(replies)
                actions.append(dict(action=action_to_dict(action),WDL=label,D1=one,D2=two,
                    immediate_win=child.result.status.value!='ongoing'and child.result.winner==0))
            if [a['WDL']for a in actions]!=item['action_WDL']:raise ValueError('first fork action truth differs')
            best_WDL=max(a['WDL']for a in actions);analysis=[]
            for depth in(1,2):
                best=max(a[f'D{depth}']for a in actions);maxima=[a for a in actions if a[f'D{depth}']==best]
                bad=sum(a['WDL']<best_WDL for a in maxima)
                analysis.append(dict(depth=depth,maximizers=len(maxima),inferior=bad,uniform_tie_error=str(F(bad,len(maxima))),
                    forced_error=bad==len(maxima),unsafe_tie=0<bad<len(maxima)))
            rows.append(dict(id=item['id'],ply=item['ply'],probability=item['probability'],immediate_win=any(a['immediate_win']for a in actions),
                actions=actions,depths=analysis))
        summary=[];mass=sum(F(r['probability'])for r in rows)
        for depth in(1,2):
            for group in('all','non_immediate'):
                chosen=[r for r in rows if group=='all'or not r['immediate_win']]
                group_mass=sum(F(r['probability'])for r in chosen)
                err=sum(F(r['probability'])*F(r['depths'][depth-1]['uniform_tie_error'])for r in chosen)
                summary.append(dict(depth=depth,group=group,contexts=len(chosen),arrival_mass=str(group_mass),
                    nominal_error_mass=str(err),conditional_uniform_tie_error=str(err/group_mass)if group_mass else None,
                    forced_error_mass=str(sum(F(r['probability'])for r in chosen if r['depths'][depth-1]['forced_error'])),
                    unsafe_tie_mass=str(sum(F(r['probability'])for r in chosen if r['depths'][depth-1]['unsafe_tie']))))
        if mass!=sum(map(F,worldlaw['first_fork_by_ply'])):raise ValueError('first fork mass differs')
        results.append(dict(world=world['world'],summary=summary,rows=rows))
    return dict(domain_digest=digest(certificate),prefix_digest=digest(prefix),rows=results,counts=dict(counts),seconds=time.perf_counter()-tick,
        scope='Nominal literal1/2ply unitmaterial on ALLfirstfork histories throughply4 reached byindependentuniformprefixlaw; uniformtiebreak only atthatfirstfork. Not actualmainlinechoices, fullpolicygames, learningbenefit orindependentheldout. Current oneordinarytype hasnoactive free materialparameter.')


def verify_supplied_rotation(certificate,worlds,prefix,nominal,queries,*,seconds=60):
    """Bind the two supplied setups by R(x,y)=(3-y,x), including history.

    Complete local dynamics plus the bijective full-prefix equality partition
    support the scoped pure-Leaper game isomorphism. This is not a transform
    admission rule for arbitrary effects, promotions, declarations or DSLs.
    """
    from dataclasses import replace
    from scripts.leaper_single_parity_truth import admit as admit_single
    from scripts.leaper_clock_rebinding import expand
    tick=time.perf_counter();source=next(w for w in worlds if w['world']==24);target=next(w for w in worlds if w['world']==26)
    sr,tr=source['rule'],target['rule'];_,sc,_=admit_single(sr,require_parity=False);_,tc,_=admit_single(tr,require_parity=False)
    if {k:v for k,v in sr.items()if k!='initial_position'}!={k:v for k,v in tr.items()if k!='initial_position'}:
        raise ValueError('rotation changes more than supplied setup')
    for piece in sr['piece_types']:
        offsets={tuple(a['offset'])for a in piece['movement_atoms']}
        if offsets!={(-y,x)for x,y in offsets}:raise ValueError('moves not quarter-turn invariant')
    def point(p):return (3-p[1],p[0])
    def position(p,fp):
        board=[None]*16
        for i,pc in enumerate(p.board):
            x,y=point((i%4,i//4));board[y*4+x]=pc
        return replace(p,board=tuple(board),ruleset_fingerprint=fp)
    if position(sc.initial_position,tc.ruleset_fingerprint)!=tc.initial_position:
        raise ValueError('supplied root setup not related by quarter-turn')
    ps=[expand(p,sc.initial_position)for p in certificate['positions']];ix={p:i for i,p in enumerate(ps)}
    def key(raw,rotate=False):
        a=raw.get('from',raw.get('from_square'));b=raw.get('to',raw.get('to_square'))
        if isinstance(a,dict):a=(a['file'],a['rank']);b=(b['file'],b['rank'])
        a,b=tuple(a),tuple(b)
        if rotate:a,b=point(a),point(b)
        return raw['actor_type_id'],a,b,raw.get('promotion_target_id')
    rotation={i:ix.get(position(p,sc.ruleset_fingerprint))for i,p in enumerate(ps)}
    if None in rotation.values()or len(set(rotation.values()))!=len(ps):raise ValueError('supplied domain not rotation closed')
    counts=Counter()
    for i,p in enumerate(ps):
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('ROTATION_REVIEW_CAP_UNKNOWN')
        left=fresh_state(p,sc);right=fresh_state(position(p,tc.ruleset_fingerprint),tc)
        if left.terminal_status!=right.terminal_status:raise ValueError('rotated terminal authority differs')
        ll=legal_successors(left,sc)if not left.terminal_status.is_terminal else()
        rr=legal_successors(right,tc)if not right.terminal_status.is_terminal else()
        expected={key(action_to_dict(a),True):rotation[ix[ch.position]]for a,ch in ll}
        actual={key(action_to_dict(a)):ix[replace(ch.position,ruleset_fingerprint=sc.ruleset_fingerprint)]for a,ch in rr}
        if len(expected)!=len(ll)or len(actual)!=len(rr)or expected!=actual:raise ValueError('rotated Core frontier is not bijective')
        counts['physical_vertices']+=1;counts['Core_edges']+=len(ll)+len(rr)
    laws={w['world']:w for w in prefix['rows']}
    def signature(record,rotate=False):return tuple(key(a,rotate)for a in record['actions'])
    target_rows={signature(r['record']):r for r in laws[26]['details']}
    if len(target_rows)!=len(laws[26]['details']):raise ValueError('ambiguous target physical prefix')
    pairs={};sessions={}
    for row in laws[24]['details']:
        other=target_rows.pop(signature(row['record'],True),None)
        if other is None:raise ValueError('rotated literal prefix missing')
        a=GameSession.replay(sc,deserialize_game_record(json.dumps(row['record'])))
        b=GameSession.replay(tc,deserialize_game_record(json.dumps(other['record'])))
        if (state_sha(a.state)!=row['id']or state_sha(b.state)!=other['id']or
            position(a.state.position,tc.ruleset_fingerprint)!=b.state.position or a.result!=b.result or
            repetition_partition(a)!=repetition_partition(b)or
            [(h.actor,h.gave_check)for h in a.state.history]!=[(h.actor,h.gave_check)for h in b.state.history]or
            a.state.ply_count!=b.state.ply_count or row['probability']!=other['probability']or row['fork']!=other['fork']):
            raise ValueError('rotated full-history binding differs')
        la=legal_successors(a.state,sc);ra=legal_successors(b.state,tc)
        if {key(action_to_dict(ac),True):v for (ac,_),v in zip(la,row['action_WDL'],strict=True)}!={key(action_to_dict(ac)):v for (ac,_),v in zip(ra,other['action_WDL'],strict=True)}:
            raise ValueError('rotated action WDL differs')
        pairs[row['id']]=other['id'];sessions[row['id']]=a;sessions[other['id']]=b;counts['full_prefix_pairs']+=1
    if target_rows:raise ValueError('unpaired target prefixes')
    matrices={r['id']:r for w in nominal['rows']for r in w['rows']};by={(r['id'],r['requested_depth']):r for r in queries['rows']};summary=[]
    for depth in(1,2):
        item=Counter();bad_mass=[F(0),F(0)]
        for lid,rid in pairs.items():
            if lid not in matrices:continue
            left,right=matrices[lid],matrices[rid]
            lm=max(a[f'D{depth}']for a in left['actions']);rm=max(a[f'D{depth}']for a in right['actions'])
            aa={key(a['action'],True):a['WDL']for a in left['actions']if a[f'D{depth}']==lm}
            bb={key(a['action']):a['WDL']for a in right['actions']if a[f'D{depth}']==rm}
            if lm!=rm or aa!=bb:raise ValueError('nominal maximizer sets not covariant')
            lq,rq=by[lid,depth],by[rid,depth]
            lk=key(lq['receipt']['action']['action'],True);rk=key(rq['receipt']['action']['action'])
            if lk not in aa or rk not in bb:raise ValueError('actual choice outside nominal tied maximizers')
            item['first_fork_pairs']+=1;item['choices_not_rotated']+=lk!=rk
            if depth==1:
                lf=min((ac for ac in sessions[lid].legal_actions()if key(action_to_dict(ac),True)in aa),key=str)
                rf=min((ac for ac in sessions[rid].legal_actions()if key(action_to_dict(ac))in bb),key=str)
                item['left_first_lexical_maximizer']+=key(action_to_dict(lf),True)==lk
                item['right_first_lexical_maximizer']+=key(action_to_dict(rf))==rk
            item['left_inferior']+=lq['optimal']is False;item['right_inferior']+=rq['optimal']is False
            item['quality_differs']+=lq['chosen_WDL']!=rq['chosen_WDL']
            for side,q,row in((0,lq,left),(1,rq,right)):
                if q['optimal']is False:bad_mass[side]+=F(row['probability'])
        summary.append(dict(depth=depth,counts=dict(item),arrival_error_mass=list(map(str,bad_mass))))
    return dict(verified=True,transformation='R(x,y)=(3-y,x)',source_world=24,target_world=26,
        counts=dict(counts),queries=summary,seconds=time.perf_counter()-tick,
        scope='All3952closedphysicalvertices and BOTHactualCorefrontiers bind the two frozen pureLeaper rules;210pairedfullprefixes preserve checks,clock,repetitionequality andprobability. Bothnominalmaximizersets rotate. Actuallexicaltiechoices neednotrotate; qualitydifference is algorithmrepresentationeffect underconditionaluniformarrival, not changedrules/values or end-to-end policystrength. No newPlayerquery or genericDSL-isomorphism claim.')


def verify_onset_reuse(inputs,results,truth,prefix,nominal,previous,sparse):
    """Provenance and finite arrival-weighted summaries, not query execution."""
    expected_ids=[r['id']for w in nominal['rows']for r in w['rows']]
    records={r['id']:(w['world'],r)for w in prefix['rows']for r in w['details']}
    matrices={r['id']:r for w in nominal['rows']for r in w['rows']}
    if len(expected_ids)!=194 or [r['id']for r in inputs['rows']]!=expected_ids:
        raise ValueError('onset support is not complete first-fork support')
    if (truth['source_prefix_digest']!=digest(prefix)or truth['source_nominal_digest']!=digest(nominal)or
        inputs['source_truth_digest']!=digest(truth)or inputs['rows']!=truth['certificate_decisions']or
        inputs['selection_digest']!=digest(expected_ids)or results['selection_digest']!=digest(expected_ids)):
        raise ValueError('onset input binding differs')
    for row in inputs['rows']:
        world,record=records[row['id']];mat=matrices[row['id']]
        if (row['world']!=world or row['record']!=record['record']or row['arrival_probability']!=record['probability']or
            row['actions']!=[dict(action=a['action'],wdl=a['WDL'])for a in mat['actions']]or
            row['value']!=max(a['WDL']for a in mat['actions'])or row['actor']!=0 or not row['fork']or row['immediate_win']):
            raise ValueError('onset root/action truth differs')
    sources={'previous_teacher':previous,'disjoint_sparse':sparse};prior={}
    for origin,source in sources.items():
        if inputs['source_query_digests'][origin]!=digest(source):raise ValueError('reused source digest differs')
        if source['plan']['query_nodes']!=8192 or source['plan']['query_seconds']!=3:raise ValueError('reused query conditions differ')
        for index,row in enumerate(source['rows']):
            key=(row['id'],row['requested_depth'])
            if key in prior:raise ValueError('ambiguous reused receipt')
            prior[key]=(origin,index,row)
    keys=[(hid,d)for hid in expected_ids for d in(1,2)]
    reused=[k for k in keys if k in prior];new=[k for k in keys if k not in prior]
    if (record_value(reused)!=inputs['reused_keys']or record_value(new)!=inputs['new_keys']or
        len(reused)!=32 or len(new)!=356 or results['new_queries']!=356 or
        inputs['plan']['depths']!=[1,2]or inputs['plan']['query_nodes']!=8192 or inputs['plan']['query_seconds']!=3):
        raise ValueError('new/reused query selection differs')
    by={};newnodes=0;reuse_counts=Counter()
    for row in results['rows']:
        key=(row['id'],row['requested_depth']);origin=row['receipt_origin'];body={k:v for k,v in row.items()if k!='receipt_origin'}
        if key in by:raise ValueError('duplicate retained onset query')
        by[key]=row
        if key in prior:
            name,index,old=prior[key]
            if origin!=dict(kind='REUSED',source=name,source_digest=digest(sources[name]),source_row=index)or body!=old:
                raise ValueError('reused receipt changed or relaunched')
            reuse_counts[name]+=1
        else:
            if origin!=dict(kind='NEW',runtime_source_sha=inputs['source_runtime_sha']):raise ValueError('new receipt provenance differs')
            newnodes+=row['receipt']['nodes']
    if set(by)!=set(keys)or newnodes!=results['new_nodes']or dict(reuse_counts)!=results['reused_by_source']:
        raise ValueError('onset incremental cost differs')
    summary=[]
    roots={r['id']:r for r in inputs['rows']}
    for depth in(1,2):
        for world in(24,26):
            rows=[by[hid,depth]for hid in expected_ids if roots[hid]['world']==world]
            mass=sum(F(roots[r['id']]['arrival_probability'])for r in rows)
            err=sum(F(roots[r['id']]['arrival_probability'])for r in rows if r['optimal']is False)
            summary.append(dict(depth=depth,world=world,contexts=len(rows),arrival_mass=str(mass),actual_error_mass=str(err),conditional_error=str(err/mass)))
    return dict(verified=True,rows=summary,new_queries=len(new),new_nodes=newnodes,reused=dict(reuse_counts),
        scope='Everyalreadyexecuted matching coldunitquery reusedbyteforbyte at scientificJSON level. 356newkeys only,32reusedkeys. Arrivalweights describe uniformprefixthenoneactualdecision, not fullD1/D2 policies, independent observations or learnedgain.')


def first_fork_error_bounds(inputs,results,prefix,nominal):
    """Partial-identification bounds; never fill the unobserved late mass.

    Incoming play stays uniform until its first critical decision. The metric
    is whether ONE selected action lowers exact WDL, not actual game utility.
    Each unobserved late action label remains in[0,1]. Contrast bounds allow
    the two algorithms to fail differently on every unobserved history.
    """
    roots={r['id']:r for r in inputs['rows']};by={(r['id'],r['requested_depth']):r for r in results['rows']}
    rows=[]
    for world in prefix['rows']:
        early=sum(map(F,world['first_fork_by_ply']));unseen=F(world['ongoing_no_fork_through_last_ply'])
        terminal=F(world['terminal_before_fork'])
        if early+unseen+terminal!=1:raise ValueError('first fork residual mass differs')
        choices=next(w['rows']for w in nominal['rows']if w['world']==world['world'])
        errors={name:F(0)for name in('FLOOR','nominal_uniform_tie_D1','nominal_uniform_tie_D2','actual_D1','actual_D2')}
        for row in choices:
            p=F(row['probability']);best=max(a['WDL']for a in row['actions'])
            errors['FLOOR']+=p*(F(0)if row['immediate_win']else F(sum(a['WDL']<best for a in row['actions']),len(row['actions'])))
            for depth in(1,2):
                errors[f'nominal_uniform_tie_D{depth}']+=p*F(row['depths'][depth-1]['uniform_tie_error'])
                q=by[row['id'],depth]
                if not q['requested_complete']or q['chosen_WDL']is None:raise ValueError('early action quality is unresolved')
                errors[f'actual_D{depth}']+=p*int(q['chosen_WDL']<roots[row['id']]['value'])
        delta=errors['actual_D1']-errors['actual_D2']
        rows.append(dict(world=world['world'],first_fork_observed_mass=str(early),unobserved_late_mass=str(unseen),
            policies={k:dict(observed_error_mass=str(v),conditional_early_error=str(v/early),
                arbitrary_late_completion_bounds=[str(v),str(v+unseen)])for k,v in errors.items()},
            D1_minus_D2_arbitrary_completion_bounds=[str(delta-unseen),str(delta+unseen)]))
    n=len(rows);survival=sum(F(r['unobserved_late_mass'])for r in rows)/n
    delta=sum(F(r['policies']['actual_D1']['observed_error_mass'])-F(r['policies']['actual_D2']['observed_error_mass'])for r in rows)/n
    return dict(rows=rows,uniform_two_root_mu=dict(observed_D1_minus_D2_error_mass=str(delta),unobserved_late_mass=str(survival),
        arbitrary_late_completion_contrast_bounds=[str(delta-survival),str(delta+survival)]),
        scope='Exactfirst-fork one-decision quality underuniformarrival, not completeD1/D2policy strength or score. Unobservedlate labels stay arbitrary[0,1], not DRAW or completedqueries. A positivecontrastlowerbound survivesalllate-labelcompletions, conditional ondefining onelegal decision there. Twofrozenrotatedroots are correlated controls, not IIDrules orholdout.')


def verify_positive_price_cells(result,directory):
    """Literal nominal D1/D2 frontier, plus finite leaf-order cell proof."""
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
    directory=Path(directory);inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz');adj=load(directory/'adjacent-pairs.json.gz')
    pair=adj['pairs'][0];plan=result['plan'];expected=[r['right_id']for r in pair['rows']]
    if (len(expected)!=128 or [r['id']for r in result['rows']]!=expected or plan['representatives']!=[.5,1.,2.]or
        plan['source_truth_digest']!=digest(truth)or plan['source_adjacency_digest']!=digest(adj)):
        raise ValueError('positive price-cell input differs')
    domain=load(directory/f"domain{pair['right_family']}.json.gz")
    if 0 in domain['terminals'].values():raise ValueError('positive terminal invalidates declared leaf alphabet')
    rootby={r['id']:r for r in truth['roots']};source=next(r for r in inputs['rows']if r['family']==pair['right_family'])
    c=admit(next(f for f in inputs['families']if f['family']==pair['right_family']),source);counts=Counter();checked=[]
    def evaluate(s,model):
        e=FixedScaleSessionEnv(s,unit_type='A');v=e.terminal()
        if v==1:raise ValueError('unexpected terminal WIN0')
        if v is not None:return MATE*v,None
        phi=list(e.features())
        if phi not in([1,-1,0,0],[1,0,0,0],[0,-1,0,0],[0,0,0,0]):raise ValueError('leaf outside four-affine alphabet')
        return model.raw(phi),phi
    for row,paired in zip(result['rows'],pair['rows'],strict=True):
        root=rootby[row['id']];s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
        if state_sha(s.state)!=row['id']or row['actual_WDL']!=root['wdl_bounds'][0]or row['direct_escape']!=bool(paired['new_best_escapes']):
            raise ValueError('positive cell root differs')
        env=FixedScaleSessionEnv(s,unit_type='A')
        if list(env.features())!=[1,-1,0,0]:raise ValueError('positive cell root features differ')
        if [p['B']for p in row['profiles']]!=[.5,1.,2.]:raise ValueError('positive cell support differs')
        for profile in row['profiles']:
            q=profile['B'];model=Model([q if n==('board','B')else 1. for n in env.names]);actions=[]
            for a in s.legal_actions():
                child=copy(s);child.submit(a);counts['Core_edges']+=1;one,phi=evaluate(child,model);two=one;phis=[phi]
                if child.result.status.value=='ongoing':
                    replies=[]
                    for b in child.legal_actions():
                        ch=copy(child);ch.submit(b);counts['Core_edges']+=1;replies.append(evaluate(ch,model))
                    two=min(v for v,_ in replies);phis=[p for v,p in replies if v==two]
                raw=action_to_dict(a);label=next(x['wdl_bounds'][0]for x in root['action_bounds']if x['action']==raw)
                actions.append(dict(action=raw,exact_WDL=label,D1=one,D2=two,D1_phi=[phi],D2_phi=phis))
            if actions!=profile['actions']:raise ValueError('price-cell literal frontier differs')
            for depth,annotation in zip((1,2),profile['depths'],strict=True):
                best=max(a[f'D{depth}']for a in actions);maxima=[a for a in actions if a[f'D{depth}']==best]
                bad=sum(a['exact_WDL']<row['actual_WDL']for a in maxima);phis=[p for a in maxima for p in a[f'D{depth}_phi']]
                nonzero=any(p is not None and any(model.gradient(p))for p in phis)
                expected_annotation=dict(depth=depth,maximizer_actions=[a['action']for a in maxima],inferior=bad,maximizers=len(maxima),
                    uniform_tie_error=str(F(bad,len(maxima))),possible_nonzero_free_leaf_gradient=nonzero,every_leaf_has_zero_free_gradient=not nonzero)
                if annotation!=expected_annotation:raise ValueError('price-cell quality/gradient differs')
        checked.append(row)
    if result['counts']!=dict(counts):raise ValueError('price-cell nominal cost differs')
    sensitive={str(d):dict(action=sum(len({digest(p['depths'][d-1]['maximizer_actions'])for p in r['profiles']})>1 for r in checked),
        quality=sum(len({p['depths'][d-1]['uniform_tie_error']for p in r['profiles']})>1 for r in checked))for d in(1,2)}
    if sensitive!=result['sensitive_counts']:raise ValueError('price-cell sensitivity differs')
    summaries=[]
    for q in(.5,1.,2.):
        for depth in(1,2):
            annotations=[next(p for p in r['profiles']if p['B']==q)['depths'][depth-1]for r in checked]
            summaries.append(dict(B=q,depth=depth,roots=len(annotations),
                nominal_uniform_tie_error=str(sum(F(a['uniform_tie_error'])for a in annotations)/len(annotations)),
                forced_error_roots=sum(a['inferior']==a['maximizers']for a in annotations),
                unsafe_tie_roots=sum(0<a['inferior']<a['maximizers']for a in annotations),
                possible_nonzero_free_leaf_gradient_roots=sum(a['possible_nonzero_free_leaf_gradient']for a in annotations)))
    if summaries!=result['summary']:raise ValueError('price-cell aggregate differs')
    affines=[(1,0),(1,-1),(0,0),(0,-1),(-int(MATE),0)]
    crossings={F(b-a,s-t)for a,s in affines for b,t in affines if s!=t and 0<F(b-a,s-t)<F(int(MATE),2)}
    if crossings!={F(1)}:raise ValueError('positive-cell affine boundary proof differs')
    return dict(verified=True,roots=len(checked),Core_edges=counts['Core_edges'],positive_cell_sensitive_roots=sensitive,
        all_positive_interior_affine_crossings=list(map(str,sorted(crossings))),
        D1_nonzero_free_gradient_by_root_WDL=dict(Counter(str(r['actual_WDL'])for r in checked if r['profiles'][0]['depths'][0]['possible_nonzero_free_leaf_gradient'])),
        scope='OnlypositiveB<MATE/2 nominalmaterialorder:1,1-B,0,-B plus draw0/LOSS-MATE; uniqueinteriorboundaryB=1. LiteralD1/D2 representativecells coverall128samefrozenstarts. No pricefit, newPlayer, experientialtraining or assertionabout lateron-policyhistories/actualtimedsearchcellinvariance.')


def verify_supplied_history_packet(packet):
    """Additional supplied histories through the existing certificate reader."""
    from scripts.leaper_single_parity_truth import admit as admit_single
    from scripts.generic_session_certificate_json import decode_session_certificate
    from scripts.generic_session_win_proof import verify_session_certificate
    from scripts.leaper_clock_rebinding import verify_history_draw_safety
    from scripts.leaper_h6_occupation import summarize_pair_onsets,supplied_first_fork_prefix
    from scripts.leaper_h6_initial_truth import decompose_existing_clock
    tick=time.perf_counter();packet=Path(packet);manifest=load(packet/'manifest.json')
    for name,expected in manifest['files'].items():
        if hashlib.sha256((packet/name).read_bytes()).hexdigest()!=expected:raise ValueError('history packet bytes differ: '+name)
    for name,expected in manifest.get('research_source_hashes',{}).items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=expected:raise ValueError('qualified research source differs: '+name)
    import gzip
    producers=json.loads(gzip.decompress((packet/'executed-producers.json.gz').read_bytes()))
    for file,source in [('material-control.json','material_control.py'),('sparse-depth-inputs.json.gz','sparse_depth.py'),('onset-depth-inputs.json.gz','onset_depth.py')]:
        if hashlib.sha256(producers[source].encode('utf-8')).hexdigest()!=load(packet/file)['plan']['source_sha256']:
            raise ValueError('executed diagnostic producer differs')
    parent=packet.parent;source=load(parent/'leaper_rule_coordinates_20261024/mate7-review-handoff.json')
    supplied=load(packet/'mate7-strategy.json')
    if supplied['source_digest']!=digest(source):raise ValueError('PRIMARY handoff digest differs')
    _,compiled,_=admit_single(source['full_rule'],require_parity=False);certificates=[]
    expected_roots={'mathematical_remaining':(source['remaining_branch']['full_record'],5),'complete_original_root':(source['full_initial_record'],7)}
    for row in supplied['rows']:
        if row['name']not in expected_roots:raise ValueError('unexpected supplied strategy')
        record,limit=expected_roots.pop(row['name'])
        s,cert=decode_session_certificate(compiled,row['certificate'],max_nodes=1000)
        if row['certificate']['root_record']!=record or cert.target!=0 or cert.tree.rank!=row['rank']or cert.tree.rank>limit:
            raise ValueError('supplied strategy binding/rank differs')
        receipt=verify_session_certificate(s,cert,max_nodes=1000,seconds=30,cancel=role_stop_requested)
        if not receipt['verified']:raise ValueError('supplied strategy is not an all-defense win')
        certificates.append(dict(name=row['name'],rank=cert.tree.rank,verification=receipt))
    if expected_roots:raise ValueError('missing supplied root strategy')
    domain=load(parent/'leaper_pair_transfer_20261024/mask5-domain.json.gz');counter=load(packet/'repeat4-counterexample.json')
    if counter['source_digest']!=digest(domain)or counter['rule']!=domain['target_rule']:raise ValueError('repeat4 source differs')
    _,compiled,_=admit_single(counter['rule'],require_parity=False);sessions=[];draw=None;win=None
    for row in counter['rows']:
        s=GameSession.replay(compiled,deserialize_game_record(json.dumps(row['record'])))
        if s.result.status.value!='ongoing'or state_sha(s.state)!=row['state_sha']or s.state.ply_count!=row['ply']:
            raise ValueError('repeat4 actual prefix differs')
        if row['value']==0:draw=verify_history_draw_safety(domain,counter['rule'],row['record'],row['draw_safety'])
        elif row['value']==1:
            bound,cert=decode_session_certificate(compiled,row['win_certificate'],max_nodes=8192)
            if bound.state!=s.state or cert.target!=0:raise ValueError('repeat4 WIN root differs')
            win=verify_session_certificate(s,cert,max_nodes=8192,seconds=30,cancel=role_stop_requested)
            if not win['verified']:raise ValueError('repeat4 WIN not verified')
        else:raise ValueError('unsupported counterexample label')
        sessions.append(s)
    if len(sessions)!=2 or draw is None or win is None:raise ValueError('incomplete repeat4 counterexample')
    a,b=sessions;key=repetition_identity_key(a.state.position,compiled)
    if (a.state.position!=b.state.position or a.state.ply_count!=b.state.ply_count or
        dict(a.state.repetition_counts)[key]!=1 or dict(b.state.repetition_counts)[key]!=1 or
        a.legal_actions()!=b.legal_actions()):raise ValueError('not matched current history aliases')
    divergence=load(packet/'repeat4-divergence.json');prefix=divergence['common_physical_prefix']
    for i,raw in enumerate(prefix):
        for s in sessions:
            aa=[ac for ac in s.legal_actions()if action_to_dict(ac)==raw]
            if len(aa)!=1:raise ValueError('common-prefix future action differs')
            s.submit(aa[0])
        if i<len(prefix)-1 and sessions[0].result!=sessions[1].result:raise ValueError('earlier terminal divergence')
    if [s.result.status.value for s in sessions]!=['repetition','ongoing']or len(prefix)!=3:
        raise ValueError('repeat4 future divergence differs')
    if [state_sha(s.state)for s in sessions]!=[divergence['left_state_sha'],divergence['right_state_sha']]:
        raise ValueError('repeat4 divergent full states differ')
    base=parent/'leaper_h6_initial_truth_20261023';adjacency=load(base/'adjacent-pairs.json.gz')
    onsets=summarize_pair_onsets(load(parent/'leaper_pair_transfer_20261024/policy-laws.json.gz'),adjacency)
    if digest(onsets)!=digest(load(packet/'policy-onsets.json')):raise ValueError('saved-law onset aggregation differs')
    clock=decompose_existing_clock(base)
    if digest(clock)!=digest(load(packet/'clock-decomposition.json')):raise ValueError('existing-clock decomposition differs')
    material=verify_material_escape_receipts(load(packet/'material-control.json'),base)
    worlds=load(parent/'leaper_single_parity_20261023/inputs.json.gz')['worlds']
    shallow=supplied_first_fork_prefix(domain,worlds)
    if digest(stable(shallow))!=digest(stable(load(packet/'shallow-first-fork.json'))):raise ValueError('literal shallow fork law differs')
    nominal=first_fork_nominal_material(domain,worlds,load(packet/'shallow-first-fork.json'))
    if digest(stable(nominal))!=digest(stable(load(packet/'first-fork-nominal.json'))):raise ValueError('first fork nominal material differs')
    sparse_truth=load(packet/'sparse-depth-truth.json.gz');sparse_inputs=load(packet/'sparse-depth-inputs.json.gz');sparse_results=load(packet/'sparse-depth-results.json.gz')
    expected_ids=[r['id']for w in nominal['rows']for r in w['rows']if r['depths'][1]['unsafe_tie']]
    old_results=load(parent/'leaper_pair_transfer_20261024/depth-results.json.gz');old_ids={r['id']for r in old_results['rows']}
    if (len(expected_ids)!=18 or old_ids&set(expected_ids)or sparse_inputs['old_query_digest']!=digest(old_results)or
        [r['id']for r in sparse_inputs['rows']]!=expected_ids or sparse_inputs['plan']['depths']!=[2,4]or
        sparse_inputs['plan']['planned_queries']!=36 or sparse_inputs['plan']['query_nodes']!=8192 or sparse_inputs['plan']['query_seconds']!=3):
        raise ValueError('sparse depth selection overlaps or differs')
    if sparse_truth['source_prefix_digest']!=digest(load(packet/'shallow-first-fork.json'))or sparse_truth['source_nominal_digest']!=digest(load(packet/'first-fork-nominal.json')):
        raise ValueError('sparse depth source digest differs')
    source_rows={r['id']:(w['world'],r)for w in nominal['rows']for r in w['rows']}
    records={r['id']:r for w in shallow['rows']for r in w['details']}
    for row in sparse_inputs['rows']:
        world,truth_row=source_rows[row['id']]
        if (row['world']!=world or row['record']!=records[row['id']]['record']or
            row['arrival_probability']!=records[row['id']]['probability']or
            row['actions']!=[dict(action=a['action'],wdl=a['WDL'])for a in truth_row['actions']]):
            raise ValueError('sparse depth root/action labels differ')
    sparse=verify_depth_receipts(worlds,sparse_truth,sparse_inputs,sparse_results,support='first_fork')
    onset_truth=load(packet/'onset-depth-truth.json.gz');onset_inputs=load(packet/'onset-depth-inputs.json.gz');onset_results=load(packet/'onset-depth-results.json.gz')
    reuse=verify_onset_reuse(onset_inputs,onset_results,onset_truth,load(packet/'shallow-first-fork.json'),load(packet/'first-fork-nominal.json'),old_results,sparse_results)
    onset=verify_depth_receipts(worlds,onset_truth,onset_inputs,onset_results,support='onset')
    rotation=verify_supplied_rotation(domain,worlds,load(packet/'shallow-first-fork.json'),load(packet/'first-fork-nominal.json'),onset_results)
    if digest(stable(rotation))!=digest(stable(load(packet/'rotation-control.json'))):raise ValueError('actual rotation control differs')
    error_bounds=first_fork_error_bounds(onset_inputs,onset_results,load(packet/'shallow-first-fork.json'),load(packet/'first-fork-nominal.json'))
    if digest(error_bounds)!=digest(load(packet/'first-fork-error-bounds.json')):raise ValueError('late-mass error bounds differ')
    price_cells=verify_positive_price_cells(load(packet/'price-regions.json'),base)
    failed=load(packet/'first-fork-failed.json')
    for row in failed['rows']:
        mass=list(map(F,row['first_fork_by_ply']));terminal=F(row['terminal_without_fork']);unknown=F(row['unresolved'])
        if sum(mass)+terminal+unknown!=1 or list(map(F,row['ever_fork_bounds']))!=[sum(mass),sum(mass)+unknown]:
            raise ValueError('failed DFS frontier mass was not preserved')
    return dict(verified=True,source_sha=manifest['runtime_source_sha'],seconds=time.perf_counter()-tick,
        mate_certificates=certificates,repeat4_draw=draw,repeat4_win=win,material=material,
        sparse_depth=sparse,
        onset_depth=onset,onset_reuse=reuse,rotation=rotation,
        first_fork_error_bounds=error_bounds,
        price_cells=price_cells,
        shallow_first_fork=[{k:v for k,v in r.items()if k!='details'}for r in shallow['rows']],clock_counts=clock['counts'],
        scope='Existing reader verifies supplied WIN and safety certificates, exact savedqueries/laws and complete shallowactualhistories; no newPlayer,training,rule/layoutsampling,capreset ordefaultchange. FullH64DFS remains failed/UNKNOWN.')


def verify_packet(packet,*,literal=False,prefixes=False,rebuild=False,policy_literal=False):
    from scripts.leaper_h6_pair_certificates import dual_replay
    from scripts.leaper_h6_adjacent_pairs import couple_uniform_prefixes,decompose_uniform_gain,paired_coordinates
    from scripts.leaper_clock_rebinding import check_domain,build_supplied_domain
    from scripts.leaper_h6_occupation import compare_pair_policies
    tick=time.perf_counter();packet=Path(packet);manifest=load(packet/'manifest.json')
    for name,expected in manifest['files'].items():
        if hashlib.sha256((packet/name).read_bytes()).hexdigest()!=expected:raise ValueError('packet bytes differ: '+name)
    base=packet.parent/'leaper_h6_initial_truth_20261023';single=packet.parent/'leaper_single_parity_20261023'
    for name,expected in manifest['source_files'].items():
        if hashlib.sha256((packet.parent/name).read_bytes()).hexdigest()!=expected:raise ValueError('source bytes differ: '+name)
    adjacency=load(base/'adjacent-pairs.json.gz');certs=load(base/'pair-certificates.json.gz')
    def compare(actual,name):
        # Scientific JSON transport normalizes Python tuples to JSON arrays.
        # Bind canonical values rather than container representation in RAM.
        if digest(stable(actual))!=digest(stable(load(packet/name))):raise ValueError('recomputed scientific evidence differs: '+name)
    compare(dual_replay(base,certs,adjacency),'dual-prefixes.json.gz')
    coupling=load(packet/'coupling.json.gz');compare(couple_uniform_prefixes(base,adjacency,coupling['plan']),'coupling.json.gz')
    gain=load(packet/'gain.json.gz');compare(decompose_uniform_gain(base,adjacency,coupling,gain['plan']),'gain.json.gz')
    compare(paired_coordinates(base,adjacency),'coordinates.json.gz')
    compare(verify_pair_order(base,adjacency),'order-proof.json')
    fresh=load(packet/'blocked-fresh.json');compare(verify_fresh_rank(base,fresh['plan']),'blocked-fresh.json')
    history=load(packet/'blocked-prefix.json');compare(verify_history_counterexamples(base,history),'history-counterexample-check.json')
    worlds=load(single/'inputs.json.gz')['worlds'];mask5=load(packet/'mask5-domain.json.gz')
    compare(check_domain(mask5,worlds,annotate=True),'mask5-truth.json.gz')
    compare(verify_depth_receipts(worlds,load(packet/'mask5-truth.json.gz'),load(packet/'depth-inputs.json.gz'),load(packet/'depth-results.json.gz')),'depth-validation.json')
    compare(shallow_material_mechanisms(worlds,load(packet/'mask5-truth.json.gz'),load(packet/'depth-results.json.gz')),'depth-mechanisms.json.gz')
    compare(material_feature_support(mask5,worlds),'material-feature-support.json')
    compare(comment_scope_review(),'comment-scope.json')
    policies=load(packet/'policy-laws.json.gz');compare(compare_pair_policies(base,adjacency,policies['plan']),'policy-laws.json.gz')
    policy_control=load(packet/'policy-validation.json')
    if not policy_control['verified']or policy_control['law_digest']!=digest(policies)or policy_control['cases']!=512:raise ValueError('policy literal control not bound')
    control=load(packet/'literal-gain.json')
    if not control['verified']or control['coupling_digest']!=digest(coupling)or control['gain_digest']!=digest(gain)or len(control['cases'])!=128:raise ValueError('literal law/gain control not bound')
    if literal:compare(verify_literal(base,adjacency,coupling,load(packet/'literal-gain-plan.json'),gain),'literal-gain.json')
    if prefixes:compare(verify_prefix_ranks(base,adjacency,history['plan']),'blocked-prefix.json')
    if rebuild:compare(build_supplied_domain(worlds,mask5['target_worlds'],mask5['plan'],mask5['source_packet_digest']),'mask5-domain.json.gz')
    if policy_literal:compare(verify_pair_policy_laws(base,adjacency,policies,load(packet/'policy-literal-plan.json')),'policy-validation.json')
    return dict(verified=True,seconds=time.perf_counter()-tick,manifest_sha256=hashlib.sha256((packet/'manifest.json').read_bytes()).hexdigest(),
        source_sha=manifest['runtime_source_sha'],H6_common_roots=128,dual_certificate_prefixes=80,prefix_counterexamples=2,
        H64_proven_WIN_histories=4,literal_uniform_gain_repeated=literal,all_prefix_ranks_repeated=prefixes,mask5_domain_regenerated=rebuild,policy_literal_repeated=policy_literal,
        scope='Portable actual-Core/history/certificate/analytic-law reader. Optional controls reproduce fullGameState risk and every played-prefix rank; default binds their exact receipts. SharedCore is not another engine; no Player/training/default/PRIMARYwrite.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet');p.add_argument('--literal',action='store_true');p.add_argument('--prefixes',action='store_true');p.add_argument('--rebuild',action='store_true');p.add_argument('--policy-literal',action='store_true')
    p.add_argument('--history-packet');p.add_argument('--directory');p.add_argument('--adjacency');p.add_argument('--coupling');p.add_argument('--plan');p.add_argument('--output',required=True);p.add_argument('--gain');a=p.parse_args()
    result=(verify_supplied_history_packet(a.history_packet)if a.history_packet else verify_packet(a.packet,literal=a.literal,prefixes=a.prefixes,rebuild=a.rebuild,policy_literal=a.policy_literal)if a.packet else
        verify_literal(a.directory,load(a.adjacency),load(a.coupling),load(a.plan),load(a.gain)if a.gain else None))
    save(a.output,result)
    if a.history_packet:
        print(json.dumps(dict(verified=result['verified'],seconds=result['seconds'],source_sha=result['source_sha'],
            mate_ranks=[r['rank']for r in result['mate_certificates']],onset_new_queries=result['onset_reuse']['new_queries'],
            onset_new_nodes=result['onset_reuse']['new_nodes'],rotation=result['rotation']['queries'],
            first_fork_error_bounds=result['first_fork_error_bounds']['uniform_two_root_mu'])))
    else:print(json.dumps({k:v for k,v in result.items()if k not in('cases','first_literal_witness_by_mechanism')}))
