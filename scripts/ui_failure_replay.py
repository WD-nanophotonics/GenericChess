"""Fixed-state UI failure diagnosis, with recorded full game histories.

Two first queen-loss roots; complete D2 material control, public D2 q0/q4
with15second/1M-node fuses, and reversed1second q0/q1/q4 cold comparisons.
Same teaching material/dynamic configuration, no fitting or new game cohort.
--reference selects frozen tracked UI export or current sandbox; code remains
an Agent diagnostic. The original UI game's persistent TT is not replicated.
"""
from pathlib import Path
import argparse
import sys
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--reference',type=Path,required=True)
p.add_argument('--games',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--first-q',choices=['baseline','one','full'],default='baseline',
               help='isolated hypothesis: ordinary q scope before first completion')
p.add_argument('--all-ui-roots',action='store_true',
               help='whole captured UI population, D2q4 reference5sec then1sec cold call')
p.add_argument('--trigger-index',choices=['on','off'],default='on',help='compiled fixed trigger dispatch ablation; same dynamic helper')
p.add_argument('--seconds',type=float,default=1,help='requested budget for timed-only diagnostic calls')
p.add_argument('--timed-only',action='store_true',help='use captured all-root1sec calls without repeating capped references')
p.add_argument('--fixed-only',action='store_true',help='only uninstrumented fixedD2q4,15sec fuse')
p.add_argument('--profile',action='store_true',help='only fixedD2q4,15sec instrumentation fuse')
args=p.parse_args()
if args.seconds<=0:p.error("--seconds must be positive")
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(args.reference.resolve()))
import json,time,hashlib
from dataclasses import asdict
import chess,generic_chess
assert Path(generic_chess.__file__).resolve().is_relative_to(args.reference.resolve())
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig,config_hash
from generic_chess.ai.evaluation.profile import PieceValueProfile,RuleSetEvaluationProfile
from generic_chess.ai.limits import SearchLimits
from scripts.search_backend_comparison import ChessBoard,minimal_ab
from scripts.research_record import record_value,write_record
from generic_chess.ai.alphabeta import search
old_ordinary=search._ordinary_qdepth_limit
if args.first_q!='baseline':
    def first_ordinary(ctx):
        if ctx.first_main_iteration_complete is False:
            return min(1,ctx.qdepth_limit) if args.first_q=='one' else ctx.qdepth_limit
        return old_ordinary(ctx)
    search._ordinary_qdepth_limit=first_ordinary
def uci(a):
    return (chess.square_name(chess.square(a.from_square.file,a.from_square.rank))+
            chess.square_name(chess.square(a.to_square.file,a.to_square.rank))+(a.promotion_target_id or '').lower())
def stopped():
    for name in ('rollout','advisor','slack'):
        f=json.loads((ROOT/'.local_agent'/f'{name}.json').read_bytes())
        if f.get('user_paused') or f.get('stopped'):raise RuntimeError('project stopped')
compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
if args.trigger_index=='off':
    if not hasattr(compiled,'_fixed_transition_triggers'):raise ValueError('reference has no compiled trigger index')
    object.__setattr__(compiled,'_fixed_transition_triggers',None)
games=json.loads(args.games.read_bytes())
report=dict(declaration=__doc__,reference=str(args.reference),first_q_policy=args.first_q,
    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    games_sha256=hashlib.sha256(args.games.read_bytes()).hexdigest(),trigger_index=args.trigger_index,
    timed_only=args.timed_only,timed_seconds=args.seconds,fixed_only=args.fixed_only,profile=args.profile,all_ui_roots=args.all_ui_roots,complete=False,roots=[])
def save():write_record(args.output,report)
save()
population=[]
for gi,game in enumerate(games['games']):
    if args.all_ui_roots:
        population.extend((gi,game,p) for p in game['plies'] if p['role']=='UI')
    else:
        population.append((gi,game,next(p for p in game['plies'] if p['role']=='UI' and
                  p['decision']['action']['actor_type_id']=='Q' and p['direct_loss_flags'])))
