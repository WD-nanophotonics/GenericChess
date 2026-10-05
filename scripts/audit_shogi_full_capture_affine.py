"""Single frozen legal prefix/full one-ply collector, not alpha-beta."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.terminal import TerminalStatus
from scripts.shogi_full_affine_inventory import FullAffineInventory,robust_dominators,BOX
from scripts.research_state_replay import read_game_state
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/shogi_full_capture_affine_20261006.json'
SOURCES=('scripts/audit_shogi_full_capture_affine.py','scripts/shogi_full_affine_inventory.py',
 'docs/research/SHOGI_FULL_CAPTURE_AFFINE_PROTOCOL.md',
 'docs/research/data/shogi_full_board_search_20261006.json','scripts/resource_mode_context.py',
 'scripts/material_leaf_choice.py','scripts/shared_min_envelope_certificate.py',
 'generic_chess/core/search_runtime.py','generic_chess/core/semantic_executor.py')
PREFIX=((19,28),(55,46),(28,37),(46,37))

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('closed full-stock follow-up')
    start=monotonic();r=dict(complete=False,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
      prefix=[],leaves={},rows={},runtime_pushes=0,runtime_pops=0,candidates=0,returned_actions=0,
      prior_pushes=30,prior_charge=2005,new_preflight_charge=492,prior_seconds=.094,
      source_queries=0,public_transitions=0)
    push=SearchPathRuntime.push;pop=SearchPathRuntime.pop;legal=SearchPathRuntime.legal_actions
    candidates=SemanticEngine._iter_candidates;runtime=None
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
        return dict(position=record_value(runtime.position),ply_count=runtime.ply_count,
                    terminal_status=record_value(runtime.terminal_status))
    try:
        prior=json.loads((ROOT/SOURCES[3]).read_text());assert prior['complete'] and prior['source_hashes_unchanged']
        for path,pin in prior['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
        # Compilation's single preflight probe is accounted conservatively;
        # hooks start immediately after it, before runtime/prefix construction.
        compiled=compile_ruleset_for_execution(build_standard_shogi_ruleset())
        SearchPathRuntime.push=counted_push;SearchPathRuntime.pop=counted_pop
        SearchPathRuntime.legal_actions=counted_legal;SemanticEngine._iter_candidates=counted_candidates
        runtime=SearchPathRuntime(read_game_state(prior['root']),compiled)
        from fractions import Fraction as F
        evaluator=FullAffineInventory(compiled,{t:F(v) for t,v in prior['weights'].items()})
        initial=snapshot();r['box']=BOX;r['integer_weights']=evaluator.weights
        for source,target in PREFIX:
            matches=[a for a in runtime.legal_actions() if hasattr(a,'from_square') and
                a.from_square.rank*9+a.from_square.file==source and a.to_square.rank*9+a.to_square.file==target
                and a.promotion_target_id is None]
            assert len(matches)==1,'frozen prefix not uniquely legal'
            action=matches[0];runtime.push(action)
            assert runtime.terminal_status.status is TerminalStatus.ONGOING
            row=evaluator.row(runtime.state)
            r['prefix'].append(dict(action=str(action),state=snapshot(),row=row));write_record(OUT,r)
        r['root']=snapshot();r['root_row']=evaluator.row(runtime.state)
        actions=runtime.legal_actions();r['root_actions']=[str(a) for a in actions]
        assert actions and len(actions)<=64 and len(set(r['root_actions']))==len(actions)
        for action in actions:
            runtime.push(action)
            try:
                assert runtime.terminal_status.status is TerminalStatus.ONGOING,'terminal needs separate goal contract'
                r['rows'][str(action)]=evaluator.row(runtime.state)
                r['leaves'][str(action)]=snapshot();write_record(OUT,r)
            finally:runtime.pop()
        assert snapshot()==r['root']
        r['certificate']=robust_dominators(r['rows'],owner=runtime.position.side_to_move)
        r['complete']=len(r['rows'])==len(actions)
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    finally:
        if runtime is not None:
            while runtime.depth:runtime.pop()
            r['initial_restored']=snapshot()==initial
        SearchPathRuntime.push=push;SearchPathRuntime.pop=pop
        SearchPathRuntime.legal_actions=legal;SemanticEngine._iter_candidates=candidates
    r['cumulative_pushes']=r['prior_pushes']+r['runtime_pushes']
    r['conservative_enumeration_charge']=r['prior_charge']+r['new_preflight_charge']+r['candidates']+r['returned_actions']
    r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+r['prior_seconds']
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:record_value(v) for k,v in r.items() if k not in ('source_sha256','prefix','root','leaves','rows','certificate','integer_weights','root_actions')}))
