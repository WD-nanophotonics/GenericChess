"""Research-only actual root-child cost observer; never a policy/solver.
Records literal root calls/windows/results. No Q or TT producer causal graph.
"""
import sys, time
from scripts import leaper_design as L
from generic_chess.ai.alphabeta import search as S


class RootCostObserver:
    def __init__(self, started, cap=2048):
        self.started, self.cap = started, cap
        self.events = []
        self.dropped = 0
        self.next_call = 0

    def __enter__(self):
        self.original = S.negamax
        original = self.original
        def observed(*args, **kwargs):
            ply = args[4] if len(args) > 4 else kwargs['ply']
            if ply != 1:
                return original(*args, **kwargs)
            parent = sys._getframe(1)
            root = parent.f_back
            # Only the production root's actual child_search call qualifies.
            if (parent.f_code.co_name != 'child_search' or
                    root.f_code.co_name != 'negamax' or root.f_locals['ply'] != 0):
                return original(*args, **kwargs)
            ctx = args[5] if len(args)>5 else kwargs['ctx']
            a = args[2] if len(args)>2 else kwargs['alpha']
            b = args[3] if len(args)>3 else kwargs['beta']
            self.next_call += 1
            event = dict(call_id=self.next_call,
                iteration=root.f_locals['depth'],
                action=L.record_value(root.f_locals['action']),
                move_index=root.f_locals['move_index'],
                root_alpha_before=root.f_locals['alpha'],
                root_beta_before=root.f_locals['beta'],
                root_best_before=root.f_locals['best'],
                root_best_action_before=L.record_value(root.f_locals['best_action']),
                child_entry_alpha=a, child_entry_beta=b,
                child_pv_node=kwargs.get('pv_node',True),
                start_seconds=time.perf_counter()-self.started,
                start_nodes=ctx.stats.nodes, start_qnodes=ctx.stats.qnodes,
                raw_return=None, root_negated_return=None, completed=False)
            try:
                result = original(*args, **kwargs)
                event.update(completed=True, raw_return=result.score,
                    root_negated_return=-result.score,
                    original_window_label=('UPPER' if result.score<=a else
                                           'LOWER' if result.score>=b else 'INTERIOR'),
                    child_pv=L.record_value(result.pv))
                return result
            except BaseException as exc:
                event['exception_type']=type(exc).__name__
                event['exception_message']=str(exc)
                raise
            finally:
                event.update(end_seconds=time.perf_counter()-self.started,
                    end_nodes=ctx.stats.nodes,end_qnodes=ctx.stats.qnodes)
                if len(self.events)<self.cap:
                    self.events.append(event)
                else:
                    self.dropped+=1
        S.negamax = observed
        return self

    def __exit__(self,*exc):
        S.negamax = self.original

    def result(self):
        return dict(events=self.events,cap=self.cap,dropped=self.dropped,
            root_child_calls=self.next_call,
            scope='Only actual ply1 calls from root child_search. Entry-window numerical bounds are not independent WDL/TT-producer proofs. Counts/times inclusive within each root call, disjoint root calls only may sum; no sum with total caller. Parent best captured before child return, not a certified subsequent promotion. No generated-unvisited label, no causal Q provenance.')
