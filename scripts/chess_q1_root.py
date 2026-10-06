"""Explicit research root operator; deliberately bypasses iterative reserve."""
from generic_chess.ai.alphabeta.search import _Context,_Budget,INF,quiescence
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime


def complete_q1_root(children,compiled,evaluator,checkpoint,remaining_seconds):
    """children is a caller-qualified COMPLETE root UCI->public-child map."""
    scores={};statistics={}
    for key,child in children.items():
        checkpoint()
        runtime=SearchPathRuntime.from_state(child,compiled)
        stats=SearchStatistics()
        limits=SearchLimits(max_depth=1,max_nodes=128,max_time_seconds=remaining_seconds(),
          quiescence_max_depth=1,quiescence_hard_max_depth=2,quiescence_max_nodes=128)
        ctx=_Context(compiled,evaluator,TranspositionTable(max_entries=16),stats,_Budget(limits,None),
          SearchTuning(),False,False,1,2,128,runtime=runtime,first_main_iteration_complete=None)
        before=(runtime.position,runtime.ply_count,runtime.terminal_status,tuple(runtime.history),runtime.repetition_counts,runtime.runtime_hash)
        scores[key]=-quiescence(child,-INF,INF,1,0,ctx)
        runtime.assert_balanced()
        if before!=(runtime.position,runtime.ply_count,runtime.terminal_status,tuple(runtime.history),runtime.repetition_counts,runtime.runtime_hash):
            raise ValueError('q1 root child not restored')
        statistics[key]=stats
    if not scores:raise ValueError('nonempty complete root required')
    best=max(scores.values());ties=sorted(k for k,v in scores.items() if v==best)
    return scores,ties,statistics
