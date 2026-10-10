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
    labels: tuple = ()

class Exhausted(Exception):
    pass


def _root_search(board, depth, *, mode='verified', reverse=False, reverse_interior=False,
                canonical_key=lambda action: action, node_limit=100000,
                seconds=30, cooperative=False, cancellation=None):
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

    def budget_check():
        if work['nodes'] >= node_limit:
            raise Exhausted('node_budget')
        if cancellation is not None and cancellation.is_cancelled():
            raise Exhausted('cancelled')
        if perf_counter()-start >= seconds:
            raise Exhausted('time_limit')

    def checkpoint():
        work['semantic_polls'] += 1
        budget_check()

    if cooperative:
        if not getattr(board, 'semantic_checkpoint_supported', False):
            raise ValueError('adapter does not support internal semantic checkpoints')
        work['semantic_polls'] = 0
        board.checkpoint = checkpoint

    def visit(left, alpha, beta, ply):
        budget_check()
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
        best=-INF;pv=();labels=()
        for candidate_label,move in frontier:
            board.push(move);work['pushes']+=1
            try:
                child=visit(left-1,-beta,-alpha,ply+1)
            finally:
                board.pop()
            score=-child.score
            if score>best:
                best=score;pv=(move,*child.pv);labels=(candidate_label,*child.labels)
            alpha=max(alpha,best)
            if alpha>=beta:
                work['cutoffs']+=1
                break
        bound='UPPER' if best<=alpha_initial else 'LOWER' if best>=beta_initial else 'EXACT'
        return Estimate(best,bound,pv,labels)

    def child_search(move, candidate_label, alpha, beta):
        board.push(move);work['pushes']+=1
        try:
            child=visit(depth-1,alpha,beta,1)
        finally:
            board.pop()
        return Estimate(-child.score,{'EXACT':'EXACT','UPPER':'LOWER','LOWER':'UPPER'}[child.bound],(move,*child.pv),(candidate_label,*child.labels))

    try:
        budget_check()
        work['nodes']+=1;work['terminal_queries']+=1
        terminal=board.terminal(0)
        if terminal is not None:
            incumbent=Estimate(terminal,'EXACT',())
        else:
            work['legal_queries']+=1
            frontier=board.actions()
            if reverse:frontier=list(reversed(frontier))
            for candidate_label,move in frontier:
                estimate=child_search(move,candidate_label,-INF,INF if incumbent is None or mode=='full' else -incumbent.score)
                entry=dict(label=candidate_label,key=canonical_key(move),score=estimate.score,bound=estimate.bound,
                           nodes=work['nodes'],verified=False,installed=False)
                candidates.append(entry)
                preferred=incumbent is not None and canonical_key(move)<canonical_key(action)
                possible=(incumbent is None or estimate.score>incumbent.score or estimate.score==incumbent.score and preferred)
                if possible and mode=='verified' and estimate.bound!='EXACT':
                    work['verifications']+=1
                    entry['verification_start_nodes']=work['nodes']
                    estimate=child_search(move,candidate_label,-INF,INF)
                    if estimate.bound!='EXACT':
                        raise AssertionError('full window did not establish exact candidate')
                    entry.update(verified=True,exact_score=estimate.score)
                if incumbent is None or estimate.score>incumbent.score or estimate.score==incumbent.score and preferred:
                    if mode=='verified' and estimate.bound!='EXACT':
                        raise AssertionError('unverified incumbent')
                    incumbent=estimate;action=move;label=candidate_label;entry['installed']=True
                work['root_completed']+=1
        complete=True
        exit_cause='completed_depth'
    except Exhausted as exc:
        complete=False
        exit_cause=str(exc)
    if not board.restored():
        raise AssertionError('root not restored')
    return dict(move=label,action=action,score=None if incumbent is None else incumbent.score,
                pv=() if incumbent is None else incumbent.pv,
                pv_labels=() if incumbent is None else incumbent.labels,
                bound=None if incumbent is None else incumbent.bound,
                completed_depth=depth if complete else 0,reason='completed_depth' if complete else 'budget',
                exit_cause=exit_cause,work=work,candidates=candidates,root_restored=True,wall_seconds=perf_counter()-start)


def root_search(board, depth, **kwargs):
    """Finite diagnostic with optional adapter-internal live budget checks.

    Only Core adapters currently propagate ``checkpoint`` inside semantic work.
    A checkpoint attribute alone does not establish Native/library cooperation.
    Node/cancel/time precedence matches the product; node units remain different.
    Restore callback ownership after successful, exhausted or exceptional work.
    """
    previous = getattr(board, 'checkpoint', None)
    try:
        return _root_search(board, depth, **kwargs)
    finally:
        if hasattr(board, 'checkpoint'):
            board.checkpoint = previous
