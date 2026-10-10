"""Bounded actual frozen-WebGame path diagnostic; never imports UI into sandbox.

Run with --reference pointing to an isolated git archive of the pinned ui-test,
and --deps to its pinned Web dependencies. Exports and user UI source stay local.
Two start-position games, opposite UI colors, max32plies;1second per call.
Minimal AB is material-only; actual UI keeps dynamic evaluator/q/TT/order.
This is product diagnosis, not matched-algorithm strength or a bug-free proof.
"""
from pathlib import Path
import argparse
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--reference',type=Path,required=True)
p.add_argument('--deps',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--ui-sha',default='99c97bb87474c44af94c76571f326ef8a41eb898',help='exact Git revision of the supplied tracked UI archive')
args=p.parse_args()
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(args.deps.resolve()))
sys.path.insert(0,str(args.reference.resolve()))

# Verify source bytes before importing the reference. User UI source is only
# read locally; the diagnostic publishes generated games/hash provenance.
import io,subprocess,tarfile,hashlib,time
verification_started=time.perf_counter()
archive=subprocess.check_output(['git','archive','--format=tar',args.ui_sha,'generic_chess'],cwd=ROOT)
verified=[]
with tarfile.open(fileobj=io.BytesIO(archive)) as reference_archive:
    for member in reference_archive.getmembers():
        if not member.isfile():continue
        expected=reference_archive.extractfile(member).read()
        observed=(args.reference/member.name).read_bytes()
        if observed!=expected:raise ValueError(f'reference differs from pinned UI revision: {member.name}')
        verified.append((member.name,hashlib.sha256(observed).hexdigest()))
verification_seconds=time.perf_counter()-verification_started

import asyncio
from dataclasses import asdict
import hashlib
import json
import time
import chess
import generic_chess
assert Path(generic_chess.__file__).resolve().is_relative_to(args.reference.resolve())
from generic_chess.ui.web import service as web
from generic_chess.ui.web.models import GameConfig,Operation
from generic_chess.core.actions import action_to_dict
from scripts.search_backend_comparison import ChessBoard,iterative_minimal
from scripts.research_record import record_value,write_record

UI_SHA=args.ui_sha
report=dict(declaration=__doc__,ui_sha=UI_SHA,reference_file_hashes=verified,
            reference_verification_seconds=verification_seconds,
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            complete=False,games=[],confounds=['UI dynamic terms/q4/hard8/TT/order/root-tactics vs material-only bare AB',
            'python-chess rule execution vs frozen Python generic Core',
            'service/controller snapshot path; no rendered-browser/HTTP/event latency claim'])
args.output.parent.mkdir(parents=True,exist_ok=True)
def save():write_record(args.output,report)
def stopped():
    for name in ('rollout','advisor','slack'):
        flags=json.loads((ROOT/'.local_agent'/f'{name}.json').read_bytes())
        if flags.get('user_paused') or flags.get('stopped'):raise RuntimeError('project stopped')
def uci(action):
    source=action.from_square;target=action.to_square
    return chess.square_name(chess.square(source.file,source.rank))+chess.square_name(chess.square(target.file,target.rank))+(action.promotion_target_id or '').lower()
def net(board,owner,values):
    return sum((1 if piece.color==owner else -1)*values[piece.piece_type] for piece in board.piece_map().values())

original=web.create_ui_player
calls=[]
class Observed:
    def __init__(self,compiled,**kw):
        start=time.perf_counter();self.player=original(compiled,**kw);self.setup=time.perf_counter()-start
        self.profile=self.player.evaluation_profile
    def choose_action(self,session,limits,**kw):
        started=time.perf_counter();decision=self.player.choose_action(session,limits,**kw)
        calls.append(dict(limits=asdict(limits),decision=record_value(decision),returned_uci=uci(decision.action),
            choose_seconds=time.perf_counter()-started,player_setup_seconds=self.setup,
            material=dict(self.profile.board_value_by_type),hand=dict(self.profile.hand_value_by_base_type),
            evaluation_config=asdict(self.player._config),tuning=asdict(self.player._tuning),
            evaluator_version=self.profile.evaluator_version,profile_cache_hit=self.player.evaluation_profile_cache_hit,
            native_requested=self.player.use_native_semantic_legality,
            native_provider=self.player.native_legality_provider is not None))
        return decision
