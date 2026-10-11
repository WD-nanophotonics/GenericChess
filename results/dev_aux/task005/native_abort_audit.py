"""Count actual extension calls and accepted provider frontiers on cancellation."""
import sys,time,json,hashlib,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from scripts import search_backend_comparison as b
from scripts.reserve_refresh_diagnostic import stopped
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider as P
from generic_chess.ai.alphabeta.search import SearchAborted
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.core.search_runtime import SearchPathRuntime as R
from generic_chess.native import _module
from generic_chess.native import semantic as ns
from scripts.research_record import record_value
mod=_module();native_call=mod.semantic_transient_legal_actions;pack_call=ns.pack_position
counts=collections.Counter()
def native(*args,**kwargs):
    counts['C_generation_entries']+=1
    result=native_call(*args,**kwargs);counts['C_generation_returns']+=1;return result
def pack(*args,**kwargs):
    counts['pack_wrapper_entries']+=1
    result=pack_call(*args,**kwargs);counts['pack_wrapper_returns']+=1;return result
class Poll:
    def __init__(self,target):self.target=target;self.calls=0;self.hit=False
    def __call__(self):
        self.calls+=1
        if self.target is not None and self.calls==self.target:
            self.hit=True;raise SearchAborted('DEV_AUX declared checkpoint cancellation')
def snapshot(r):
    return (r.position,r.ply_count,r.terminal_status,r.current_identity,r.runtime_hash,r._snapshot,tuple(r.history),r._history_context,tuple(r.repetition_counts.items()),len(r._frames))
start=time.monotonic();compiled=b.compile_ruleset_for_execution(b.build_builtin_ruleset('western_chess'));board=b.CoreBoard(b.CASES[0],compiled)
expected=set(board.runtime.legal_actions());rows=[]
try:
    mod.semantic_transient_legal_actions=native;ns.pack_position=pack
    for strict in (False,True):
        for target in (1,2,3,4,5,6,7,None):
            stopped();assert time.monotonic()-start<120
            provider=P.try_create(compiled,strict=strict);assert provider is not None
            rt=R.from_state(board.initial,compiled,history_witnesses=board.witnesses,legal_binding_provider=provider)
            stats=SearchStatistics();rt.attach_stats(stats);before=snapshot(rt);poll=Poll(target);counts=collections.Counter();returned=None;aborted=False
            try:returned=rt.legal_actions(poll)
            except SearchAborted as exc:
                assert 'DEV_AUX declared' in str(exc);aborted=True
            assert snapshot(rt)==before and rt._legal_provider_active
            assert rt.legal_provider_fallbacks==rt.legal_provider_operational_failures==0
            if aborted:assert rt._legal_cache is None and not rt._bindings
            else:assert set(returned)==expected
            assert aborted==poll.hit
            first={'aborted':aborted,'polls':poll.calls,'actual':dict(counts),'accepted_frontiers':rt.legal_provider_calls,'accepted_actions':rt.legal_provider_actions,'stats_calls':stats.native_legality_calls,'metrics_actions':provider.last_call_metrics.get('actions'),'partial_frontier_installed':aborted and rt._legal_cache is not None,'fallbacks':rt.legal_provider_fallbacks,'operational_failures':rt.legal_provider_operational_failures}
            assert first['accepted_frontiers']==first['stats_calls']
            if target in (4,5,6,7):assert counts['C_generation_returns']==1 and first['accepted_frontiers']==0
            recovery=None
            if aborted:
                counts=collections.Counter();actions=rt.legal_actions()
                assert set(actions)==expected and snapshot(rt)==before and rt._legal_provider_active
                assert rt.legal_provider_calls==1 and rt.legal_provider_fallbacks==rt.legal_provider_operational_failures==0
                recovery={'actual':dict(counts),'accepted_frontiers':rt.legal_provider_calls,'legal_actions':len(actions),'balanced':True}
            rows.append({'strict':strict,'target_poll':target,'first':first,'recovery':recovery,'strong_semantic_restoration':True})
finally:mod.semantic_transient_legal_actions=native_call;ns.pack_position=pack_call
fault_rows=[]
try:
    mod.semantic_transient_legal_actions=native;ns.pack_position=pack
    for strict in (False,True):
        stopped();assert time.monotonic()-start<120
        provider=P.try_create(compiled,strict=strict);assert provider is not None
        rt=R.from_state(board.initial,compiled,history_witnesses=board.witnesses,legal_binding_provider=provider)
        stats=SearchStatistics();rt.attach_stats(stats);before=snapshot(rt);counts=collections.Counter();raised=False;returned=None
        decoder=provider._decode_action
        def fail_decode(*args,**kwargs):raise ValueError('DEV_AUX declared decode fault')
        provider._decode_action=fail_decode
        try:
            try:returned=rt.legal_actions()
            except ValueError as exc:
                assert 'DEV_AUX declared decode fault' in str(exc);raised=True
            assert snapshot(rt)==before and counts['C_generation_returns']==1 and rt.legal_provider_calls==0
            assert raised==strict
            if not strict:assert set(returned)==expected and rt.legal_provider_fallbacks==rt.legal_provider_operational_failures==1 and not rt._legal_provider_active
            else:assert rt.legal_provider_fallbacks==rt.legal_provider_operational_failures==0 and rt._legal_provider_active
            fault_rows.append({'strict':strict,'actual':dict(counts),'accepted_frontiers':rt.legal_provider_calls,'stats_enabled':stats.native_legality_enabled,'stats_calls':stats.native_legality_calls,'fallbacks':rt.legal_provider_fallbacks,'operational_failures':rt.legal_provider_operational_failures,'propagated':raised,'provider_active':rt._legal_provider_active,'root_restored':True})
        finally:provider._decode_action=decoder
finally:mod.semantic_transient_legal_actions=native_call;ns.pack_position=pack_call

report={'complete':True,'scope':'actual installed C-generation entries/returns versus accepted provider-frontier counters at16declared checkpoints; no timing','source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'generic_chess/core/search_runtime.py',ROOT/'generic_chess/ai/alphabeta/native_legality.py')},'rows':rows,'fault_rows':fault_rows}
(Path(__file__).parent/'native_abort_counts.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{'strict':r['strict'],'poll':r['target_poll'],'C':r['first']['actual'].get('C_generation_returns',0),'accepted':r['first']['accepted_frontiers'],'aborted':r['first']['aborted'],'metrics_actions':r['first']['metrics_actions']} for r in rows],indent=2))
