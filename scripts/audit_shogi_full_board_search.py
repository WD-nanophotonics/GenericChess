"""One frozen initial full-stock production integration control."""
import hashlib,json,sys
from pathlib import Path
from dataclasses import asdict
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.core.transition import initial_state
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.shogi_full_board_inventory import FullBoardInventory
from scripts.shogi_static_inventory import StaticInventory
from scripts.shogi_exact_contact_family import exact_board_means
from scripts.research_record import record_value,write_record
OUT=ROOT/'docs/research/data/shogi_full_board_search_20261006.json'
SOURCES=('scripts/audit_shogi_full_board_search.py','scripts/shogi_full_board_inventory.py',
 'docs/research/SHOGI_FULL_BOARD_SEARCH_PROTOCOL.md','scripts/resource_mode_context.py',
 'scripts/shogi_static_inventory.py','scripts/shogi_exact_contact_family.py',
 'docs/research/data/shogi_full_contact_distance_20261005.json',
 'docs/research/data/shogi_coordinate_comparison_20261005.json',
 'generic_chess/rules/standard_shogi.py','generic_chess/core/search_runtime.py',
 'generic_chess/core/semantic_executor.py','generic_chess/ai/alphabeta/search.py')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('closed initial-state control')
    start=monotonic();r=dict(complete=False,runtime_pushes=0,runtime_pops=0,
      candidates=0,returned_actions=0,evaluations=[],public_transitions=0,source_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    push=SearchPathRuntime.push;pop=SearchPathRuntime.pop;legal=SearchPathRuntime.legal_actions
    candidates=SemanticEngine._iter_candidates
    def check():
        if monotonic()-start>=15:raise TimeoutError('whole15sec cap')
        if r['candidates']+r['returned_actions']>5000:raise ValueError('whole5000 enumeration cap')
    def counted_candidates(self,*args,**kwargs):
        for item in candidates(self,*args,**kwargs):
            r['candidates']+=1;check();yield item
    def counted_legal(self,*args,**kwargs):
        check();actions=legal(self,*args,**kwargs);r['returned_actions']+=len(actions);check();return actions
    def counted_push(self,*args,**kwargs):
        check()
        if r['runtime_pushes']>=128:raise ValueError('128 attempted push cap')
        r['runtime_pushes']+=1;return push(self,*args,**kwargs)
    def counted_pop(self,*args,**kwargs):
        result=pop(self,*args,**kwargs);r['runtime_pops']+=1;return result
    try:
        c=compile_ruleset_for_execution(build_standard_shogi_ruleset());root=initial_state(c)
        before=record_value(root);means=exact_board_means('geometric_half')
        weights={t:v/means['TR'] for t,v in means.items()};e=FullBoardInventory(c,weights)
        r.update(root=before,weights=weights,integer_weights=e.weights,root_score=e.evaluate(root))
        assert r['root_score']==0
        try:StaticInventory({t:weights[t] for t in ('P','TP','R')}).evaluate(root)
        except ValueError as error:r['old_guard']=str(error)
        else:raise AssertionError('old partial-stock guard should reject full root')
        evaluate=e.evaluate
        def counted_evaluate(state):
            check();value=evaluate(state);r['evaluations'].append(value)
            assert value==0,'initial one-ply inventory should stay balanced'
            return value
        e.evaluate=counted_evaluate
        write_record(OUT,r)
        SearchPathRuntime.push=counted_push;SearchPathRuntime.pop=counted_pop
        SearchPathRuntime.legal_actions=counted_legal;SemanticEngine._iter_candidates=counted_candidates
        stats=SearchStatistics()
        action,score,pv,reason=run_root_search(root,c,e,TranspositionTable(max_entries=16),
          SearchLimits(max_depth=1,max_nodes=128,max_time_seconds=max(.001,15-(monotonic()-start)),quiescence_max_depth=0),
          None,stats,use_tt=False,use_ordering=False,tuning=SearchTuning(use_root_tactical=False))
        r.update(selected=str(action),score=score,pv=[str(a) for a in pv],reason=reason,
          statistics=asdict(stats),evaluation_calls=e.calls,root_unchanged=record_value(root)==before)
        assert reason=='completed_depth' and stats.completed_depth==1 and stats.qnodes==0
        assert score==0 and r['root_unchanged'] and r['runtime_pushes']==r['runtime_pops']
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    finally:
        SearchPathRuntime.push=push;SearchPathRuntime.pop=pop
        SearchPathRuntime.legal_actions=legal;SemanticEngine._iter_candidates=candidates
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r)
    print(json.dumps({k:record_value(v) for k,v in r.items() if k not in ('root','weights','integer_weights','source_sha256','statistics','evaluations')}))
