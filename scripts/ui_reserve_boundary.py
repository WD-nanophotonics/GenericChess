"""First-completion reserve boundary: two preselected roots, no default change.
Highest legal frontier among eight existing search attribution cases, plus
existing generated4x4seed21. Two reversed1second pairs and one deterministic
pre-completion cancellation per arm/root. Same unit material within each root.
Selection occurs before any performance result; no population extension.
"""
from pathlib import Path
import sys,json,time,hashlib,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.search_backend_comparison import CASES,CoreBoard,Material
from scripts.research_record import record_value,write_record
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta import search
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.movegen import legal_actions
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
oldordinary=search._ordinary_qdepth_limit;oldq=search._quiescence_runtime
report=dict(declaration=__doc__,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),complete=False,selection=[],roots=[])
def save():write_record(args.output,report)
def stopped():
    for n in ('rollout','advisor','slack'):
        flags=json.loads((ROOT/'.local_agent'/f'{n}.json').read_bytes())
        if flags.get('stopped') or flags.get('user_paused'):raise RuntimeError('project stopped')
compiled={g:compile_ruleset_for_execution(build_builtin_ruleset('western_chess' if g=='chess' else 'standard_shogi')) for g in ('chess','shogi')}
boards=[]
for case in CASES:
    b=CoreBoard(case,compiled[case['game']]);count=len(b.actions())
    report['selection'].append(dict(id=case['id'],legal_actions=count));boards.append((count,case,b))
_,case,b=max(boards,key=lambda x:(x[0],x[1]['id']))
s=GameSession(b.compiled);s._state=b.initial;s._search_history_witnesses=b.witnesses
selected=[(case['id'],s,b.material)]
config=GeneratorConfig(seed=21,board_size=4,setup_preset='bilateral_random',allow_hybrid=True)
generated=generate_game(config)
# Existing generator returns a legacy RuleSet; normal public compilation owns lowering.
gc=compile_ruleset_for_execution(generated.ruleset);gs=GameSession(gc)
class Unit:
    def evaluate(self,state):
        p=state.position;v=sum((1 if x.owner==p.side_to_move else -1)*100 for x in p.board if x is not None and not gc.types_by_id[x.current_type_id].is_anchor)
        return v+sum((1 if o==p.side_to_move else -1)*100*n for o,h in enumerate(p.hands) for _,n in h.items())
    def type_value(self,tid):return 0 if gc.types_by_id[tid].is_anchor else 100
    def capture_order_value(self,moving,captured):return 10*self.type_value(captured.current_type_id)-self.type_value(moving.current_type_id)
selected.append(('generated4-seed21',gs,Unit()))
report['selected_ids']=[x[0] for x in selected];report['selection_rule']='max legal frontier; deterministic id tie; candidate outcomes not inspected'
save()
for name,session,evaluator in selected:
    initial=session.state;witnesses=session._search_history_witnesses
    legal=tuple(session.legal_actions());root=dict(id=name,rule_fingerprint=session.compiled.ruleset_fingerprint,legal_count=len(legal),rows=[])
    report['roots'].append(root);save()
    for index,arm in enumerate(('baseline','one','one','baseline','baseline','one')):
        stopped();cancel=index>=4;token=CancellationToken() if cancel else None;injection={}
        def ordinary(ctx):
            if arm=='one' and ctx.first_main_iteration_complete is False:return min(1,ctx.qdepth_limit)
            return oldordinary(ctx)
        def q(alpha,beta,ply,qdepth,ctx):
            if cancel and not injection and ctx.first_main_iteration_complete is False:
                injection.update(at=time.perf_counter(),ply=ply,qdepth=qdepth,first_complete=False);token.cancel()
            return oldq(alpha,beta,ply,qdepth,ctx)
        search._ordinary_qdepth_limit=ordinary;search._quiescence_runtime=q
        player=AlphaBetaPlayer(session.compiled,evaluator_override=evaluator,use_native_semantic_legality=False)
        limits=SearchLimits(max_time_seconds=1,max_nodes=1000000,quiescence_max_depth=4,quiescence_hard_max_depth=8)
        start=time.perf_counter()
        try:d=player.choose_action(session,limits,cancel_token=token)
        finally:search._ordinary_qdepth_limit=oldordinary;search._quiescence_runtime=oldq
        end=time.perf_counter();restored=session.state==initial and session._search_history_witnesses==witnesses
        assert restored and (d.action is None or d.action in legal)
        root['rows'].append(dict(index=index,arm=arm,deterministic_cancel=cancel,wall_seconds=end-start,
            injection=injection,cancel_return_seconds=None if not injection else end-injection['at'],
            root_restored=restored,returned_source='completed_iteration' if d.completed_depth else 'incomplete_root_fallback',decision=record_value(d)))
        save();print(name,index,arm,cancel,d.completed_depth,d.termination_reason,end-start,flush=True)
report['complete']=True;save()
