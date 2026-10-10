"""Finite diagnostic of exact root selection under narrowed child windows.

No product import, TT, qsearch, reductions or C replacement. Full-state board
adapters own semantics. Fail-soft estimates carry their bound relative to the
input window. Root canonical order is independent from traversal order. Exact
verification shares the original time/node cap and never installs a partial
candidate. This is a diagnostic algorithm, not a complete generic player.
"""
from dataclasses import dataclass
from time import perf_counter

INF = 10**12

@dataclass(frozen=True)
class Estimate:
    score: int
    bound: str
    pv: tuple

class Exhausted(Exception):
    pass


def root_search(board, depth, *, mode='verified', reverse=False, reverse_interior=False,
                canonical_key=lambda action: action, node_limit=100000,
                seconds=30):
    if mode not in ('full', 'unsafe', 'verified'):
        raise ValueError(mode)
    if depth < 1:
        raise ValueError('diagnostic requires a root action')
    start=perf_counter()
    work=dict(nodes=0, pushes=0, terminal_queries=0, legal_queries=0,
              cutoffs=0, root_completed=0, verifications=0)
    candidates=[]
    incumbent=None
    label=None
    action=None

    def visit(left, alpha, beta, ply):
        if work['nodes'] >= node_limit or perf_counter()-start >= seconds:
            raise Exhausted
        work['nodes']+=1;work['terminal_queries']+=1
        terminal=board.terminal(ply)
        if terminal is not None or left==0:
            return Estimate(terminal if terminal is not None else board.evaluate(), 'EXACT', ())
        work['legal_queries']+=1
        frontier=board.actions()
        if reverse_interior:
            frontier=list(reversed(frontier))
        if not frontier:
            raise ValueError('nonterminal node has no diagnostic actions')
        alpha_initial=alpha;beta_initial=beta
        best=-INF;pv=()
        for _,move in frontier:
            board.push(move);work['pushes']+=1
            try:
                child=visit(left-1,-beta,-alpha,ply+1)
            finally:
                board.pop()
            score=-child.score
            if score>best:
                best=score;pv=(move,*child.pv)
            alpha=max(alpha,best)
            if alpha>=beta:
                work['cutoffs']+=1
                break
        bound='UPPER' if best<=alpha_initial else 'LOWER' if best>=beta_initial else 'EXACT'
        return Estimate(best,bound,pv)

    def child_search(move, alpha, beta):
        board.push(move);work['pushes']+=1
        try:
            child=visit(depth-1,alpha,beta,1)
        finally:
            board.pop()
        return Estimate(-child.score,{'EXACT':'EXACT','UPPER':'LOWER','LOWER':'UPPER'}[child.bound],(move,*child.pv))

    try:
        if node_limit<1 or seconds<=0:
            raise Exhausted
        work['nodes']+=1;work['terminal_queries']+=1
        terminal=board.terminal(0)
        if terminal is not None:
            incumbent=Estimate(terminal,'EXACT',())
        else:
            work['legal_queries']+=1
            frontier=board.actions()
            if reverse:frontier=list(reversed(frontier))
            for candidate_label,move in frontier:
                estimate=child_search(move,-INF,INF if incumbent is None or mode=='full' else -incumbent.score)
                entry=dict(label=candidate_label,key=canonical_key(move),score=estimate.score,bound=estimate.bound,
                           nodes=work['nodes'],verified=False,installed=False)
                candidates.append(entry)
                preferred=incumbent is not None and canonical_key(move)<canonical_key(action)
                possible=(incumbent is None or estimate.score>incumbent.score or estimate.score==incumbent.score and preferred)
                if possible and mode=='verified' and estimate.bound!='EXACT':
                    work['verifications']+=1
                    entry['verification_start_nodes']=work['nodes']
                    estimate=child_search(move,-INF,INF)
                    if estimate.bound!='EXACT':
                        raise AssertionError('full window did not establish exact candidate')
                    entry.update(verified=True,exact_score=estimate.score)
                if incumbent is None or estimate.score>incumbent.score or estimate.score==incumbent.score and preferred:
                    if mode=='verified' and estimate.bound!='EXACT':
                        raise AssertionError('unverified incumbent')
                    incumbent=estimate;action=move;label=candidate_label;entry['installed']=True
                work['root_completed']+=1
        complete=True
    except Exhausted:
        complete=False
    if not board.restored():
        raise AssertionError('root not restored')
    return dict(move=label,action=action,score=None if incumbent is None else incumbent.score,
                pv=() if incumbent is None else incumbent.pv,
                bound=None if incumbent is None else incumbent.bound,
                completed_depth=depth if complete else 0,reason='completed_depth' if complete else 'budget',
                work=work,candidates=candidates,root_restored=True,wall_seconds=perf_counter()-start)