for gi,game,selected in population:
    moves=[p['uci'] for p in game['plies'] if p['ply']<selected['ply']]
    session=GameSession(compiled)
    for move in moves:
        session.submit({uci(a):a for a in session.legal_actions()}[move])
    board=ChessBoard(dict(setup='start',moves=' '.join(moves)))
    names={'P':chess.PAWN,'N':chess.KNIGHT,'B':chess.BISHOP,'R':chess.ROOK,'Q':chess.QUEEN,'K':chess.KING}
    board.values={names[k]:v for k,v in selected['material'].items()}
    config=EvaluationConfig(**selected['evaluation_config'])
    values=selected['material'];gains={pt.type_id:max(0,max((values[t] for t in pt.promotion_target_ids),default=0)-values[pt.type_id]) for pt in compiled.piece_types}
    profile=RuleSetEvaluationProfile(compiled.ruleset_fingerprint,1,'ui-human-teaching-v1',config_hash(config),
        {pt.type_id:PieceValueProfile(pt.type_id,'human-teaching-v1',0.,values[pt.type_id],values[pt.type_id],gains[pt.type_id],0.,0.,pt.is_anchor,pt.is_promotable) for pt in compiled.piece_types},
        3000,values,values,gains)
    evaluator=Evaluator(compiled,profile,config)
    root=dict(game_index=gi,ply=selected['ply'],moves=moves,fen=board.board.fen(),
              original=selected,rows=[],material_root_children=[])
    report['roots'].append(root);save()
    stopped();root['minimal_D2']=minimal_ab(board,2,seconds=15,node_limit=1000000)
    # All opposing legal responses at D2; mate and static material are distinct.
    for label,move in board.actions():
        board.push(move)
        responses=[]
        for reply_label,reply in board.actions():
            board.push(reply);terminal=board.terminal(2)
            responses.append(dict(reply=reply_label,score=terminal if terminal is not None else board.evaluate(),terminal=terminal is not None))
            board.pop()
        terminal=board.terminal(1)
        worst=min(responses,key=lambda x:x['score']) if responses else None
        root['material_root_children'].append(dict(move=label,worst=worst,child_terminal=terminal))
        board.pop()
    assert board.restored();save()
    if args.profile or args.fixed_only:
        cases=[(4,2,15)]
    elif args.all_ui_roots:
        cases=[(4,2,5),(4,None,args.seconds)] if args.first_q=='baseline' and not args.timed_only else [(4,None,args.seconds)]
    elif args.timed_only:
        cases=[(4,None,args.seconds)]
    else:
        cases=[(0,2,15),(4,2,15)]
        for repeat in range(2):
            cases.extend((q,None,1) for q in ([0,1,4] if repeat==0 else [4,1,0]))
    for index,(q,depth,seconds) in enumerate(cases):
        stopped()
        player=AlphaBetaPlayer(compiled,evaluator_override=evaluator,use_native_semantic_legality=False)
        limits=SearchLimits(max_depth=depth,max_time_seconds=seconds,max_nodes=1000000,
                            quiescence_max_depth=q,quiescence_hard_max_depth=8 if q else 0)
        tick=time.perf_counter()
        if args.profile:
            import cProfile,pstats
            profiler=cProfile.Profile()
            d=profiler.runcall(player.choose_action,session,limits)
            profiler.dump_stats(str(args.output.with_suffix(f'.{gi}.pstats')))
            stats=pstats.Stats(profiler)
            calls=[]
            for (file,line,name),(primitive,total,own,cumulative,callers) in stats.stats.items():
                calls.append(dict(file=file,line=line,name=name,primitive=primitive,
                                  total=total,own_seconds=own,cumulative_seconds=cumulative))
            root['profile']=sorted(calls,key=lambda x:x['cumulative_seconds'],reverse=True)
        else:
            d=player.choose_action(session,limits)
        root['rows'].append(dict(index=index,q=q,limits=asdict(limits),wall=time.perf_counter()-tick,
                                uci=None if d.action is None else uci(d.action),decision=record_value(d)))
        save();print(gi,selected['ply'],index,q,depth,root['rows'][-1]['uci'],d.completed_depth,d.termination_reason,flush=True)
report['complete']=True;save()
