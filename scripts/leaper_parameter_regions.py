"""Observer-only algebra on complete Core-generated Leaper graph caches.

This never generates a move or trains the experiential learner. Fresh-position
D1-D4 action SETS use cached authoritative transitions, with return to the fresh
root treated as repeat-two draw. Public-search checks remain separate.
"""
from collections import Counter,defaultdict
from fractions import Fraction
from itertools import combinations
import gzip,json,math,pickle,time
from pathlib import Path

from generic_chess.ai.evaluation.config import MATE_SCORE
from generic_chess.rules.compiler import compile_ruleset_for_execution
from scripts.leaper_microgames import role_stop_requested,Exhaustion
from scripts.leaper_retrograde import root_action_labels


def draw_only_closure(edges, terminals):
    """Vertices from which no decisive terminal is reachable by ANY policy.

    This is a complete-graph observer, not a rules/history quotient. In the
    scoped Leaper worlds, its forward-closed complement of terminal ancestors
    can only end in an actual draw or repeat-two draw, under any played prefix.
    A minimax DRAW alone is insufficient: a player might still blunder to mate.
    Resource-incomplete graphs must not be passed as if they were complete.
    """
    from collections import deque
    parents=[[]for _ in edges]
    for i,children in enumerate(edges):
        if not children and i not in terminals:
            raise ValueError('complete graph needs a label for every sink')
        for child in children:
            if not 0<=child<len(edges):raise ValueError('unexpanded graph child')
            parents[child].append(i)
    if any(i<0 or i>=len(edges)or v not in(-1,0,1)or edges[i]
           for i,v in terminals.items()):
        raise ValueError('invalid terminal vertex')
    decisive={i for i,v in terminals.items()if v}
    pending=deque(decisive)
    while pending:
        for parent in parents[pending.popleft()]:
            if parent not in decisive:
                decisive.add(parent);pending.append(parent)
    return frozenset(set(range(len(edges)))-decisive)


def material_vector(position):
    return tuple(sum((1 if p.owner==0 else -1)for p in position.board
                     if p and p.current_type_id==name)for name in('A','B','C'))


def tie_error_counts(scores, labels):
    """Exact uniform-tie observer error, not the deployed search tie policy.

    WDL labels must already be proved. Return a rational expected error and
    distinguish unavoidable errors from ties with both safe and unsafe moves.
    """
    if not scores or len(scores)!=len(labels)or any(v not in(-1,0,1)for v in labels):
        raise ValueError('complete scores and proved WDL labels required')
    top=max(scores);best=max(labels)
    selected=[v for s,v in zip(scores,labels)if s==top]
    bad=sum(v<best for v in selected)
    return dict(forced=bad==len(selected),unsafe=0<bad<len(selected),
                expected_error=Fraction(bad,len(selected)),choices=len(selected))


def uniform_tie_distance(scores, other_scores):
    """TV bound on error-expectation differences even with missing WDL labels."""
    if not scores or len(scores)!=len(other_scores):
        raise ValueError('matching nonempty action score vectors required')
    top,other_top=max(scores),max(other_scores)
    a={i for i,s in enumerate(scores)if s==top}
    b={i for i,s in enumerate(other_scores)if s==other_top}
    return 1-Fraction(len(a&b),max(len(a),len(b)))


