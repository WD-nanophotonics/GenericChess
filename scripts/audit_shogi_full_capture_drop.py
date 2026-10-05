"""Frozen full-stock capture/drop path under the remaining family budget."""
import hashlib,json,sys
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.actions import action_drop_base_type_id
from scripts.shogi_full_affine_inventory import FullAffineInventory
from scripts.research_state_replay import read_game_state
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/shogi_full_capture_drop_20261006.json'
SOURCES=('scripts/audit_shogi_full_capture_drop.py','docs/research/SHOGI_FULL_CAPTURE_DROP_PROTOCOL.md',
 'scripts/shogi_full_affine_inventory.py','docs/research/data/shogi_full_capture_affine_20261006.json',
 'docs/research/data/shogi_full_board_search_20261006.json','generic_chess/core/search_runtime.py',
 'generic_chess/core/semantic_executor.py')
PREFIX=((19,28),(55,46),(28,37),(46,37),(10,37),(None,19))

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('closed capture/drop path')
    start=monotonic();r=dict(complete=False,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
      path=[],runtime_pushes=0,runtime_pops=0,candidates=0,returned_actions=0,
      prior_pushes=66,prior_charge=3985,new_preflight_charge=492,prior_seconds=.359,
      source_queries=0,public_transitions=0)
    push=SearchPathRuntime.push;pop=SearchPathRuntime.pop;legal=SearchPathRuntime.legal_actions
    candidates=SemanticEngine._iter_candidates;runtime=None;initial=None
    def check():
        if monotonic()-start+r['prior_seconds']>=15:raise TimeoutError('cumulative15sec cap')
        if r['prior_charge']+r['new_preflight_charge']+r['candidates']+r['returned_actions']>5000:raise ValueError('cumulative5000 enumeration cap')
    def counted_candidates(self,*args,**kwargs):
        for item in candidates(self,*args,**kwargs):r['candidates']+=1;check();yield item
    def counted_legal(self,*args,**kwargs):
        actions=legal(self,*args,**kwargs);r['returned_actions']+=len(actions);check();return actions
    def counted_push(self,*args,**kwargs):
        check()
        if r['prior_pushes']+r['runtime_pushes']>=128:raise ValueError('cumulative128 attempted push cap')
        r['runtime_pushes']+=1;return push(self,*args,**kwargs)
    def counted_pop(self,*args,**kwargs):
        result=pop(self,*args,**kwargs);r['runtime_pops']+=1;return result
    def snapshot():
        return dict(position=record_value(runtime.position),ply_count=runtime.ply_count,terminal_status=record_value(runtime.terminal_status))
    try:
        prior=json.loads((ROOT/SOURCES[3]).read_text());opening=json.loads((ROOT/SOURCES[4]).read_text())
        for raw in (prior,opening):
            assert raw['complete'] and raw['source_hashes_unchanged']
            for path,pin in raw['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
        assert prior['cumulative_pushes']==66 and prior['conservative_enumeration_charge']==3985
        compiled=compile_ruleset_for_execution(build_standard_shogi_ruleset())
        SearchPathRuntime.push=counted_push;SearchPathRuntime.pop=counted_pop
        SearchPathRuntime.legal_actions=counted_legal;SemanticEngine._iter_candidates=counted_candidates
        runtime=SearchPathRuntime(read_game_state(opening['root']),compiled);initial=snapshot()
        evaluator=FullAffineInventory(compiled,{t:F(v) for t,v in opening['weights'].items()})
        for source,target in PREFIX:
            def matches(action):
                if not hasattr(action,'to_square') or action.to_square.rank*9+action.to_square.file!=target:return False
                if source is None:return action_drop_base_type_id(action)=='P'
                return hasattr(action,'from_square') and action.from_square.rank*9+action.from_square.file==source and action.promotion_target_id is None
            choices=[a for a in runtime.legal_actions() if matches(a)]
            assert len(choices)==1,'frozen path not uniquely legal'
            runtime.push(choices[0]);assert runtime.terminal_status.status is TerminalStatus.ONGOING
            row=evaluator.row(runtime.state)
            r['path'].append(dict(action=str(choices[0]),state=snapshot(),row=row));write_record(OUT,r)
        assert r['path'][-2]['row']==[0]*8 or tuple(r['path'][-2]['row'])==(0,)*8
        assert row==(-evaluator.weights['P'],1,0,0,0,0,0,0)
        r.update(drop_threshold=evaluator.weights['P'],final_row=row,complete=True)
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    finally:
        try:
            if runtime is not None:
                while runtime.depth:runtime.pop()
                r['initial_restored']=initial is not None and snapshot()==initial
        except Exception as error:r['cleanup_error']=f'{type(error).__name__}: {error}'
        finally:
            SearchPathRuntime.push=push;SearchPathRuntime.pop=pop
            SearchPathRuntime.legal_actions=legal;SemanticEngine._iter_candidates=candidates
    r['cumulative_pushes']=r['prior_pushes']+r['runtime_pushes']
    r['conservative_enumeration_charge']=r['prior_charge']+r['new_preflight_charge']+r['candidates']+r['returned_actions']
    r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+r['prior_seconds']
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:record_value(v) for k,v in r.items() if k not in ('source_sha256','path')}))
