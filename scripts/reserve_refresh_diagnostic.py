"""Protected tactical refresh diagnostic; no production policy changes.
Uses one original run_root_search budget and a completed cheap D1 reserve.
An isolated q1 D1 recomputation follows; partial refresh never replaces reserve.
The default clear policy empties TT around q1. Opt-in phase_bypass disables
TT in cheap-q0/q1 and retains configured-q entries for deeper iterations.
Retained warm bounds have a selective contract, not finite-horizon equality.
"""
from __future__ import annotations
import argparse,hashlib,inspect,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.research_record import record_value,write_record
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta import search
from generic_chess.ai.alphabeta import player as player_module
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig,config_hash
from generic_chess.ai.evaluation.profile import PieceValueProfile,RuleSetEvaluationProfile
import chess
def uci(a):
    return chess.square_name(chess.square(a.from_square.file,a.from_square.rank))+chess.square_name(chess.square(a.to_square.file,a.to_square.rank))+(a.promotion_target_id or '').lower()
from scripts.search_backend_comparison import CASES,CoreBoard
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game

ORIGINAL=search.run_root_search
SOURCE=inspect.getsource(ORIGINAL)
ANCHOR="""        if progress_callback is not None:
            progress_callback(depth, stats.nodes, stats.qnodes)
"""
REFRESH="""        if depth == 1 and ctx.qdepth_limit > 0 and best.declaration is None:
            _refresh_log('reserve', ctx, best)
            original_q, original_tt = ctx.qdepth_limit, ctx.use_tt
            if not _naive_tt:
                ctx.tt.clear()
                ctx.use_tt = False
            ctx.qdepth_limit = min(1, original_q)
            _refresh_log('begin', ctx, best)
            try:
                # RHS assignment is essential: an abort retains complete reserve.
                refreshed = negamax(state, 1, -INF, INF, 0, ctx)
                _refresh_log('complete', ctx, refreshed)
                best = refreshed
            except SearchAborted as exc:
                _refresh_log('aborted', ctx, best, str(exc))
                abort_reason = str(exc)
                break
            finally:
                ctx.qdepth_limit = original_q
                ctx.use_tt = original_tt
                if not _naive_tt:
                    ctx.tt.clear()
"""
assert SOURCE.count(ANCHOR)==1
MODIFIED=SOURCE.replace(ANCHOR,ANCHOR+REFRESH)
PHASE_REFRESH=REFRESH.replace('''            if not _naive_tt:
                ctx.tt.clear()
                ctx.use_tt = False''','''            ctx.use_tt = False''').replace(
    'ctx.use_tt = original_tt','ctx.use_tt = use_tt').replace('''                if not _naive_tt:
                    ctx.tt.clear()''','')
PHASE_MODIFIED=SOURCE.replace(ANCHOR,ANCHOR+PHASE_REFRESH)
ITERATION='    for depth in range(1, max_depth + 1):'
assert PHASE_MODIFIED.count(ITERATION)==1
PHASE_MODIFIED=PHASE_MODIFIED.replace(ITERATION,ITERATION+
    '\n        ctx.use_tt = use_tt if depth > 1 or ctx.qdepth_limit == 0 else False')


def stopped():
    for name in ('rollout','advisor','slack'):
        f=json.loads((ROOT/'.local_agent'/f'{name}.json').read_bytes())
        if f.get('stopped') or f.get('user_paused'):raise RuntimeError('project stopped')


def make_refresh(events,naive=False,token=None,cancel_phase=None,expected_state=None,*,tt_policy='clear'):
    namespace=dict(search.__dict__)
    def event(phase,ctx,result,reason=None):
        events.append(dict(phase=phase,at=time.perf_counter(),deadline=ctx.budget._deadline,
            budget_identity=id(ctx.budget),q=ctx.qdepth_limit,use_tt=ctx.use_tt,
            nodes=ctx.stats.nodes,qnodes=ctx.stats.qnodes,tt_hits=ctx.stats.tt_hits,
            action=record_value(result.best_action),score=result.score,pv=record_value(result.pv),reason=reason,
            runtime_depth=ctx.runtime.depth,runtime_balanced=ctx.runtime.pushes==ctx.runtime.pops,
            runtime_restored=None if expected_state is None else (ctx.runtime.position==expected_state.position and ctx.runtime.ply_count==expected_state.ply_count and ctx.runtime.terminal_status==expected_state.terminal_status)))
        ctx.runtime.assert_balanced()
        if expected_state is not None:assert events[-1]['runtime_restored']
        if phase==cancel_phase:token.cancel()
    namespace.update(_refresh_log=event,_naive_tt=naive)
    if tt_policy not in ('clear','phase_bypass'):
        raise ValueError('unknown diagnostic TT policy')
    code=MODIFIED if tt_policy=='clear' else PHASE_MODIFIED
    exec(compile(code,'<protected-reserve-diagnostic>','exec'),namespace)
    return namespace['run_root_search']