def tie_study(output, *, regions, models_by_world, whole_seconds=300,depths=(1,2)):
    """Compare frozen models under uniform action-set ties on cached graphs.

    This is a post-hoc observer control. It neither reruns public queries nor
    substitutes an imagined randomized tie policy for actual deployed results.
    """
    from generic_chess.learning.incremental import Model
    if not depths or any(d not in(1,2,3,4)for d in depths):
        raise ValueError('tie observer depths must be D1-D4')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    regions=Path(regions);reference=json.loads((regions/'summary.json').read_text(encoding='utf-8'))
    began=time.perf_counter();rows=[];status='COMPLETE';last=0.
    config=dict(regions=str(regions),models=models_by_world,whole_seconds=whole_seconds,depths=depths,
        scope='All ongoing cached reachable Positions reset to fresh history; uniform random tie expectation,not actual search or game strength')
    (output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (output/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    def guard():
        nonlocal last
        now=time.perf_counter()
        if now-began>=whole_seconds:raise Exhaustion('WHOLE_TIME_UNKNOWN')
        if now-last>=.2:
            last=now
            if role_stop_requested():raise Exhaustion('STOPPED_USER')
    try:
      for world,models in models_by_world.items():
        g=pickle.loads(gzip.decompress(Path(reference['config']['caches'][world]).read_bytes()))
        labels={r['index']:r['values']for l in(regions/(world+'-labels.jsonl')).read_text(encoding='utf-8').splitlines()for r in(json.loads(l),)}
        phi=[material_vector(p)for p in g['positions']]
        for name,weights in models.items():
            guard();model=Model(weights[:3]);leaf=[model.raw(p)for p in phi]
            for depth in depths:
                counts=Counter();hist=Counter();expected=Fraction(0)
                for i,lab in labels.items():
                    guard();v=tie_error_counts(action_scores(g,i,leaf,depth),lab)
                    counts['positions']+=1;counts['forced']+=v['forced'];counts['unsafe']+=v['unsafe']
                    expected+=v['expected_error'];hist[str(v['expected_error'])]+=1
                rows.append(dict(world=world,model=name,depth=depth,**counts,
                    expected_errors=str(expected),expected_errors_float=float(expected),
                    expected_error_rate=float(expected)/len(labels),error_fraction_histogram=hist,
                    missing_positions=reference['worlds'][world]['ongoing']-len(labels),
                    full_domain_expected_error_bounds=[float(expected),float(expected)+reference['worlds'][world]['ongoing']-len(labels)]))
                (output/'partial.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
            print(world,name,'tie observer seconds',time.perf_counter()-began,flush=True)
    except Exhaustion as error:status=str(error)
    if status=='COMPLETE'and any(r['missing_positions']for r in rows):status='PARTIAL_LABELS'
    result=dict(config=config,status=status,rows=rows,planned=sum(len(depths)*len(m)for m in models_by_world.values()),
        recorded=len(rows),seconds=time.perf_counter()-began,new_search_queries=0)
    (output/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def action_scores(graph,root,leaf_scores,depth):
    """Player-to-move scores at a fresh history, at most four plies.

    Mate distances match public q0 scores. A board cannot recur in two plies:
    each player moves one of its own actors,with no pass/drop/promotion here.
    Thus the first possible recurrence is the root at ply4. D5+ could repeat
    a later vertex and needs a different full-history observer,not this cache.
    """
    if depth not in(1,2,3,4):raise ValueError('Only D1-D4 fresh-position algebra')
    sign=1 if graph['positions'][root].side_to_move==0 else -1
    def score(child,ply):
        if child in graph['terminals']:
            side=1 if graph['positions'][child].side_to_move==0 else -1
            return graph['terminals'][child]*side*(MATE_SCORE-ply)
        if child==root:return 0
        return leaf_scores[child]
    if depth>2:
        from functools import lru_cache
        @lru_cache(None)
        def value(index,left,ply):
            if index in graph['terminals']or index==root or not left:
                return score(index,ply)*sign
            choose=max if graph['positions'][index].side_to_move==graph['positions'][root].side_to_move else min
            return choose(value(c,left-1,ply+1)for c in graph['edges'][index])
        return tuple(value(c,depth-1,1)for c in graph['edges'][root])
    result=[]
    for child in graph['edges'][root]:
        if depth==1 or child in graph['terminals']:
            value=score(child,1)*sign
        else:
            # The opponent minimizes the root player's score.
            value=min(score(grandchild,2)*sign for grandchild in graph['edges'][child])
        result.append(value)
    return tuple(result)


def supervised_fit(histogram,*,scale=10.,low=0.,high=8.):
    """Explicit oracle supervised BCE control, NOT experiential learning.

    Target W/D/L is 1/.5/0. A=C=1; p=(1+tanh(material/scale))/2.
    Fixed feature histogram makes a convex one-parameter objective. Bisection
    finds its minimum on the declared interval; boundary optima stay boundaries.
    """
    n=sum(sum(counts.values())for counts in histogram.values())
    def objective(r):
        loss=derivative=0.
        for (a,b,c),counts in histogram.items():
            count=sum(counts.values());target=counts[1]+counts[0]/2
            z=2*(a+b*r+c)/scale
            p=1/(1+math.exp(-z))
            loss+=count*(max(z,0)+math.log1p(math.exp(-abs(z))))-target*z
            derivative+=(count*p-target)*2*b/scale
        return loss/n,derivative/n
    if objective(low)[1]>=0:r=low
    elif objective(high)[1]<=0:r=high
    else:
        lo,hi=low,high
        for _ in range(70):
            mid=(lo+hi)/2
            if objective(mid)[1]<0:lo=mid
            else:hi=mid
        r=(lo+hi)/2
    return dict(ratio=r,loss=objective(r)[0],derivative=objective(r)[1],
        bounds=[low,high],scale=scale,uniform_loss=objective(1)[0],
        interpretation='Oracle-supervised expected-outcome BCE on all ongoing fresh Positions; not TD, strength, calibration or intrinsic price')


def fresh_observer_session(graph,index):
    """Explicit constructed fresh-history observer, NOT a recovered old game.

    GameSession has no public arbitrary-position reset. This research-only
    construction replaces its state AND search witnesses together. Core still
    computes terminal/history authority; all moves/search use committed code.
    It must never be serialized as a replayable original-root game record.
    """
    from generic_chess.session.session import GameSession
    from scripts.leaper_retrograde import fresh_state
    session=GameSession(graph['compiled'])
    position=graph['positions'][index]
    session._state=fresh_state(position,graph['compiled'])
    session._search_history_witnesses=(position,)
    assert len(session.state.history)==1 and not session.history
    return session


def public_position_study(output,*,regions,whole_seconds=3600,
                          parameter_curve=False,reuse_uniform_from=None,
                          models_by_world=None):
    """Actual public q0 policies at ALL prior declared fresh observer Positions.

    Uniform, explicitly oracle-supervised and CLOSED experiential TD weights
    are frozen before calls. Ordering has no learned prices. A returned shallow
    iteration retains its actual quality but is not a completed target-depth
    result. No retry, training or newly selected positions after a cutoff.
    """
    import hashlib
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,BudgetEnd
    from generic_chess.learning.mainline_search import search
    regions=Path(regions);reference=json.loads((regions/'summary.json').read_text(encoding='utf-8'))
    assert reference['status']=='COMPLETE'
    if models_by_world is not None:
        assert not parameter_curve and reuse_uniform_from is None
        assert models_by_world and set(models_by_world)<=set(reference['worlds'])
        reference['worlds']={w:reference['worlds'][w]for w in models_by_world}
        reference['config']['caches']={w:reference['config']['caches'][w]for w in models_by_world}
        for models in models_by_world.values():
            assert models
            for weights in models.values():
                assert len(weights)==6 and weights[0]==1.
                Model(weights)  # Validate before starting the experiment.
    if reuse_uniform_from is not None:
        previous=json.loads((Path(reuse_uniform_from)/'summary.json').read_text(encoding='utf-8'))
        assert previous['status']=='COMPLETE'and previous['missing']==0
        assert previous['config']['regions']==str(regions)
        assert previous['config']['query_nodes']==100000 and previous['config']['query_seconds']==3
        assert all(m['uniform']==[1.]*6 for m in previous['config']['models'].values())
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    began=time.perf_counter();rows=[];worlds={};status='COMPLETE';last_stop_check=0.
    config=dict(regions=str(regions),whole_seconds=whole_seconds,query_nodes=100000,
        query_seconds=3,depths=[1,2],selection='ALL ongoing graph Positions;fresh observer histories;SHA index order independent of labels',
        models={},source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Constructed fresh observer GameSessions,not original-root legal histories or heldout/strength trials;supervised arm sees oracle aggregate,TD arm unchanged')
    for world,summary in reference['worlds'].items():
        if models_by_world is not None:
            config['models'][world]=models_by_world[world]
        elif parameter_curve:
            specs=[r['model']for r in summary['rows']if r['depth']==1 and r['model']['kind']in('open','boundary')]
            config['models'][world]={s['name']:[1.,s['ratio'],1.,1.,1.,1.]for s in specs}
        else:
            config['models'][world]={'uniform':[1.,1.,1.,1.,1.,1.],
                'oracle_supervised':[1.,summary['supervised']['ratio'],1.,1.,1.,1.],
                'closed_TD':[1.,.9900874213210581,.9659358144086714,1.,1.,1.]}
    config['parameter_curve']=parameter_curve
    config['reuse_uniform_from']=None if reuse_uniform_from is None else str(reuse_uniform_from)
    (output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (output/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    total=sum(s['ongoing']*2*len(config['models'][w])for w,s in reference['worlds'].items())
    def guard():
        nonlocal last_stop_check
        now=time.perf_counter()
        if now-began>=whole_seconds:raise BudgetEnd('WHOLE_TIME_UNKNOWN')
        if now-last_stop_check>=.2:
            last_stop_check=now
            if role_stop_requested():raise BudgetEnd('STOPPED_USER')
    try:
      for world,cache in reference['config']['caches'].items():
        guard();g=pickle.loads(gzip.decompress(Path(cache).read_bytes()))
        g['compiled']=compile_ruleset_for_execution(g['rules'])
        labels={r['index']:r['values']for line in(regions/(world+'-labels.jsonl')).read_text(encoding='utf-8').splitlines()for r in(json.loads(line),)}
        names=config['models'][world];counts=defaultdict(Counter);examples=[]
        indices=sorted(labels,key=lambda i:hashlib.sha256(f'{world}:{i}'.encode()).digest())
        worlds[world]=dict(planned=len(indices)*2*len(names),recorded=0,table={},examples=examples)
        old_stream=None
        if reuse_uniform_from is not None:
            old_stream=(Path(reuse_uniform_from)/(world+'-queries.jsonl')).open(encoding='utf-8')
            old_uniform=(r for line in old_stream for r in(json.loads(line),)if r[1]=='uniform')
        # Compact rows: index,model,requested/completed depth,nodes,seconds,
        # action index,exact chosen,exact best,PV features,terminal,PV squares,
        # scalar value,termination reason. Shapes are fixed by these Leaper rules.
        with(output/(world+'-queries.jsonl')).open('x',encoding='utf-8')as stream:
          for ordinal,index in enumerate(indices):
            guard();session=fresh_observer_session(g,index)
            env=FixedScaleSessionEnv(session,unit_type='A')
            local={}
            for model,full in names.items():
              weights=[full[{'A':0,'B':1,'C':2}[name]+(3 if kind=='hand'else 0)]for kind,name in env.names]
              for depth in(1,2):
                guard();remaining=whole_seconds-time.perf_counter()+began
                if remaining<=0:raise BudgetEnd('WHOLE_TIME_UNKNOWN')
                reused=old_stream is not None and model=='boundary:1'
                if reused:
                    row=list(next(old_uniform));assert(row[0],row[2])==(index,depth)
                    assert row[8]==g['values'][index]and(row[6]is None or row[7]==labels[index][row[6]])
                    row[1]=model;ai,chosen,best=row[6:9]
                else:
                    receipt=search(env,Model(weights),depth=depth,nodes=100000,
                        seconds=min(3,remaining),cancel=guard)
                    ai=g['actions'][index].index(receipt.action.action)if receipt.complete and receipt.action else None
                    chosen=None if ai is None else labels[index][ai];best=g['values'][index]
                    pv=[[c.action.from_square.file,c.action.from_square.rank,c.action.to_square.file,c.action.to_square.rank]for c in receipt.pv_choices]
                    row=[index,model,depth,receipt.completed_depth,receipt.nodes,receipt.seconds,
                        ai,chosen,best,receipt.pv_phi,receipt.pv_terminal,pv,receipt.value,receipt.reason]
                row=row[:14]+[reused]
                stream.write(json.dumps(row,separators=(',',':'))+'\n')
                key=f'{model}:D{depth}';stat=counts[key]
                stat['queries']+=1;stat['nodes']+=row[4]
                stat['new_nodes']+=0 if reused else row[4];stat['reused']+=reused
                stat['requested_complete']+=ai is not None and row[3]==depth
                stat['unknown']+=chosen is None;stat['errors']+=chosen is not None and chosen<best
                stat['seconds']+=row[5];local[model,depth]=(ai,chosen)
                worlds[world]['recorded']+=1
            stream.flush()
            if 'uniform'in names and 'closed_TD'in names and len(examples)<12 and any(local['uniform',d][1]!=local['closed_TD',d][1]for d in(1,2)):
                examples.append(dict(index=index,values={f'{m}:D{d}':v for(m,d),v in local.items()}))
            if ordinal%1000==0:
                worlds[world]['table']=dict(counts)
                partial=dict(status='RUNNING',planned=total,worlds=worlds,seconds=time.perf_counter()-began)
                (output/'partial.json').write_text(json.dumps(partial,indent=2),encoding='utf-8')
                print(world,'positions',ordinal,'seconds',time.perf_counter()-began,flush=True)
          worlds[world]['table']=dict(counts)
        if old_stream is not None:old_stream.close()
    except BudgetEnd as error:
        status=str(error)
        if worlds:worlds[world]['table']=dict(counts)
    result=dict(config=config,status=status,planned=total,worlds=worlds,
        recorded=sum(s['recorded']for s in worlds.values()),seconds=time.perf_counter()-began)
    result['missing']=total-result['recorded']
    (output/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def study(output,*,caches,whole_seconds=900,resume=False):
    output=Path(output);output.mkdir(parents=True,exist_ok=resume)
    elapsed=0.
    if resume:
        # Conservative original deadline: config was written just after start.
        # Include interruption/recovery time; never restart the original cap.
        elapsed=max(0.,time.time()-(output/'config.json').stat().st_mtime+1)
        previous=json.loads((output/'config.json').read_text(encoding='utf-8'))
        assert previous['whole_seconds']==whole_seconds
        assert previous['caches']=={k:str(v)for k,v in caches.items()}
    began=time.perf_counter()-elapsed;worlds={};status='COMPLETE'
    config=dict(caches={k:str(v)for k,v in caches.items()},whole_seconds=whole_seconds,
        depth=[1,2],parameter_range=[0,8],fixed_A_C=1,
        scope='All ongoing Positions reachable from each saved initial world,RESET to fresh history; not all arrangements,actual old histories or independent rules')
    if not resume:(output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (output/('executed-source-recovery.py'if resume else'executed-source.py')).write_bytes(Path(__file__).read_bytes())
    last_stop_check=0.
    def guard():
        nonlocal last_stop_check
        now=time.perf_counter()
        if now-began>=whole_seconds:raise Exhaustion('WHOLE_TIME_UNKNOWN')
        if now-last_stop_check>=.2:
            last_stop_check=now
            if role_stop_requested():raise Exhaustion('STOPPED_USER')
    try:
        for world,cache in caches.items():
            guard();g=pickle.loads(gzip.decompress(Path(cache).read_bytes()))
            g['compiled']=compile_ruleset_for_execution(g['rules'])
            active=[i for i,e in enumerate(g['edges'])if e]
            phi=[material_vector(p)for p in g['positions']]
            hist=defaultdict(Counter)
            for i in active:
                sign=1 if g['positions'][i].side_to_move==0 else -1
                hist[tuple(sign*x for x in phi[i])][g['values'][i]]+=1
            fitted=supervised_fit(hist)
            lines={(a+c,b)for i,(a,b,c)in enumerate(phi)if g['edges'][i]}
            cuts=sorted({Fraction(c-a,b-d)for(a,b),(c,d)in combinations(lines,2)
                if b!=d and 0<Fraction(c-a,b-d)<8})
            endpoints=[Fraction(0),*cuts,Fraction(8)]
            specs=[dict(name=f'open:{a}:{b}',ratio=float((a+b)/2),interval=[str(a),str(b)],kind='open')for a,b in zip(endpoints,endpoints[1:])]
            specs += [dict(name=f'boundary:{c}',ratio=float(c),kind='boundary')for c in cuts]
            specs += [dict(name='supervised_fit',ratio=fitted['ratio'],kind='supervised'),
                dict(name='closed_TD_projection',ratio=.9900874213210581,kind='projection'),
                dict(name='closed_TD_actual',ratio=.9900874213210581,C=.9659358144086714,kind='closed_experiential')]
            # Freeze exact root-action WDL once, independent of all parameters.
            labels={};changed=0;fallback=0
            label_path=output/(world+'-labels.jsonl')
            if resume and label_path.exists():
                for line in label_path.read_text(encoding='utf-8').splitlines():
                    record=json.loads(line);i=record['index'];labels[i]=tuple(record['values'])
                # Only a complete prior deterministic label pass is reusable.
                assert set(labels)==set(active)
                assert all(len(labels[i])==len(g['edges'][i])and max(labels[i])==g['values'][i]for i in active)
                changed=sum(labels[i]!=tuple(-g['values'][c]for c in g['edges'][i])for i in active)
                fallback=sum(g['values'][i]==1 and any(g['values'][c]==-1 and g['ranks'][c]>=g['ranks'][i]for c in g['edges'][i])for i in active)
            else:
              with label_path.open('x',encoding='utf-8')as stream:
               for number,i in enumerate(active):
                    guard();lab=root_action_labels(g,i)
                    values=tuple(lab[a]for a in g['actions'][i]);labels[i]=values
                    raw=tuple(-g['values'][c]for c in g['edges'][i])
                    changed+=values!=raw
                    fallback+=g['values'][i]==1 and any(g['values'][c]==-1 and g['ranks'][c]>=g['ranks'][i]for c in g['edges'][i])
                    stream.write(json.dumps(dict(index=i,values=values))+'\n')
                    if number%5000==0:print(world,'labelled',number,'seconds',time.perf_counter()-began,flush=True)
            rows=[]
            for spec in specs:
                guard();r=spec['ratio'];c=spec.get('C',1.)
                # Reuse the learner's actual summation, including this Python
                # version's compensated builtin sum. A hand-written a+b*r+c
                # can split algebraic ties by one ULP and misstate action SETS.
                from generic_chess.learning.incremental import Model
                model=Model([1.,r,c])
                leaf=[model.raw(p)for p in phi]
                for depth in(1,2):
                    counts=Counter();sizes=Counter();witnesses=[]
                    file_name=spec['name'].replace(':','_').replace('/','-')
                    with(output/(world+'-'+file_name+f'-D{depth}-sets.jsonl')).open('x',encoding='utf-8')as stream:
                        for i in active:
                            guard();scores=action_scores(g,i,leaf,depth);best=max(scores)
                            selected=tuple(k for k,s in enumerate(scores)if s==best)
                            wdl=[labels[i][k]for k in selected];exact=g['values'][i]
                            forced=max(wdl)<exact;unsafe=min(wdl)<exact==max(wdl)
                            counts['forced_errors']+=forced;counts['unsafe_ties']+=unsafe
                            counts['safe']+=min(wdl)==exact;sizes[len(selected)]+=1
                            if forced and len(witnesses)<3:witnesses.append(i)
                            stream.write(json.dumps([i,sum(1<<k for k in selected)])+'\n')
                    rows.append(dict(model=spec,depth=depth,positions=len(active),**counts,
                        optimal_set_sizes=sizes,forced_example_indices=witnesses))
                print(world,spec['name'],'done seconds',time.perf_counter()-began,flush=True)
            n=len(active);feature_majority_errors=n-sum(max(c.values())for c in hist.values())
            worlds[world]=dict(vertices=len(g['edges']),ongoing=n,
                fresh_relative_WDL=Counter(g['values'][i]for i in active),
                exact_action_labels_changed_from_naive=changed,full_root_attractors=fallback,
                feature_histogram=[dict(phi=p,wdl=c)for p,c in sorted(hist.items())],
                minimum_3class_errors_for_ANY_material_vector_function=feature_majority_errors,
                supervised=fitted,cuts=list(map(str,cuts)),rows=rows)
            (output/'partial.json').write_text(json.dumps(worlds,indent=2),encoding='utf-8')
    except Exhaustion as error:status=str(error)
    result=dict(config=config,status=status,worlds=worlds,seconds=time.perf_counter()-began,
        completed_worlds=len(worlds),missing_worlds=len(caches)-len(worlds))
    (output/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
