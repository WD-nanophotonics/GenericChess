"""Fresh-root, repeat-two Leaper attractors generated entirely by shared Core.

This supports only the declared four-actor or coexistence capture-removal worlds.
It is not a GameState transposition table. Existing played prefixes cannot use
these labels without a separate history argument; the public learner is unchanged.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import replace
import heapq
import hashlib
import json
from math import perm
from pathlib import Path
import time

from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.position import GameState, HistoryRecord
from generic_chess.core.terminal import TerminalResult, TerminalStatus, terminal_result
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_to_dict
from scripts.leaper_microgames import (
    DIAGONAL, Exhaustion, coexistence_rules, make_rules, quiet_layouts, role_stop_requested,
)


def inactive_clock(width):
    """Upper bound on all positions + 1, including either/both pieces captured.

    Core currently requires positive integer max_ply. With repeat-two, every
    legal play ends by repetition/mate/stalemate before this clock can fire.
    The bound includes side to move and excludes neither illegal Anchor checks
    nor unreachable arrangements, so it is conservative, not a measured count.
    """
    n=width*width
    return 2*(perm(n,2)+2*perm(n,3)+perm(n,4))+1


def fresh_state(position, compiled):
    """Construct a fresh graph vertex, explicitly NOT a recovered played state."""
    key=repetition_identity_key(position,compiled)
    state=GameState(position,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),
                    (HistoryRecord(key,-1,'',False),))
    return replace(state,terminal_status=terminal_result(state,compiled))


def attractor(edges, terminals):
    """Relative W/L and minimum-win/maximum-loss distance; residual cycle draws.

    Heap order finalizes the minimum rank of winning nodes; losing nodes wait
    for every child. The graph must be complete before this function is called.
    Zero residual values are proven draws in this finite reachability game,
    never resource cutoffs. Terminal input is relative to its side to move.
    """
    parents=defaultdict(list)
    for parent,children in enumerate(edges):
        for child in children:parents[child].append(parent)
    values={i:v for i,v in terminals.items()if v}
    ranks={i:0 for i in values};queue=[(0,i)for i in values];heapq.heapify(queue)
    remaining=list(map(len,edges));worst=defaultdict(int)
    while queue:
        rank,child=heapq.heappop(queue)
        for parent in parents[child]:
            if parent in values or parent in terminals:continue
            if values[child]==-1:
                values[parent]=1;ranks[parent]=rank+1
            else:
                remaining[parent]-=1;worst[parent]=max(worst[parent],rank)
                if remaining[parent]:continue
                values[parent]=-1;ranks[parent]=worst[parent]+1
            heapq.heappush(queue,(ranks[parent],parent))
    for i in range(len(edges)):values.setdefault(i,0)
    return values,ranks


def solve_world(*, kinds=('M','M'), width=3, layouts=None, b_geometry=DIAGONAL, lineup=None,
                max_states=200000, seconds=120., composition_layout='original', initial_position=None,
                composition_c_axis='horizontal'):
    """Build and solve one explicitly restricted world; never accepts a RuleSet.

    No clock, progress counter, promotion, hands, drops, claims, semantic state,
    perpetual-check loss or history-dependent legality is silently discarded.
    The constructor fixes their absence. Position is sufficient for MOVES here;
    lifting graph WDL to actual repeat-two games is restricted to fresh roots.
    """
    began=time.perf_counter()
    if lineup is not None:
        if width!=3 or layouts is not None:raise ValueError('coexistence uses its declared 3x3 setup')
        # Each square is empty or one of the owner/type pairs. This deliberately
        # overcounts Anchor/piece multiplicities, but bounds all repeat keys.
        alphabet=1+2*(1+len(set(lineup)))
        rules=coexistence_rules(lineup,horizon=2*alphabet**9+1,layout=composition_layout,
            initial_position=initial_position,c_axis=composition_c_axis,b_geometry=b_geometry)
        layouts=[tuple(i for i,p in enumerate(sum(rules.initial_position,()))if p)]
    else:
        if composition_layout!='original'or initial_position is not None or composition_c_axis!='horizontal':raise ValueError('composition setup requires lineup')
        if layouts is None:layouts=quiet_layouts(288)if width==3 else[(0,1,width*width-1,width*width-2)]
        rules=make_rules(kinds=kinds,width=width,layouts=layouts,b_geometry=b_geometry,
                         horizon=inactive_clock(width))
    compiled=compile_ruleset_for_execution(rules)
    positions=[];indices={};pending=deque();actions=[];edges=[];terminals={};reasons=Counter()
    def add(position):
        if position not in indices:
            if len(positions)>=max_states:raise Exhaustion('UNKNOWN: Position allowance exhausted')
            indices[position]=len(positions);positions.append(position);pending.append(position)
        return indices[position]
    roots=[add(initial_state(compiled,str(i)if i else None).position)for i in range(len(layouts))]
    while pending:
        if role_stop_requested():raise Exhaustion('STOPPED_USER')
        if time.perf_counter()-began>=seconds:raise Exhaustion('UNKNOWN: graph time allowance exhausted')
        position=pending.popleft();index=indices[position]
        assert index==len(edges)
        state=fresh_state(position,compiled)
        if state.terminal_status.is_terminal:
            result=state.terminal_status
            assert result.status in(TerminalStatus.CHECKMATE,TerminalStatus.STALEMATE)
            terminals[index]=0 if result.winner is None else 1 if result.winner==position.side_to_move else -1
            reasons[result.status.value]+=1;actions.append(());edges.append(())
            continue
        choices=tuple(sorted(legal_actions(state,compiled),key=lambda a:json.dumps(action_to_dict(a),sort_keys=True)))
        assert choices
        children=tuple(apply_action(state,a,compiled)for a in choices)
        assert all(c.terminal_status.status not in(TerminalStatus.REPETITION,TerminalStatus.MAX_PLY)for c in children)
        actions.append(choices);edges.append(tuple(add(c.position)for c in children))
    values,ranks=attractor(edges,terminals)
    # Independently check every attractor/cycle constraint and rank certificate.
    for i,children in enumerate(edges):
        v=values[i]
        if i in terminals:assert v==terminals[i];continue
        if v==1:
            winning=[ranks[c]for c in children if values[c]==-1]
            assert winning and ranks[i]==min(winning)+1
        elif v==-1:
            assert all(values[c]==1 for c in children)
            assert ranks[i]==max(ranks[c]for c in children)+1
        else:
            assert all(values[c]!=-1 for c in children)and any(values[c]==0 for c in children)
    graph_seconds=time.perf_counter()-began
    summary=dict(kinds=kinds if lineup is None else None,lineup=lineup,width=width,composition_layout=composition_layout,
        composition_c_axis=composition_c_axis,declared_max_ply=rules.max_ply,
        positions=len(positions),edges=sum(map(len,edges)),terminal_reasons=reasons,
        relative_wdl=Counter(str(v)for v in values.values()),max_decisive_rank=max(ranks.values(),default=0),
        root_player0_wdl=Counter(str(values[i])for i in roots),
        genuine_choice_positions=sum(len({values[c]for c in es})>1 for es in edges),
        graph_seconds=graph_seconds,root_rows=[dict(layout=layout,value=values[i],rank=ranks.get(i),
            actions=[dict(action=action_to_dict(a),value=-values[c],child_rank=ranks.get(c))for a,c in zip(actions[i],edges[i])])
            for layout,i in zip(layouts,roots)],
        scope='Fresh roots only, repeat2 draw; no active whole-game clock by finite-position bound. No general history quotient or experiential oracle training.')
    return dict(rules=rules,compiled=compiled,positions=positions,indices=indices,
                actions=actions,edges=edges,terminals=terminals,values=values,ranks=ranks,roots=roots,summary=summary)


def run(output, **kwargs):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    (output/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    (output/'config.json').write_text(json.dumps(dict(arguments=kwargs,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2),encoding='utf-8')
    try:graph=solve_world(**kwargs)
    except Exhaustion as error:
        (output/'failure.json').write_text(json.dumps(dict(status=str(error),numeric_labels=None)),encoding='utf-8')
        raise
    (output/'rules.json').write_text(json.dumps(ruleset_to_dict(graph['rules']),indent=2),encoding='utf-8')
    (output/'summary.json').write_text(json.dumps(graph['summary'],indent=2),encoding='utf-8')
    return graph


def history_value(graph, state, *, with_rank=False):
    """Restricted observer: previously visited Positions become draw targets.

    This recomputes an attractor with blocked transitions. It does not return
    the fresh label as the played label, or modify public search/learning.
    Future cycles are still draw; every decisive attractor strategy decreases
    rank, so the fresh-root argument applies to the remaining graph as well.
    Only complete histories from this exact constructor/fingerprint are used.
    """
    compiled=graph['compiled']
    assert state.position.ruleset_fingerprint==compiled.ruleset_fingerprint
    assert len(state.history)==state.ply_count+1
    assert Counter(h.position_key for h in state.history)==dict(state.repetition_counts), 'history/count mismatch'
    assert state.history[-1].position_key==repetition_identity_key(state.position,compiled), 'history/current mismatch'
    assert state.ply_count<compiled.max_ply
    if state.terminal_status.is_terminal:
        result=state.terminal_status
        assert result.status in(TerminalStatus.CHECKMATE,TerminalStatus.STALEMATE,TerminalStatus.REPETITION)
        value=0 if result.winner is None else 1 if result.winner==state.position.side_to_move else -1
        return (value,0 if value else None)if with_rank else value
    if 'key_indices'not in graph:
        graph['key_indices']={repetition_identity_key(p,compiled):i for i,p in enumerate(graph['positions'])}
    keys=graph['key_indices'];blocked=frozenset(keys[h.position_key]for h in state.history)
    current=graph['indices'][state.position];cache=graph.setdefault('history_values',{})
    key=current,blocked
    if key not in cache:
        draw=len(graph['edges'])
        edges=[tuple(draw if c in blocked else c for c in cs)for cs in graph['edges']]+[()]
        values,ranks=attractor(edges,dict(graph['terminals'])|{draw:0})
        cache[key]=(values[current],ranks.get(current))
    return cache[key]if with_rank else cache[key][0]


def root_action_labels(graph, root):
    """Exact actions from a fresh root; returning to that root is already draw.

    Fresh child labels alone are unsafe when a winning child can revisit the
    parent. One blocked-root attractor scores every first action correctly.
    """
    if root in graph['terminals']:return {}
    raw={a:-graph['values'][c]for a,c in zip(graph['actions'][root],graph['edges'][root])}
    # Only a putative WIN action whose losing child has no smaller rank can
    # rely on revisiting this winning parent. For every other label, a
    # rank-decreasing winning strategy or residual-draw strategy avoids it.
    # Losing parents have ALL winning children at strictly smaller ranks.
    # Draw/losing alternatives of a winning parent cannot improve by replacing
    # that parent's win with draw. Fall back to the full attractor for ANY
    # unprotected winning child, including those not chosen by a searcher.
    if graph['values'][root]!=1 or all(
        graph['values'][c]!=-1 or graph['ranks'][c]<graph['ranks'][root]
        for c in graph['edges'][root]):
        return raw
    edges=list(graph['edges']);edges[root]=()
    values,_=attractor(edges,dict(graph['terminals'])|{root:0})
    labels={a:-values[c]for a,c in zip(graph['actions'][root],graph['edges'][root])}
    assert max(labels.values())==graph['values'][root]
    return labels


def history_action_labels(graph, state):
    """Score every legal action with one prefix-blocked observer attractor.

    Previously visited positions are draw targets. The new child is fresh in
    the remaining graph: decisive rank strategies cannot return to it, while
    residual cycles draw. No exact labels reach the experiential learner.
    """
    history_value(graph,state)  # Validate complete history/fingerprint first.
    if state.terminal_status.is_terminal:return {}
    keys=graph['key_indices']
    blocked={keys[h.position_key]for h in state.history}
    draw=len(graph['edges'])
    edges=[tuple(draw if c in blocked else c for c in cs)for cs in graph['edges']]+[()]
    values,_=attractor(edges,dict(graph['terminals'])|{draw:0})
    current=graph['indices'][state.position]
    labels={a:0 if c in blocked else -values[c]
        for a,c in zip(graph['actions'][current],graph['edges'][current])}
    assert max(labels.values())==history_value(graph,state)
    return labels


def winning_history_certificate(graph, state, *, max_nodes=10000):
    """Replay a scoped attractor win through actual Core against ALL defenses.

    This certifies a WDL win from the supplied full prefix, not the strength of
    a heuristic policy. Prefix keys are blocked before ranks are calculated.
    Every later edge strictly decreases rank, excluding new repetitions.
    """
    value=history_value(graph,state)
    if not value:raise ValueError('a decisive complete-history root is required')
    if max_nodes<1:raise Exhaustion('UNKNOWN: certificate node allowance exhausted')
    if state.terminal_status.is_terminal:
        return dict(winner=state.terminal_status.winner,root_value=value,root_rank=0,nodes=1,
            terminal_branches=1,leaf_paths=[[]],scope='Already actual Core scoring terminal;no successor or hypothetical play')
    blocked={graph['key_indices'][h.position_key]for h in state.history}
    draw=len(graph['edges'])
    edges=[tuple(draw if c in blocked else c for c in cs)for cs in graph['edges']]+[()]
    values,ranks=attractor(edges,dict(graph['terminals'])|{draw:0})
    root=graph['indices'][state.position];assert values[root]==value
    winner=state.position.side_to_move if value==1 else 1-state.position.side_to_move
    pending=[(state,())];nodes=0;leaves=[]
    while pending:
        if role_stop_requested():raise Exhaustion('STOPPED_USER')
        actual,path=pending.pop();nodes+=1
        if nodes>max_nodes:raise Exhaustion('UNKNOWN: certificate node allowance exhausted')
        if actual.terminal_status.is_terminal:
            assert actual.terminal_status.status in(TerminalStatus.CHECKMATE,TerminalStatus.STALEMATE)
            assert actual.terminal_status.winner==winner
            leaves.append([action_to_dict(a)for a in path]);continue
        i=graph['indices'][actual.position]
        choices=list(zip(graph['actions'][i],edges[i]))
        if actual.position.side_to_move==winner:
            choices=[next((a,c)for a,c in choices if values[c]==-1 and ranks[c]==ranks[i]-1)]
        for action,child in choices:
            assert child!=draw and ranks[child]<ranks[i]
            actual_child=apply_action(actual,action,graph['compiled'])
            assert graph['indices'][actual_child.position]==child
            assert actual_child.terminal_status.status not in(TerminalStatus.REPETITION,TerminalStatus.MAX_PLY)
            pending.append((actual_child,path+(action,)))
    return dict(winner=winner,root_value=value,root_rank=ranks[root],nodes=nodes,
        terminal_branches=len(leaves),leaf_paths=leaves,
        scope='Actual Core full-prefix replay,one rank strategy and ALL defender replies;not a general history quotient')


def fresh_depth_study(output, *, width=4, roots_count=64,
                      depths=(1,2,3,4,6,8,12), whole_seconds=900):
    """A bounded public-search resource curve on a declared exact small world.

    Root selection hashes layouts before solving; neither WDL nor search errors
    select roots. Symmetric layouts remain correlated, not independent games.
    Returned shallower iterations, missing requests and UNKNOWN stay explicit.
    """
    from statistics import median
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,BudgetEnd
    from generic_chess.learning.mainline_search import search
    from generic_chess.session.session import GameSession
    output=Path(output);output.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    layouts=quiet_layouts(roots_count,width=width)
    config=dict(width=width,roots=layouts,depths=depths,query_nodes=8192,query_seconds=3,
        whole_seconds=whole_seconds,graph_seconds=120,graph_positions=200000,
        root_selection='same safe-layout SHA order as original benchmark;default first;no label selection',
        evaluation='material unit M=1;public q0;zero capture-order prices;fresh TT per query')
    (output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    try:graph=solve_world(width=width,layouts=layouts,seconds=min(120,whole_seconds))
    except Exhaustion as error:
        failure=dict(status=str(error),numeric_labels=None,queries=0,
            missing=len(layouts)*len(depths),seconds=time.perf_counter()-began)
        (output/'summary.json').write_text(json.dumps(failure,indent=2),encoding='utf-8')
        return failure
    (output/'rules.json').write_text(json.dumps(ruleset_to_dict(graph['rules']),indent=2),encoding='utf-8')
    (output/'exact.json').write_text(json.dumps(graph['summary'],indent=2),encoding='utf-8')
    rows=[];labels={};status='COMPLETE'
    def guard():
        if role_stop_requested():raise BudgetEnd('STOPPED_USER')
        if time.perf_counter()-began>=whole_seconds:raise BudgetEnd('WHOLE_TIME_UNKNOWN')
    try:
        for setup,root in enumerate(graph['roots']):
            guard();labels[setup]=root_action_labels(graph,root)
        with(output/'queries.jsonl').open('x',encoding='utf-8')as stream:
            for depth in depths:
                for setup,root in enumerate(graph['roots']):
                    guard();session=GameSession(graph['compiled'],initial_setup_key=str(setup)if setup else None)
                    env=FixedScaleSessionEnv(session,unit_type='M')
                    receipt=search(env,Model([1.]*len(env.names)),depth=depth,nodes=8192,
                        seconds=min(3,whole_seconds-time.perf_counter()+began),cancel=guard)
                    chosen=labels[setup].get(receipt.action.action)if receipt.complete else None
                    row=dict(setup=setup,layout=layouts[setup],depth=depth,
                        completed_depth=receipt.completed_depth,returned=receipt.complete,
                        nodes=receipt.nodes,seconds=receipt.seconds,reason=receipt.reason,
                        chosen_value=chosen,exact_best=graph['values'][root],
                        optimal=None if chosen is None else chosen==graph['values'][root],
                        pv_terminal=receipt.pv_terminal,pv_phi=receipt.pv_phi,value=receipt.value,
                        action=None if not receipt.complete else action_to_dict(receipt.action.action))
                    rows.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
                print('completed requested depth',depth,flush=True)
    except BudgetEnd as error:status=str(error)
    def canonical(layout):
        variants=[]
        for reflect in(False,True):
            xy=[(s%width,s//width)for s in layout]
            if reflect:xy=[(width-1-x,y)for x,y in xy]
            for _ in range(4):
                variants.append(tuple(y*width+x for x,y in xy))
                xy=[(width-1-y,x)for x,y in xy]
        return min(variants)
    summary=dict(status=status,scope=f'Finite {len(layouts)}-root MM diagnostic;not heldout or population depth monotonicity. Exact action labels block return to parent;no active rule clock.',
        root_symmetry_classes=len({canonical(x)for x in layouts}),graph=graph['summary'],
        planned=len(layouts)*len(depths),queries=len(rows),missing=len(layouts)*len(depths)-len(rows),
        nodes=sum(r['nodes']for r in rows),seconds=time.perf_counter()-began,
        by_requested_depth=[dict(depth=d,queries=len(rs),returned=sum(r['returned']for r in rs),
            requested_complete=sum(r['completed_depth']==d for r in rs),
            completed_depths=Counter(str(r['completed_depth'])for r in rs),
            errors=sum(r['optimal']is False for r in rs),unknown=sum(r['optimal']is None for r in rs),
            nodes=sum(r['nodes']for r in rs),median_nodes=median(r['nodes']for r in rs)if rs else None,
            seconds=sum(r['seconds']for r in rs))for d in depths for rs in([r for r in rows if r['depth']==d],)])
    (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


def composition_without_clock(output, *, ratios=(.25,.75,1.,1.25,3.),
                              depths=(1,2,3,6), whole_seconds=600, layout='original'):
    """New-rule diagnostic at previously exposed common H6 legal prefixes.

    Rebuild each complete Core graph once for new history-conditioned labels,
    then retain an ignored local graph cache for future reuse. No old slots are
    refilled. The prefix subset is deliberately NOT all unlimited histories.
    """
    import gzip,pickle
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,BudgetEnd
    from generic_chess.learning.mainline_search import search
    from scripts.leaper_microgames import ExactTree,session_at
    output=Path(output);output.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    source=Path(__file__).read_bytes()
    (output/'executed-source.py').write_bytes(source)
    config=dict(ratios=ratios,depths=depths,layout=layout,whole_seconds=whole_seconds,graph_seconds_each=120,
        graph_states_each=200000,query_nodes=100000,query_seconds=3,fixed_A=1,fixed_C=1,
        selection='ALL H6 common ongoing prefixes in declared layout,not all no-clock histories',
        source_sha256=hashlib.sha256(source).hexdigest())
    (output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    small=[];maps=[]
    for lineup in(('A','B','A'),('A','B','C')):
        tree=ExactTree(compile_ruleset_for_execution(coexistence_rules(lineup,layout=layout)))
        tree.solve(initial_state(tree.compiled));small.append(tree)
        maps.append({p:s for s,p in tree.paths.items()})
    paths=sorted((p for p in set(maps[0])&set(maps[1])if all(t.edges[m[p]]for t,m in zip(small,maps))),
                 key=lambda p:json.dumps([action_to_dict(a)for a in p],sort_keys=True))
    def guard():
        if role_stop_requested():raise BudgetEnd('STOPPED_USER')
        if time.perf_counter()-began>=whole_seconds:raise BudgetEnd('WHOLE_TIME_UNKNOWN')
    rows=[];worlds={};status='COMPLETE'
    try:
        with(output/'queries.jsonl').open('x',encoding='utf-8')as stream:
            for world,lineup,old,mapping in zip(('ABA','ABC'),(('A','B','A'),('A','B','C')),small,maps):
                guard();graph=solve_world(lineup=lineup,composition_layout=layout,
                    seconds=min(120,whole_seconds-time.perf_counter()+began))
                # Own generated objects only; never load third-party pickle.
                cache={k:v for k,v in graph.items()if k!='compiled'}
                (output/(world+'-graph.pkl.gz')).write_bytes(gzip.compress(pickle.dumps(cache)))
                (output/(world+'-rules.json')).write_text(json.dumps(ruleset_to_dict(graph['rules']),indent=2),encoding='utf-8')
                worlds[world]=dict(graph=graph['summary'],changed_reference_contexts=0,contexts=0)
                for index,path in enumerate(paths):
                    guard();session=session_at(graph['compiled'],None,path);state=session.state
                    assert not state.terminal_status.is_terminal
                    sign=1 if state.position.side_to_move==0 else -1
                    best=history_value(graph,state);old_best=old.values[mapping[path]]*sign
                    worlds[world]['changed_reference_contexts']+=best!=old_best
                    worlds[world]['contexts']+=1
                    env=FixedScaleSessionEnv(session,unit_type='A')
                    for ratio in ratios:
                        weights=[ratio if n==('board','B')else 1. for n in env.names]
                        for depth in depths:
                            guard();receipt=search(env,Model(weights),depth=depth,nodes=100000,
                                seconds=min(3,whole_seconds-time.perf_counter()+began),cancel=guard)
                            chosen=None
                            if receipt.complete:
                                child=apply_action(state,receipt.action.action,graph['compiled'])
                                chosen=-history_value(graph,child)
                            row=dict(world=world,index=index,path=[action_to_dict(a)for a in path],
                                ratio=ratio,depth=depth,completed_depth=receipt.completed_depth,
                                complete=receipt.complete,nodes=receipt.nodes,seconds=receipt.seconds,
                                reason=receipt.reason,exact_best=best,old_h6_best=old_best,
                                chosen_value=chosen,optimal=None if chosen is None else chosen==best,
                                action=None if not receipt.complete else action_to_dict(receipt.action.action))
                            rows.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
                print('completed world',world,'seconds',time.perf_counter()-began,flush=True)
    except(BudgetEnd,Exhaustion)as error:status=str(error)
    summary=dict(config=config,status=status,common_contexts=len(paths),worlds=worlds,
        planned=2*len(paths)*len(ratios)*len(depths),queries=len(rows),
        missing=2*len(paths)*len(ratios)*len(depths)-len(rows),
        nodes=sum(r['nodes']for r in rows),seconds=time.perf_counter()-began,
        table=[dict(world=w,ratio=r,depth=d,queries=len(rs),
            requested_complete=sum(x['complete']and x['completed_depth']==d for x in rs),
            unknown=sum(x['optimal']is None for x in rs),errors=sum(x['optimal']is False for x in rs))
            for w in('ABA','ABC')for r in ratios for d in depths
            for rs in([x for x in rows if x['world']==w and x['ratio']==r and x['depth']==d],)])
    (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


def paired_history_study(output, *, caches, prefixes, models, depths=(1,2,3),
                         reused=(), whole_seconds=600):
    """Frozen policies at identical complete legal histories in two rule worlds.

    Caches must be own generated graphs. Labels are observer-only, recomputed
    with the full prefix. A reused row names the world/index/model/depth and
    must carry an action, exact label and completed depth; its action is checked
    against the current graph. No training or missing-slot retry occurs here.
    """
    import gzip,pickle
    from generic_chess.core.actions import action_from_dict
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,BudgetEnd
    from generic_chess.learning.mainline_search import search
    from scripts.leaper_microgames import session_at
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    began=time.perf_counter();rows=[];contexts=[];status='COMPLETE'
    config=dict(caches={k:str(v)for k,v in caches.items()},prefixes=prefixes,
        models=models,depths=depths,whole_seconds=whole_seconds,query_nodes=100000,
        query_seconds=3,selection='Previously fixed common legal prefixes; exposed finite diagnostic')
    (output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (output/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    old={(r['world'],r['index'],r['model'],r['depth']):r for r in reused}
    def guard():
        if role_stop_requested():raise BudgetEnd('STOPPED_USER')
        if time.perf_counter()-began>=whole_seconds:raise BudgetEnd('WHOLE_TIME_UNKNOWN')
    try:
        with(output/'queries.jsonl').open('x',encoding='utf-8')as stream:
            for world,cache in caches.items():
                guard();g=pickle.loads(gzip.decompress(Path(cache).read_bytes()))
                g['compiled']=compile_ruleset_for_execution(g['rules'])
                for index,encoded in enumerate(prefixes):
                    guard();path=tuple(action_from_dict(a)for a in encoded)
                    session=session_at(g['compiled'],None,path);state=session.state
                    assert not state.terminal_status.is_terminal
                    labels=history_action_labels(g,state);best=history_value(g,state)
                    assert set(labels)==set(legal_actions(state,g['compiled']))
                    contexts.append(dict(world=world,index=index,best=best,ply=state.ply_count,
                        action_values=[dict(action=action_to_dict(a),value=v)for a,v in labels.items()]))
                    env=FixedScaleSessionEnv(session,unit_type='A')
                    for name,weights in models.items():
                        for depth in depths:
                            guard();key=(world,index,name,depth)
                            if key in old:
                                row=dict(old[key]);a=action_from_dict(row['action'])
                                assert row['completed_depth']==depth and labels[a]==row['chosen_value']
                                assert row['exact_best']==best
                                row['reused']=True
                            else:
                                remaining=whole_seconds-time.perf_counter()+began
                                if remaining<=0:raise BudgetEnd('WHOLE_TIME_UNKNOWN')
                                receipt=search(env,Model(weights),depth=depth,nodes=100000,
                                    seconds=min(3,remaining),cancel=guard)
                                a=receipt.action.action if receipt.complete and receipt.action else None
                                value=None if a is None else labels[a]
                                row=dict(world=world,index=index,model=name,depth=depth,
                                    completed_depth=receipt.completed_depth,complete=receipt.complete,
                                    nodes=receipt.nodes,seconds=receipt.seconds,reason=receipt.reason,
                                    exact_best=best,chosen_value=value,
                                    optimal=None if value is None else value==best,
                                    action=None if a is None else action_to_dict(a),reused=False)
                            rows.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
                print('completed',world,'seconds',time.perf_counter()-began,flush=True)
    except(BudgetEnd,Exhaustion)as error:status=str(error)
    planned=len(caches)*len(prefixes)*len(models)*len(depths)
    summary=dict(config=config,status=status,planned=planned,recorded=len(rows),missing=planned-len(rows),
        reused=sum(r['reused']for r in rows),new_nodes=sum(r['nodes']for r in rows if not r['reused']),
        seconds=time.perf_counter()-began,contexts=contexts,
        table=[dict(world=w,model=m,depth=d,queries=len(rs),
            requested_complete=sum(r['complete']and r['completed_depth']==d for r in rs),
            unknown=sum(r['optimal']is None for r in rs),errors=sum(r['optimal']is False for r in rs))
            for w in caches for m in models for d in depths
            for rs in([r for r in rows if(r['world'],r['model'],r['depth'])==(w,m,d)],)])
    (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


def experiential_probe(output, *, episodes=32, depth=2, opening_count=0, opening_seed=20261022,
                       random_foe_seed=None, initial_weights=None,
                       lineup=('A','B','C'), c_axis='horizontal', initial_positions=None,
                       selfplay=False, b_geometry=DIAGONAL, initial_position=None):
    """One declared coexistence experiential check, with NO label interface.

    The default fresh root, or explicit sampled openings and opponent policies,
    diagnose available signal rather than independent strength or coverage.
    Literal PV paths are retained for later mechanism analysis. Optional initial
    weights change only the learner's starting point; the foe stays uniform.
    A single explicit initial position can also use label-blind played openings.
    Explicit fresh initial boards use ordinary validated setup options. They
    cannot be combined with played random openings or imported old histories.
    Optional selfplay shares the current model on both sides, frozen during
    each episode and updated once afterwards; the default foe stays uniform.
    """
    from dataclasses import asdict
    import random
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,TDLeafEpisode,play_episode,BudgetEnd
    from generic_chess.session.session import GameSession
    from scripts.leaper_microgames import sampled_openings,session_at
    if not isinstance(selfplay,bool) or (selfplay and random_foe_seed is not None):
        raise ValueError('selfplay is boolean and cannot use a random foe')
    output=Path(output);output.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    if initial_position is not None and initial_positions is not None:
        raise ValueError('declare one initial position or multiple setup boards')
    rules=coexistence_rules(lineup,horizon=2*9**9+1,c_axis=c_axis,b_geometry=b_geometry,
                            initial_position=initial_position)
    setups=[None]
    if initial_positions is not None:
        from dataclasses import replace
        from generic_chess.rules.schema import RuleInitialSetupOption
        if opening_count or not initial_positions:
            raise ValueError('fresh initial boards require nonempty positions and no played openings')
        boards=tuple(initial_positions)
        rules=replace(rules,initial_position=boards[0],initial_setup_options=tuple(
            RuleInitialSetupOption(str(i),board)for i,board in enumerate(boards)if i))
        setups += [str(i)for i in range(1,len(boards))]
    compiled=compile_ruleset_for_execution(rules)
    paths=sampled_openings(compiled,count=opening_count,seed=opening_seed)if opening_count else[()]
    env=FixedScaleSessionEnv(GameSession(compiled),unit_type='A')
    weights=[1.]*len(env.names)if initial_weights is None else list(initial_weights)
    if len(weights)!=len(env.names)or weights[0]!=1.:
        raise ValueError('initial weights must match environment names and fixed A=1')
    model=Model(weights);foe=model if selfplay else Model([1.]*len(env.names))
    config=dict(episodes=episodes,candidate_depth=depth,foe_depth=depth if selfplay else 2,initial=model.weights,
        names=env.names,eta=.05,lam=.95,scale=10,root='one symmetric fresh coexistence start',
        lineup=lineup,c_axis=c_axis,b_geometry=b_geometry,
        colors='episode%2',query_nodes=8192,game_nodes=524288,game_horizon=64,
        game_seconds=10,whole_nodes=2000000,whole_seconds=120,
        oracle='NONE: no reference labels available to the training runner',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    config.update(opening_count=opening_count,opening_seed=opening_seed,
        opening_selection='Uniform legal random walks;target lengths cycle1..6;terminal/duplicate paths retained;NO oracle or search selection',
        opening_paths=[[action_to_dict(a)for a in path]for path in paths])
    config.update(foe_policy=f'episode-frozen adaptive D{depth} selfplay'if selfplay else'uniform D2'if random_foe_seed is None else'uniform legal RNG,zero search nodes',
        random_foe_seed=random_foe_seed)
    if opening_count:config['root']='Declared world actual histories after fixed random legal openings;not fresh Position resets'
    if initial_positions is not None:
        config.update(root='Declared validated fresh initial boards;two colors per board;no previous history',
            initial_setup_count=len(setups),initial_setup_order=setups)
    (output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (output/'rules.json').write_text(json.dumps(ruleset_to_dict(rules),indent=2),encoding='utf-8')
    (output/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    paid=0;rows=[];queries=[];status='COMPLETE'
    def guard():
        if role_stop_requested():raise BudgetEnd('STOPPED_USER')
        if time.perf_counter()-began>=120:raise BudgetEnd('WHOLE_TIME_UNKNOWN')
        if paid>=2000000:raise BudgetEnd('WHOLE_NODES_UNKNOWN')
    with(output/'queries.jsonl').open('x',encoding='utf-8')as qout,(output/'episodes.jsonl').open('x',encoding='utf-8')as eout,(output/'opponent-moves.jsonl').open('x',encoding='utf-8')as fout:
        try:
            for i in range(episodes):
                guard()
                if 2000000-paid<524288:raise BudgetEnd('FULL_GAME_RESERVE_CAP')
                opening_index=(i//2)%len(paths)
                setup_index=(i//2)%len(setups)
                env=FixedScaleSessionEnv(session_at(compiled,setups[setup_index],paths[opening_index]),unit_type='A')
                initial_record=env.record();before=list(model.weights)
                rng=random.Random(random_foe_seed+i)if random_foe_seed is not None else None
                def random_foe(current):
                    choice=rng.choice(current.actions())
                    assert choice.kind=='ACTION'
                    fout.write(json.dumps(dict(episode=i,ply=current.session.state.ply_count,
                        actor=current.player(),action=action_to_dict(choice.action)))+'\n');fout.flush()
                    return choice
                def observe(ply,actor,receipt):
                    nonlocal paid
                    paid+=receipt.nodes;assert model.weights==before
                    row=dict(episode=i,color=i%2,ply=ply,actor=actor,candidate_weights=before,
                        opening_index=opening_index,prefix_length=len(paths[opening_index]),
                        initial_setup_index=setup_index,
                        search_weights=list((model if actor==i%2 else foe).weights),**asdict(receipt))
                    queries.append(row);qout.write(json.dumps(row,default=str)+'\n');qout.flush()
                result=play_episode(env,model,opponent=foe,learner=TDLeafEpisode(),learner_color=i%2,
                    horizon=64,depth=depth,opponent_depth=depth if selfplay else 2,query_nodes=8192,max_nodes=524288,
                    seconds=10,cancel=guard,on_query=observe,search_backend='mainline',
                    opponent_policy=None if rng is None else random_foe)
                row=dict(episode=i,color=i%2,before_weights=before,weights=list(model.weights),
                    opening_index=opening_index,initial_record=initial_record,
                    initial_setup_index=setup_index,
                    record=env.record(),**asdict(result))
                rows.append(row);eout.write(json.dumps(row)+'\n');eout.flush()
                if result.ending=='STOPPED_USER':raise BudgetEnd('STOPPED_USER')
        except BudgetEnd as error:status=str(error)
    own=[q for q in queries if q['actor']==q['color']]
    summary=dict(config=config,status=status,episodes=len(rows),missing=episodes-len(rows),
        final=model.weights,nodes=paid,queries=len(queries),seconds=time.perf_counter()-began,
        outcomes=Counter('UNKNOWN'if e['outcome']is None else str(e['outcome']*(1 if e['color']==0 else -1))for e in rows),
        endings=Counter(e['ending']for e in rows),changed_updates=sum(e['update']['changed']for e in rows),
        candidate_queries=len(own),terminal_pvs=sum(q['pv_terminal']for q in own),
        nonterminal_trainable_features=sum(not q['pv_terminal']and any(q['pv_phi'][1:])for q in own if q['complete']),
        scope='Declared opening/policy mechanism evidence,not independent games or strength/transfer validation.')
    (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output')
    parser.add_argument('--width',type=int,default=3);parser.add_argument('--seconds',type=float,default=120.)
    parser.add_argument('--states',type=int,default=200000)
    args=parser.parse_args()
    result=run(args.output,width=args.width,seconds=args.seconds,max_states=args.states)
    print(json.dumps({k:v for k,v in result['summary'].items()if k!='root_rows'},indent=2))
