"""Bounded actual iterative-search versus frozen complete-tree reference."""
import hashlib,json,sys
from pathlib import Path
from fractions import Fraction as F
from time import monotonic
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.shogi_static_inventory import StaticInventory,SCALE
from scripts.shogi_exact_contact_family import exact_board_means
from scripts.research_state_replay import read_game_state
from scripts.research_record import record_value,write_record
OUT=ROOT/'docs/research/data/shogi_static_search_20261006.json'
SOURCES=('scripts/audit_shogi_static_search.py','scripts/shogi_static_inventory.py','docs/research/SHOGI_STATIC_SEARCH_PROTOCOL.md','docs/research/data/shogi_promotion_use_20261005.json','scripts/shogi_exact_contact_family.py','generic_chess/core/search_runtime.py','generic_chess/core/semantic_executor.py','generic_chess/ai/alphabeta/search.py','generic_chess/ai/alphabeta/tuning.py')

def full_reference(raw,evaluator):
    values={key:min(evaluator.evaluate(read_game_state(leaf['state'])) for leaf in branch['leaves'].values()) for key,branch in raw['branches'].items()}
    best=max(values.values());return best,sorted(k for k,v in values.items() if v==best),values

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('closed audit not rerun')
    start=monotonic();r=dict(complete=False,searches=[],runtime_pushes=0,runtime_pops=0,public_transitions=0,source_queries=0,candidates=0,returned_actions=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    push=SearchPathRuntime.push;pop=SearchPathRuntime.pop;legal=SearchPathRuntime.legal_actions;candidates=SemanticEngine._iter_candidates;stack=[];current=None
    def check():
        if monotonic()-start>=15:raise TimeoutError('whole15sec cap')
        if r['candidates']+r['returned_actions']>5000:raise ValueError('whole5000 enumeration cap')
    def counted_candidates(self,*args,**kwargs):
        for item in candidates(self,*args,**kwargs):
            check();r['candidates']+=1
            if r['candidates']+r['returned_actions']>5000:raise ValueError('candidate cap')
            yield item
    def counted_legal(self,*args,**kwargs):
        check();actions=legal(self,*args,**kwargs);r['returned_actions']+=len(actions);check();return actions
    def counted_push(self,action,*args,**kwargs):
        check()
        if r['runtime_pushes']>=128:raise ValueError('128 runtime-push cap')
        r['runtime_pushes']+=1;result=push(self,action,*args,**kwargs);stack.append(str(action));path=tuple(stack)
        expected=saved[path]
        assert record_value(self.position)==expected['position'] and self.ply_count==expected['ply_count'] and record_value(self.terminal_status)==expected['terminal_status']
        current['visited'].append(list(path));return result
    def counted_pop(self,*args,**kwargs):
        result=pop(self,*args,**kwargs);stack.pop();r['runtime_pops']+=1;return result
    try:
        raw=json.loads((ROOT/SOURCES[3]).read_text());assert raw['complete'] and raw['public_transitions']==48
        saved={}
        for key,branch in raw['branches'].items():
            saved[key,]=branch['state']
            for reply,leaf in branch['leaves'].items():saved[key,reply]=leaf['state']
        compiled=compile_ruleset_for_execution(build_standard_shogi_ruleset());root=read_game_state(raw['root'])
        means=exact_board_means('geometric_half');weights={t:means[t]/means['TR'] for t in ('P','TP','R')}
        r['scale']=SCALE;r['contact_weights']=weights;r['leaf_error_bound']=F(1,SCALE);r['pairwise_error_bound']=F(2,SCALE)
        assert all(abs(F(StaticInventory(weights).weights[t],SCALE)-v)<=F(1,2*SCALE) for t,v in weights.items())
        SearchPathRuntime.push=counted_push;SearchPathRuntime.pop=counted_pop;SearchPathRuntime.legal_actions=counted_legal;SemanticEngine._iter_candidates=counted_candidates
        for name,vector in (('geometric_half',weights),('unit',{t:F(1) for t in weights})):
            check();evaluator=StaticInventory(vector);best,ties,values=full_reference(raw,evaluator);evaluator.calls=0
            assert ties==raw['selections_before_goal'][name]['tie_set']
            current=dict(law=name,reference_score=best,ties=ties,branch_minima=values,integer_weights=evaluator.weights,visited=[],complete=False);r['searches'].append(current);write_record(OUT,r)
            stats=SearchStatistics()
            action,score,pv,reason=run_root_search(root,compiled,evaluator,TranspositionTable(max_entries=16),SearchLimits(max_depth=2,max_nodes=128,max_time_seconds=max(0.001,15-(monotonic()-start)),quiescence_max_depth=0),None,stats,use_tt=False,use_ordering=False,tuning=SearchTuning(use_root_tactical=False))
            current.update(selected=str(action),score=score,pv=[str(a) for a in pv],reason=reason,statistics=asdict(stats),evaluation_calls=evaluator.calls)
            assert reason=='completed_depth' and stats.completed_depth==2 and stats.qnodes==0 and not stats.root_scan_used_fallback
            assert score==best and str(action) in ties and not stack
            current['complete']=True;write_record(OUT,r)
        assert r['runtime_pushes']==r['runtime_pops'];r['complete']=len(r['searches'])==2
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    finally:
        SearchPathRuntime.push=push;SearchPathRuntime.pop=pop;SearchPathRuntime.legal_actions=legal;SemanticEngine._iter_candidates=candidates
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items());write_record(OUT,r);print(json.dumps({k:record_value(v) for k,v in r.items() if k not in ('searches','source_sha256')}))
