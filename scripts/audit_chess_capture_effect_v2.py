"""Actual qsearch mirror with versioned native capture-effect metadata."""
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from dataclasses import asdict
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import generic_chess.ai.alphabeta.search as search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.identity import position_identity_key
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalResult,TerminalStatus
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.audit_lichess_complete_children import uci
from scripts.audit_chess_multimode_source_replay import fen,MANIFEST,MANIFEST_SHA
from scripts.public_goal_intervals import PublicGame
from scripts.chess_complete_child_noisy import native_chess_noisy
from scripts.chess_capture_effect_hint_v2 import ChessCaptureEffectHintV2
from generic_chess.core.semantic_executor import semantic_engine_for
from scripts.chess_approx_static_inventory import ChessApproxStaticInventory
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.research_record import record_value,write_record
OUT=ROOT/'docs/research/data/chess_capture_effect_v2_20261006.json'
FEN='k7/8/8/8/4p3/8/3P4/7K w - - 0 1'
SOURCES=('scripts/audit_chess_capture_effect_v2.py','docs/research/CHESS_CAPTURE_EFFECT_V2_PROTOCOL.md',
 'scripts/chess_complete_child_noisy.py','scripts/chess_capture_effect_hint_v2.py','generic_chess/core/semantic_executor.py','scripts/chess_approx_static_inventory.py',
 'scripts/chess_exact_contact_family.py','scripts/audit_f24f_western_chess_perft.py',
 'scripts/audit_lichess_complete_children.py','scripts/audit_chess_multimode_source_replay.py',
 'scripts/research_record.py','scripts/public_goal_intervals.py','generic_chess/ai/alphabeta/search.py',
 'generic_chess/ai/alphabeta/quiescence.py','generic_chess/core/search_runtime.py',
 'docs/research/data/chess_zero_target_correction_20261005.json')


