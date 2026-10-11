"""Prospective bounded comparison of a diagnostic full-q shallow refresh.
No product/default changes. Samples and limits are fixed before search results.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, random, sys, time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.research_record import record_value,write_record
from scripts import reserve_refresh_diagnostic as rr
from generic_chess.ai.alphabeta import player as pm
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.generation.generator import generate_game
from generic_chess.generation.config import GeneratorConfig
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.session.session import GameSession
class SearchMetadataAdapter(CompiledSemanticRuleset):
    """Read-only legacy geometry metadata; semantic runtime remains authority."""
    __slots__=()
    def __getattr__(self,name):return getattr(self._legacy_compiled,name)
    @property
    def semantic(self):return self

def runtime_state(rt):
    occurrences=frozenset(collections.Counter((h,e.identity,int(e.count)) for h,b in rt._occurrences.items() for e in b).items())
    return (rt.position,rt.ply_count,rt.terminal_status,rt.current_identity,rt.runtime_hash,rt._snapshot,tuple(rt.history),rt._history_context,occurrences,frozenset(rt._opaque_imported_keys),frozenset(rt._history_aliases.items()))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--seconds',type=float,default=4)
    args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    if (out/'declaration.json').exists():raise RuntimeError('Do not overwrite frozen experiment')
    rr.POLICY_SOURCES['clear']=rr.MODIFIED.replace('ctx.qdepth_limit = min(1, original_q)','ctx.qdepth_limit = original_q')
    declaration=dict(question='Does full configured shallowq4 displace completed depth on prospective unfamiliar roots?',seeds=list(range(1001,1009)),board_sizes='odd seed4, even seed8',setup='bilateral_random',hybrid=True,roots=[0,8],walk='Random(seed+7000), repr-sorted public legal action at each ply; no resampling terminal or unavailable roots',seconds=args.seconds,max_nodes=1000000,max_depth=12,q=4,hardq=8,orders=2,arms=['baseline','fullq4_refresh'],backends=['Core','Native requested, record actual'],max_calls=128,expected_max_search_seconds=128*args.seconds,decision='Depth loss or refresh abort can reject unconditional adoption. q support alone is not strength. Defaults unchanged; no post-result budget extension.',scope='Generated legacy movement mixes compiled to semantic IR with read-only metadata adapter; complete domain target retained, tested generator cohort only. Full default profile evaluator frozen per ruleset. New seed selection prospective, not claimed untouched universal validation or human holdout.',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),refresh_sha256=hashlib.sha256(rr.POLICY_SOURCES['clear'].encode()).hexdigest())
    write_record(out/'declaration.json',declaration)
    samples=[];roots=[];setup_start=time.perf_counter()
    for seed in declaration['seeds']:
        rr.stopped();cfg=GeneratorConfig(seed=seed,board_size=4 if seed%2 else 8,setup_preset='bilateral_random',allow_hybrid=True)
        g=generate_game(cfg);source=compile_legacy_ruleset_for_semantic_execution(g.ruleset)
        c=SearchMetadataAdapter(ir=source.ir,_legacy_compiled=source._legacy_compiled,support=source.support)
        ec=EvaluationConfig();profile=build_ruleset_profile(c,ec);ev=Evaluator(c,profile,ec)
        s=GameSession(c);rng=random.Random(seed+7000);walk=[]
        for ply in range(9):
            actions=tuple(s.legal_actions())
            if ply in declaration['roots']:
                name=f'seed{seed}-ply{ply}';entry=dict(root=name,seed=seed,ply=ply,config=record_value(cfg),ruleset=json.loads(serialize_ruleset(g.ruleset)),fingerprint=c.ruleset_fingerprint,initial=record_value(s.state),witnesses=record_value(s._search_history_witnesses),walk=walk.copy(),evaluation_config=record_value(ec),profile=record_value(profile),legal_count=len(actions),included=bool(actions))
                samples.append(entry)
                if actions:roots.append((name,c,s.state,s._search_history_witnesses,ev,actions))
            if ply==8:break
            if not actions:
                samples.append(dict(seed=seed,unavailable_ply=8,terminal_at_ply=ply,resampled=False));break
            action=rng.choice(sorted(actions,key=repr));walk.append(record_value(action));s.submit(action)
    write_record(out/'samples.json',dict(setup_wall=time.perf_counter()-setup_start,samples=samples))
    rows=[];runtimes=[];captured=[];oa=SearchPathRuntime.attach_stats;of=pm.SearchStatistics;original=pm.run_root_search
    def attach(rt,stats):
        value=oa(rt,stats);runtimes.append((rt,runtime_state(rt)));return value
    def factory():
        stats=SearchStatistics();captured.append(stats);return stats
    try:
        SearchPathRuntime.attach_stats=attach;pm.SearchStatistics=factory
        for name,c,initial,witnesses,ev,legal in roots:
            for order in range(2):
                for native in ((False,True) if order==0 else (True,False)):
                    for arm in (('baseline','fullq4_refresh') if order==0 else ('fullq4_refresh','baseline')):
                        rr.stopped();events=[];runtimes.clear();captured.clear()
                        pm.run_root_search=original if arm=='baseline' else rr.make_refresh(events,expected_state=initial)
                        p=AlphaBetaPlayer(c,evaluator_override=ev,use_native_semantic_legality=native,use_disk_cache=False)
                        session=SimpleNamespace(compiled=c,state=initial,_search_witnesses=witnesses)
                        t=time.perf_counter();value=p.choose_action(session,SearchLimits(max_depth=12,max_nodes=1000000,max_time_seconds=args.seconds,quiescence_max_depth=4,quiescence_hard_max_depth=8));wall=time.perf_counter()-t
                        assert len(runtimes)==len(captured)==1;rt,snapshot=runtimes[0];rt.assert_balanced();assert runtime_state(rt)==snapshot and session.state is initial and value.action in legal
                        assert len({e['budget_identity'] for e in events})<=1 and len({e['deadline'] for e in events})<=1
                        rows.append(dict(root=name,order=order,native_requested=native,arm=arm,seconds=args.seconds,wall=wall,decision=record_value(value),stats=record_value(captured[0]),events=events,root_restored=True))
                        write_record(out/'result.json',dict(complete=False,rows=rows));print(name,order,native,arm,value.completed_depth,value.result_ordinary_qdepth,value.score,round(wall,3),flush=True)
        write_record(out/'result.json',dict(complete=True,rows=rows))
    finally:SearchPathRuntime.attach_stats=oa;pm.SearchStatistics=of;pm.run_root_search=original
if __name__=='__main__':main()