web.create_ui_player=Observed

async def main():
    save()
    for game_index,ui_owner in enumerate((0,1)):
        stopped();calls.clear()
        service=web.GameService(args.output.parent/f'{args.output.stem}-saves-{game_index}')
        config=GameConfig(kind='western_chess',mode='pve',human=1-ui_owner,think_seconds=1.0)
        start=time.perf_counter();game=service.create(config);setup=time.perf_counter()-start
        board=ChessBoard(dict(setup='start',moves=''))
        # Actual published UI teaching table, not fitted from any test labels.
        board.values={chess.KING:0,chess.PAWN:1000,chess.KNIGHT:3000,chess.BISHOP:3000,chess.ROOK:5000,chess.QUEEN:9000}
        data=dict(ui_owner=ui_owner,start_fen=board.board.fen(),config=config.model_dump(),
                  create_seconds=setup,plies=[],stopping='running',ui_action_mismatches=0)
        report['games'].append(data);save()
        try:
            for ply in range(32):
                stopped()
                owner=0 if board.board.turn else 1
                before_fen=board.board.fen();before_net=net(board.board,board.board.turn,board.values)
                tick=time.perf_counter()
                if owner==ui_owner:
                    if game.task is None:game.kick()
                    assert game.task is not None
                    await asyncio.wait_for(game.task,timeout=15)
                    if game.ai_error:raise AssertionError(game.ai_error)
                    observed=calls[-1]
                    final=game.controller.history_entries()[-1].action
                    chosen=uci(final)
                    assert chosen==observed['returned_uci'],'returned/committed action mismatch'
                    details=dict(role='UI',**observed)
                else:
                    # Retain the actual game history; restoration is relative
                    # to this move's root, not the game's initial position.
                    board.root_fen=board.board.fen()
                    board.root_stack=len(board.board.move_stack)
                    board.root_ply=board.root_stack
                    result=iterative_minimal(board,seconds=1.0,node_limit=1000000,max_depth=12)
                    chosen=result['move'];assert chosen is not None
                    state=game.snapshot();legal=game.legal()
                    mapping={uci(action):i for i,action in enumerate(legal)}
                    assert set(mapping)=={move.uci() for move in board.board.legal_moves},'backend legal-set mismatch'
                    response=await game.operate(Operation(expected_revision=game.revision,request_id=f'g{game_index}p{ply}',
                        kind='action',action_id=f'{game.revision}:{mapping[chosen]}'))
                    details=dict(role='AB',result=result,limits=dict(seconds=1.0,node_fuse=1000000,max_depth=12),
                                 material=dict(board.values))
                move=chess.Move.from_uci(chosen);assert move in board.board.legal_moves
                actor=board.board.turn;board.push(move)
                assert len(game.controller.history_entries())==ply+1
                # Direct capture candidates are flags, not labels of blunders.
                threats=[]
                for reply in list(board.board.legal_moves):
                    if not board.board.is_capture(reply):continue
                    child=board.board.copy();child.push(reply)
                    loss=before_net-net(child,actor,board.values)
                    if loss>=3000:
                        threats.append(dict(reply=reply.uci(),net_loss=loss,checkmate=child.is_checkmate()))
                entry=dict(ply=ply+1,owner=owner,before_fen=before_fen,uci=chosen,after_fen=board.board.fen(),
                    total_turn_seconds=time.perf_counter()-tick,direct_loss_flags=threats,**details)
                data['plies'].append(entry);save()
                print(game_index,ply+1,details['role'],chosen,
                    details.get('decision',{}).get('completed_depth',details.get('result',{}).get('completed_depth')),flush=True)
                if game.controller.session.result.status.value!='ongoing':
                    data['stopping']='rules_terminal';break
            else:data['stopping']='32ply_predeclared_cut'
            data['final_result']=record_value(game.controller.session.result)
            data['record']=json.loads(game.controller.record_text())
        finally:
            await service.close()
        save()
    report['complete']=True;save()
asyncio.run(main())