def main():
    if OUT.exists():raise FileExistsError('new fixed semantic control never rerun')
    start=monotonic();r=dict(complete=False,public_transitions=0,runtime_pushes=0,runtime_pops=0,
        entries=0,source_pushes=0,source_entries=0,children={},runs=[],synthetic_initial_fen=FEN,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    oldclass=search._runtime_noisy_actions;push,pop,legal=SearchPathRuntime.push,SearchPathRuntime.pop,SearchPathRuntime.legal_actions
    def save():r['seconds']=monotonic()-start;write_record(OUT,r)
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec cap')
        if r['public_transitions']+r['runtime_pushes']>128 or r['entries']>5000:raise ValueError('local cap')
        if r['source_pushes']>128 or r['source_entries']>5000:raise ValueError('source cap')
    def counted_push(self,*args,**kwargs):
        check()
        if r['public_transitions']+r['runtime_pushes']>=128:raise ValueError('pre-push cap')
        r['runtime_pushes']+=1;return push(self,*args,**kwargs)
    def counted_pop(self,*args,**kwargs):
        result=pop(self,*args,**kwargs);r['runtime_pops']+=1;return result
    def counted_legal(self,*args,**kwargs):
        check();result=legal(self,*args,**kwargs);r['entries']+=len(result);check();return result
    def adapter(ctx,actions):
        captures=[];remaining=[]
        for action in actions:
            if hint.legal_pattern_captures(action.pattern_id):
                captures.append(action);ctx.stats.capture_qactions+=1
            else:remaining.append(action)
        return captures+oldclass(ctx,remaining)
    save()
    try:
        if hashlib.sha256(MANIFEST.read_bytes()).hexdigest()!=MANIFEST_SHA:raise ValueError('manifest drift')
        author=MANIFEST.parent/'python-chess/chess/__init__.py'
        entry=next(e for e in json.loads(MANIFEST.read_text())['source_files'] if e['name']=='chess/__init__.py')
        if hashlib.sha256(author.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('author drift')
        sys.path.insert(0,str(author.parent.parent));import chess
        if Path(chess.__file__).resolve()!=author.resolve() or chess.__version__!='1.11.2':raise ValueError('pinned author identity')
        r.update(author_sha256=entry['sha256'],manifest_sha256=MANIFEST_SHA)
        compiled=compile_ruleset_for_execution(build_western_chess_ruleset());r['compilations']=1;game=PublicGame(compiled)
        hint=ChessCaptureEffectHintV2(compiled.ruleset_fingerprint,semantic_engine_for(compiled).ir.patterns);r['pattern_bits']=hint.bits
        p=position_from_fen(FEN,compiled);key=position_identity_key(p,compiled)
        initial=GameState(p,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),))
        board=chess.Board(FEN)
        if not board.is_valid() or board.outcome(claim_draw=False) is not None or game.terminal(initial).is_terminal:raise ValueError('valid synthetic initial')
        actions=list(game.actions(initial,check));r['entries']+=len(actions)
        source=list(board.legal_moves);r['source_entries']+=len(source)
        if sorted(uci(a) for a in actions)!=sorted(m.uci() for m in source):raise ValueError('prefix complete actions')
        chosen=next(a for a in actions if uci(a)=='d2d4');r['public_transitions']+=1;r['entries']+=len(actions);check()
        root=game.successor(initial,chosen);board.push(next(m for m in source if m.uci()=='d2d4'));r['source_pushes']+=1
        r['initial']=record_value(initial);r['root']=record_value(root)
        if fen(r['root']).split()[0]!=board.board_fen() or root.ply_count!=1 or len(root.history)!=2:raise ValueError('prefix board/history')
        known={m.uci():m for m in board.legal_moves};r['source_entries']+=len(known)
        r['public_transitions']+=len(known);r['entries']+=len(known);check()
        pairs=list(legal_successors(root,compiled));r['entries']+=len(pairs);check()
        if sorted(uci(a) for a,c in pairs)!=sorted(known):raise ValueError('complete root action mismatch')
        weights={m:lo for (_,m),(lo,hi) in exact_chess_contact_intervals('geometric_half').items()}
        evaluator=ChessApproxStaticInventory(weights);noisy=native_chess_noisy(root,pairs,compiled)
        values={};r['reference_noisy']=[uci(a) for a in noisy]
        for a,c in pairs:
            m=known[uci(a)]
            if hint.legal_pattern_captures(a.pattern_id)!=board.is_capture(m):raise ValueError('hint/source capture mismatch')
            eb=board.copy(stack=True);eb.push(m);r['source_pushes']+=1;check()
            if not eb.is_valid() or eb.outcome(claim_draw=False) is not None or eb.is_check() or game.terminal(c).is_terminal:raise ValueError('nonchecking ongoing child contract')
            if fen(record_value(c)).split()[0]!=eb.board_fen() or c.ply_count!=2 or len(c.history)!=3:raise ValueError('child source/history')
            value=-evaluator.evaluate(c);values[uci(a)]=value
            r['children'][uci(a)]=dict(state=record_value(c),source_fen=eb.fen(en_passant='fen'),is_capture=board.is_capture(m),is_ep=board.is_en_passant(m),value=value)
        expected=max([evaluator.evaluate(root)]+[values[uci(a)] for a in noisy]);r['reference_score']=expected
        r['integer_weights']=evaluator.weights
        SearchPathRuntime.push,SearchPathRuntime.pop,SearchPathRuntime.legal_actions=counted_push,counted_pop,counted_legal
        for name,fn in (('original',oldclass),('metadata_adapter',adapter)):
            runtime=SearchPathRuntime.from_state(root,compiled);stats=SearchStatistics()
            limits=SearchLimits(max_depth=1,max_nodes=128,max_time_seconds=max(.001,15-(monotonic()-start)),quiescence_max_depth=1,quiescence_hard_max_depth=2,quiescence_max_nodes=128)
            ctx=search._Context(compiled,evaluator,TranspositionTable(max_entries=16),stats,search._Budget(limits,None),SearchTuning(),False,False,1,2,128,runtime=runtime)
            search._runtime_noisy_actions=fn
            before=(runtime.position,runtime.ply_count,runtime.terminal_status,tuple(runtime.history),runtime.repetition_counts,runtime.runtime_hash)
            counts=(r['runtime_pushes'],r['entries']);score=search.quiescence(root,-search.INF,search.INF,0,0,ctx)
            runtime.assert_balanced()
            if before!=(runtime.position,runtime.ply_count,runtime.terminal_status,tuple(runtime.history),runtime.repetition_counts,runtime.runtime_hash):raise ValueError('restoration mismatch')
            r['runs'].append(dict(name=name,score=score,stats=asdict(stats),runtime_pushes=r['runtime_pushes']-counts[0],entries=r['entries']-counts[1]));save()
        if r['runs'][1]['score']!=expected or r['runtime_pushes']!=r['runtime_pops']:raise ValueError('adapter actual/reference or balance')
        check();r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    finally:
        search._runtime_noisy_actions=oldclass;SearchPathRuntime.push,SearchPathRuntime.pop,SearchPathRuntime.legal_actions=push,pop,legal
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in r['source_sha256'].items())
    save();print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','initial','root','children','runs')}));print(json.dumps(r['runs']))


if __name__=='__main__':main()