def queen_roots(games_path,all_ui=False):
    games=json.loads(games_path.read_bytes())
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    for gi,g in enumerate(games['games']):
        selected_rows=[p for p in g['plies'] if p['role']=='UI'] if all_ui else [next(p for p in g['plies'] if p['role']=='UI' and p['decision']['action']['actor_type_id']=='Q' and p['direct_loss_flags'])]
        for selected in selected_rows:
            session=GameSession(compiled)
            for p in g['plies']:
                if p['ply']>=selected['ply']:break
                session.submit({uci(a):a for a in session.legal_actions()}[p['uci']])
            cfg=EvaluationConfig(**selected['evaluation_config']);values=selected['material']
            gains={pt.type_id:max(0,max((values[t] for t in pt.promotion_target_ids),default=0)-values[pt.type_id]) for pt in compiled.piece_types}
            profile=RuleSetEvaluationProfile(compiled.ruleset_fingerprint,1,'ui-human-teaching-v1',config_hash(cfg),
                {pt.type_id:PieceValueProfile(pt.type_id,'human-teaching-v1',0.,values[pt.type_id],values[pt.type_id],gains[pt.type_id],0.,0.,pt.is_anchor,pt.is_promotable) for pt in compiled.piece_types},3000,values,values,gains)
            yield f'ui-{gi}-{selected["ply"]}' if all_ui else f'queen-{gi}',session,Evaluator(compiled,profile,cfg)

def transfer_roots():
    case=next(c for c in CASES if c['id']=='shogi-tactic')
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))
    b=CoreBoard(case,compiled);s=GameSession(compiled);s._state=b.initial;s._search_history_witnesses=b.witnesses
    yield case['id'],s,b.material
    g=generate_game(GeneratorConfig(seed=21,board_size=4,setup_preset='bilateral_random',allow_hybrid=True))
    gc=compile_ruleset_for_execution(g.ruleset);s=GameSession(gc)
    class Unit:
        def type_value(self,tid):return 0 if gc.types_by_id[tid].is_anchor else 100
        def evaluate(self,state):
            p=state.position
            return sum((1 if x.owner==p.side_to_move else -1)*self.type_value(x.current_type_id) for x in p.board if x is not None)+sum((1 if o==p.side_to_move else -1)*self.type_value(t)*n for o,h in enumerate(p.hands) for t,n in h.items())
        def capture_order_value(self,m,c):return 10*self.type_value(c.current_type_id)-self.type_value(m.current_type_id)
    yield 'generated4-seed21',s,Unit()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--games',type=Path,default=ROOT/'.local_agent/ui-product-20261010/games-final.json')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--batch',choices=['scope','time','transfer','cancel','qzero','population'],required=True)
    p.add_argument('--tt-policy',choices=['clear','phase_bypass'],default='clear')
    args=p.parse_args()
    report=dict(declaration=__doc__,batch=args.batch,complete=False,
        tt_policy=args.tt_policy,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        search_source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
        generated_function_sha256=hashlib.sha256((MODIFIED if args.tt_policy=='clear' else PHASE_MODIFIED).encode()).hexdigest(),rows=[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():write_record(args.output,report)
    save();global_start=time.perf_counter()
    roots=transfer_roots() if args.batch=='transfer' else queen_roots(args.games,all_ui=args.batch=='population')
    for root_index,(name,s,e) in enumerate(roots):
        legal=tuple(s.legal_actions());initial=s.state;w=s._search_history_witnesses
        if args.batch=='population':cases=[(a,1,None,False,None) for a in (('baseline','refresh') if root_index%2==0 else ('refresh','baseline'))]
        elif args.batch=='scope':cases=[('baseline',5,1,False,None),('naive',5,1,False,None),('refresh',5,1,False,None)]
        elif args.batch=='time':cases=[(a,t,None,False,None) for t in (.025,.05,.1,1) for a in ('baseline','refresh','refresh','baseline')]
        elif args.batch=='transfer':cases=[(a,1,None,False,None) for a in ('baseline','refresh','refresh','baseline')]
        elif args.batch=='cancel':cases=[('refresh',1,None,True,'begin'),('refresh',1,None,True,'complete')]
        else:cases=[(a,1,2,False,None) for a in ('baseline','refresh')]
        for arm,seconds,depth,cancel,phase in cases:
            stopped();assert time.perf_counter()-global_start<300
            events=[];token=CancellationToken() if cancel else None
            fn=ORIGINAL if arm=='baseline' else make_refresh(events,arm=='naive',token,phase,s.state,
                tt_policy='clear' if arm=='naive' else args.tt_policy)
            player_module.run_root_search=fn
            player=AlphaBetaPlayer(s.compiled,evaluator_override=e,use_native_semantic_legality=False)
            q=0 if args.batch=='qzero' else 4
            limits=SearchLimits(max_time_seconds=seconds,max_depth=depth,max_nodes=1000000,quiescence_max_depth=q,quiescence_hard_max_depth=8 if q else 0)
            start=time.perf_counter()
            try:d=player.choose_action(s,limits,cancel_token=token)
            finally:player_module.run_root_search=ORIGINAL
            end=time.perf_counter()
            restored=s.state==initial and s._search_history_witnesses==w
            assert restored and (d.action is None or d.action in legal)
            assert len({v['budget_identity'] for v in events})<=1
            assert len({v['deadline'] for v in events})<=1
            source='incomplete_root_fallback' if not d.completed_depth else 'completed_main'
            if events and d.completed_depth==1:source='completed_refresh' if any(v['phase']=='complete' for v in events) else 'protected_cheap_reserve'
            row=dict(root=name,arm=arm,seconds=seconds,max_depth=depth,q=q,cancel_phase=phase,wall=end-start,
                decision=record_value(d),events=events,root_restored=restored,returned_source=source)
            report['rows'].append(row);save()
            print(name,arm,seconds,depth,d.completed_depth,source,d.termination_reason,flush=True)
    report.update(complete=True,wall=time.perf_counter()-global_start);save()

if __name__=='__main__':main()
