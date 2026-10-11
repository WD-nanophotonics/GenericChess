"""Actual Core-owned caller: semantic attack backend and legality attribution."""
import argparse, hashlib, json, random, sys, time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import full_q_refresh_comparison as p
from scripts.research_record import record_value, write_record
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta import player as pm
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.native import semantic as ns
from scripts.native_core_availability import NativeCoreAvailability
from scripts.native_core_probe import NativeCoreProbe
from generic_chess.core import search_runtime as runtime_module

class CountedSemanticEvaluator(SemanticAttackEvaluator):
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw);self.score_calls=self.map_calls=0
    def evaluate(self,state):
        self.score_calls+=1;return super().evaluate(state)
    def _attack_maps(self,state):
        self.map_calls+=1;return super()._attack_maps(state)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    b=Path(args.output);b.mkdir(parents=True,exist_ok=True)
    if (b/'declaration.json').exists():raise RuntimeError('frozen output exists')
    modes=[('core-check',None),('separate-native',False),('shared-native',True)]
    declaration=dict(question='Does one identical ply0 child projection shared between check and availability reverse separate Native query loss?' ,roots=['1051-ply8','1052-ply8'],modes=modes,orders=2,depths=[2],q=4,hardq=8,nodes=100000,seconds=10,calls=12,expected_seconds='Maximum120searchseconds plus setup; expected3min; interruptible',decision='Complete equal-depth action/score/non-time work must match for evaluator backend attribution; any mismatch investigated without fitting. Both arms retain the same Native legal provider; only gave-check differs and complete non-time work must agree. Partial iterations are execution limits, not decision gains. No cap extension/default changes.',scope='Both arms use actual Native semantic attacks and Native legal provider, same weights, original Core history/precedence/order/TT. Same S0-S4 availability in both arms; only the readonly child check consumer differs. Actual public AlphaBetaPlayer, Core terminal/history/identity/declarations and fresh TT/ordering defaults. Previously observed1051-1052 roots; changed premise is shared exact Position ply0 projection for check and availability versus original Core check with seed+7000 walk; adaptive developmental transfer, no independent holdout claim; frozen identical weights/profile, explicit SEMANTIC attack authority. Not legacy evaluation equality or thin-capsule product integration.',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write_record(b/'declaration.json',declaration)
    roots=[];samples=[]
    for seed in (1051,1052):
        g=p.generate_game(p.GeneratorConfig(seed=seed,board_size=8,setup_preset='bilateral_random',allow_hybrid=True));src=p.compile_legacy_ruleset_for_semantic_execution(g.ruleset);c=p.SearchMetadataAdapter(ir=src.ir,_legacy_compiled=src._legacy_compiled,support=src.support);ec=p.EvaluationConfig();profile=p.build_ruleset_profile(c,ec);s=p.GameSession(c);rng=random.Random(seed+7000)
        for _ in range(8):
            if s.result.status.value != 'ongoing':break
            actions=sorted(s.legal_actions(),key=repr)
            if not actions:break
            s.submit(rng.choice(actions))
        if s.result.status.value != 'ongoing' or s.state.ply_count!=8:
            write_record(b/('unavailable-'+str(seed)+'.json'),dict(seed=seed,state=record_value(s.state),result=record_value(s.result),policy='No replacement root'));continue
        roots.append((seed,c,ec,profile,s));samples.append(dict(seed=seed,initial=record_value(s.state),witnesses=record_value(s._search_witnesses),profile=record_value(profile),config=record_value(ec)))
    write_record(b/'samples.json',samples)
    runtimes=[];captured=[];old_attach=SearchPathRuntime.attach_stats;old_stats=pm.SearchStatistics
    imports=queries=0;old_pack=ns.pack_current_position;old_attack=ns.attacked_squares
    def pack(*a,**kw):
        nonlocal imports;imports+=1;return old_pack(*a,**kw)
    def attack(*a,**kw):
        nonlocal queries;queries+=1;return old_attack(*a,**kw)
    def attach(rt,stats):
        v=old_attach(rt,stats);runtimes.append((rt,p.runtime_state(rt)));return v
    def factory():
        v=SearchStatistics();captured.append(v);return v
    rows=[];start=time.perf_counter()
    try:
        SearchPathRuntime.attach_stats=attach;pm.SearchStatistics=factory;ns.pack_current_position=pack;ns.attacked_squares=attack
        for seed,c,ec,profile,s in roots:
            legal=set(s.legal_actions());saved=s.state
            for depth in declaration['depths']:
                for order in range(2):
                    for backend,native in (modes if order==0 else list(reversed(modes))):
                        p.rr.stopped();runtimes.clear();captured.clear();imports=queries=0
                        t=time.perf_counter();ev=CountedSemanticEvaluator(c,profile,ec,backend='native');availability=NativeCoreAvailability(c) if native is None else NativeCoreProbe(c,shared=native);check=None if native is None else availability;player=AlphaBetaPlayer(c,evaluator_override=ev,use_native_semantic_legality=True,use_disk_cache=False,availability_provider=availability.for_position)
                        original_check=runtime_module.SearchPathRuntime._gave_check
                        def query_check(rt,position,checkpoint=None):
                            value=check.check(position,checkpoint=checkpoint)
                            return original_check(rt,position,checkpoint) if value is None else value
                        if check:runtime_module.SearchPathRuntime._gave_check=query_check
                        try:value=player.choose_action(s,SearchLimits(max_depth=depth,max_nodes=100000,max_time_seconds=10,quiescence_max_depth=4,quiescence_hard_max_depth=8))
                        finally:runtime_module.SearchPathRuntime._gave_check=original_check
                        elapsed=time.perf_counter()-t
                        assert len(runtimes)==len(captured)==1
                        rt,snapshot=runtimes[0];rt.assert_balanced();assert p.runtime_state(rt)==snapshot and s.state==saved and value.action in legal
                        row=dict(check_counts=None if check is None else dict(calls=check.check_calls,imports=check.imports,queries=check.check_queries,fallbacks=check.check_fallbacks,reuses=check.reuses,payload_seconds=check.payload_seconds,query_seconds=check.query_seconds),seed=seed,depth_requested=depth,order=order,attack_backend='native',native_legal_requested=True,check_mode=backend,availability_counts=None if availability is None else dict(calls=availability.calls,imports=availability.imports,queries=availability.queries,fallbacks=availability.fallbacks,payload_seconds=availability.payload_seconds,query_seconds=availability.query_seconds),provider_created=player.native_legality_provider is not None,caller_seconds=elapsed,score_calls=ev.score_calls,map_calls=ev.map_calls,actual_attack_imports=imports,actual_attack_queries=queries,decision=record_value(value),stats=record_value(captured[0]),root_restored=True)
                        rows.append(row);write_record(b/'result.json',dict(complete=False,rows=rows));print(seed,depth,order,backend,native,value.completed_depth,value.termination_reason,round(elapsed,3),value.score,flush=True)
    finally:
        SearchPathRuntime.attach_stats=old_attach;pm.SearchStatistics=old_stats;ns.pack_current_position=old_pack;ns.attacked_squares=old_attack
    write_record(b/'result.json',dict(complete=True,rows=rows,elapsed_seconds=time.perf_counter()-start))
if __name__=='__main__':main()
