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
                max_states=200000, seconds=120.):
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
        rules=coexistence_rules(lineup,horizon=2*alphabet**9+1)
        layouts=[tuple(i for i,p in enumerate(sum(rules.initial_position,()))if p)]
    else:
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
    summary=dict(kinds=kinds if lineup is None else None,lineup=lineup,width=width,declared_max_ply=rules.max_ply,
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
    edges=list(graph['edges']);edges[root]=()
    values,_=attractor(edges,dict(graph['terminals'])|{root:0})
    labels={a:-values[c]for a,c in zip(graph['actions'][root],graph['edges'][root])}
    assert max(labels.values())==graph['values'][root]
    return labels


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
                              depths=(1,2,3,6), whole_seconds=600):
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
    config=dict(ratios=ratios,depths=depths,whole_seconds=whole_seconds,graph_seconds_each=120,
        graph_states_each=200000,query_nodes=100000,query_seconds=3,fixed_A=1,fixed_C=1,
        selection='ALL previously exposed H6 common ongoing prefixes,not all no-clock histories',
        source_sha256=hashlib.sha256(source).hexdigest())
    (output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    small=[];maps=[]
    for lineup in(('A','B','A'),('A','B','C')):
        tree=ExactTree(compile_ruleset_for_execution(coexistence_rules(lineup)))
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
                guard();graph=solve_world(lineup=lineup,seconds=min(120,whole_seconds-time.perf_counter()+began))
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


def experiential_probe(output, *, episodes=32, depth=2):
    """One symmetric ABC experiential check, with NO reference-label interface.

    One deterministic fresh root and alternating learner colors intentionally
    diagnose available signal, not independent strength or exploration coverage.
    Literal PV paths are now retained for later mechanism analysis.
    """
    from dataclasses import asdict
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,TDLeafEpisode,play_episode,BudgetEnd
    from generic_chess.session.session import GameSession
    output=Path(output);output.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    rules=coexistence_rules(('A','B','C'),horizon=2*9**9+1)
    compiled=compile_ruleset_for_execution(rules)
    env=FixedScaleSessionEnv(GameSession(compiled),unit_type='A')
    model=Model([1.]*len(env.names));foe=Model([1.]*len(env.names))
    config=dict(episodes=episodes,candidate_depth=depth,foe_depth=2,initial=model.weights,
        names=env.names,eta=.05,lam=.95,scale=10,root='one symmetric fresh ABC start',
        colors='episode%2',query_nodes=8192,game_nodes=524288,game_horizon=64,
        game_seconds=10,whole_nodes=2000000,whole_seconds=120,
        oracle='NONE: no reference labels available to the training runner',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (output/'rules.json').write_text(json.dumps(ruleset_to_dict(rules),indent=2),encoding='utf-8')
    (output/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    paid=0;rows=[];queries=[];status='COMPLETE'
    def guard():
        if role_stop_requested():raise BudgetEnd('STOPPED_USER')
        if time.perf_counter()-began>=120:raise BudgetEnd('WHOLE_TIME_UNKNOWN')
        if paid>=2000000:raise BudgetEnd('WHOLE_NODES_UNKNOWN')
    with(output/'queries.jsonl').open('x',encoding='utf-8')as qout,(output/'episodes.jsonl').open('x',encoding='utf-8')as eout:
        try:
            for i in range(episodes):
                guard()
                if 2000000-paid<524288:raise BudgetEnd('FULL_GAME_RESERVE_CAP')
                env=FixedScaleSessionEnv(GameSession(compiled),unit_type='A');before=list(model.weights)
                def observe(ply,actor,receipt):
                    nonlocal paid
                    paid+=receipt.nodes;assert model.weights==before
                    row=dict(episode=i,color=i%2,ply=ply,actor=actor,candidate_weights=before,
                        search_weights=list((model if actor==i%2 else foe).weights),**asdict(receipt))
                    queries.append(row);qout.write(json.dumps(row,default=str)+'\n');qout.flush()
                result=play_episode(env,model,opponent=foe,learner=TDLeafEpisode(),learner_color=i%2,
                    horizon=64,depth=depth,opponent_depth=2,query_nodes=8192,max_nodes=524288,
                    seconds=10,cancel=guard,on_query=observe,search_backend='mainline')
                row=dict(episode=i,color=i%2,before_weights=before,weights=list(model.weights),
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
        scope='Single-root deterministic mechanism evidence,not independent games or strength/transfer validation.')
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
