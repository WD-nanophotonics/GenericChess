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


def verify_depth_receipts(worlds,truth,inputs,results):
    """Verify retained decisions/PVs/labels. NEVER rerun a closed query batch."""
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,SessionChoice,MATE
    from scripts.leaper_single_parity_truth import admit as admit_single
    selected=[s for s in truth['certificate_decisions']if s['actor']==0 and s['fork']and not s['immediate_win']]
    if inputs['source_truth_digest']!=digest(truth)or inputs['rows']!=selected or inputs['selection_digest']!=digest([s['id']for s in selected]):raise ValueError('depth diagnostic selection differs')
    by={s['id']:s for s in selected};plan=inputs['plan']
    expected={(s['id'],d)for s in selected for d in plan['depths']}
    actual=[(r['id'],r['requested_depth'])for r in results['rows']]
    if len(actual)!=len(set(actual))or set(actual)!=expected or results['missing']!=0:raise ValueError('depth receipt support differs')
    nodes=0;pv_edges=0;bad_controls=[];summaries=[]
    for row in results['rows']:
        root=by[row['id']];world=next(w for w in worlds if w['world']==root['world']);_,c,_=admit_single(world['rule'],require_parity=False)
        s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
        if state_sha(s.state)!=row['id']:raise ValueError('depth root history mismatch')
        env=FixedScaleSessionEnv(s,unit_type='A');model=Model(row['weights']);receipt=row['receipt'];nodes+=receipt['nodes']
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
                    captures.append(dict(action=action_to_dict(a),record=record_value(ch.to_record()),state_sha=state_sha(ch.state)))
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
    p.add_argument('--directory');p.add_argument('--adjacency');p.add_argument('--coupling');p.add_argument('--plan');p.add_argument('--output',required=True);p.add_argument('--gain');a=p.parse_args()
    result=(verify_packet(a.packet,literal=a.literal,prefixes=a.prefixes,rebuild=a.rebuild,policy_literal=a.policy_literal)if a.packet else
        verify_literal(a.directory,load(a.adjacency),load(a.coupling),load(a.plan),load(a.gain)if a.gain else None))
    save(a.output,result);print(json.dumps({k:v for k,v in result.items()if k not in('cases','first_literal_witness_by_mechanism')}))
