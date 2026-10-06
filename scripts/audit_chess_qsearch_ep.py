"""One frozen full-history classification audit, not a performance trial."""
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from generic_chess.ai.alphabeta.search import _runtime_noisy_actions
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state, legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.public_goal_intervals import PublicGame
from scripts.audit_lichess_complete_children import uci
from scripts.audit_chess_multimode_source_replay import fen, MANIFEST, MANIFEST_SHA
from scripts.chess_complete_child_noisy import native_chess_noisy, opponent_removal
from scripts.research_record import record_value, write_record
OUT = ROOT/'docs/research/data/chess_qsearch_ep_20261006.json'
SOURCES = ('scripts/audit_chess_qsearch_ep.py','scripts/chess_complete_child_noisy.py',
 'docs/research/CHESS_QSEARCH_EP_PROTOCOL.md','generic_chess/ai/alphabeta/quiescence.py',
 'generic_chess/ai/alphabeta/search.py','generic_chess/core/search_runtime.py',
 'generic_chess/core/transition.py','generic_chess/rules/western_chess.py',
 'scripts/audit_lichess_complete_children.py','scripts/audit_chess_multimode_source_replay.py',
 'scripts/public_goal_intervals.py','scripts/research_record.py')


def main():
    if OUT.exists(): raise FileExistsError('closed classification check never rerun')
    start = monotonic()
    r = dict(complete=False,public_transitions=0,runtime_pushes=0,runtime_pops=0,
             entries=0,source_pushes=0,source_entries=0,prefix=[],children={},
             source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    push, pop = SearchPathRuntime.push, SearchPathRuntime.pop
    def save(): r['seconds']=monotonic()-start; write_record(OUT,r)
    def check():
        if monotonic()-start >= 15: raise TimeoutError('15sec cap')
        if r['public_transitions']+r['runtime_pushes']>128 or r['entries']>5000: raise ValueError('local caps')
        if r['source_pushes']>128 or r['source_entries']>5000: raise ValueError('source caps')
    def counted_push(self,*a,**kw):
        check()
        if r['public_transitions']+r['runtime_pushes']>=128: raise ValueError('pre-push cap')
        r['runtime_pushes']+=1; return push(self,*a,**kw)
    def counted_pop(self,*a,**kw):
        result=pop(self,*a,**kw); r['runtime_pops']+=1; return result
    save()
    try:
        if hashlib.sha256(MANIFEST.read_bytes()).hexdigest()!=MANIFEST_SHA: raise ValueError('manifest drift')
        author=MANIFEST.parent/'python-chess/chess/__init__.py'
        entry=next(x for x in json.loads(MANIFEST.read_text())['source_files'] if x['name']=='chess/__init__.py')
        if hashlib.sha256(author.read_bytes()).hexdigest()!=entry['sha256']: raise ValueError('author drift')
        sys.path.insert(0,str(author.parent.parent)); import chess
        if Path(chess.__file__).resolve()!=author.resolve() or chess.__version__!='1.11.2': raise ValueError('author identity')
        r.update(author_sha256=entry['sha256'],manifest_sha256=MANIFEST_SHA)
        compiled=compile_ruleset_for_execution(build_western_chess_ruleset()); r['compilations']=1
        game=PublicGame(compiled); engine=semantic_engine_for(compiled); state=initial_state(compiled); board=chess.Board()
        def match(s,b):
            if fen(record_value(s)).split()[0]!=b.board_fen() or b.turn!=(s.position.side_to_move==0): raise ValueError('board/actor mismatch')
            if not b.is_valid() or b.outcome(claim_draw=False) is not None or game.terminal(s).is_terminal: raise ValueError('ongoing scope')
            if len(s.history)!=len(b.move_stack)+1 or s.ply_count!=len(b.move_stack): raise ValueError('full history mismatch')
            for p in engine.ir.patterns:
                if not p.name.startswith('castle_'): continue
                color=chess.WHITE if '_w_' in p.name else chess.BLACK
                expected=b.has_kingside_castling_rights(color) if p.name.endswith('_ks') else b.has_queenside_castling_rights(color)
                if bool(engine._slot_value(s.position,p.slot_guards[0].slot_id,0))!=expected: raise ValueError('rights mismatch')
            ep_slots={e.slot_id for p in engine.ir.patterns for e in p.effects if e.kind=='set_token'}
            if len(ep_slots)!=1: raise ValueError('EP binding scope')
            ep=engine._slot_value(s.position,next(iter(ep_slots)),0)
            if (None if ep is None else ep[0]+8*ep[1])!=b.ep_square: raise ValueError('forced EP mismatch')
        match(state,board)
        for step in ('e2e4','a7a6','e4e5','d7d5'):
            actions=list(game.actions(state,check)); r['entries']+=len(actions)
            choices={uci(a):a for a in actions}; moves=list(board.legal_moves); r['source_entries']+=len(moves)
            if sorted(choices)!=sorted(m.uci() for m in moves): raise ValueError('prefix complete choices')
            r['entries']+=len(actions); r['public_transitions']+=1; check()
            state=game.successor(state,choices[step]); board.push(next(m for m in moves if m.uci()==step)); r['source_pushes']+=1
            match(state,board); r['prefix'].append(dict(uci=step,state=record_value(state),source_fen=board.fen(en_passant='fen'))); save()
        r['root']=record_value(state); root_moves=list(board.legal_moves); r['source_entries']+=len(root_moves)
        known={m.uci():m for m in root_moves}
        r['public_transitions']+=len(known); r['entries']+=len(known); check()
        pairs=list(legal_successors(state,compiled)); r['entries']+=len(pairs); check()
        if sorted(uci(a) for a,c in pairs)!=sorted(known): raise ValueError('complete root children')
        stats=SearchStatistics(); old=classify_noisy(state,pairs,compiled,stats)
        newstats=SearchStatistics(); new=native_chess_noisy(state,pairs,compiled,newstats)
        runtime=SearchPathRuntime.from_state(state,compiled)
        actions=list(runtime.legal_actions(check)); r['entries']+=len(actions); check()
        if set(actions)!=set(a for a,c in pairs): raise ValueError('runtime complete actions')
        ctx=SimpleNamespace(runtime=runtime,compiled=compiled,stats=SearchStatistics(),checkpoint=check)
        SearchPathRuntime.push,SearchPathRuntime.pop=counted_push,counted_pop
        old_runtime=_runtime_noisy_actions(ctx,actions); runtime.assert_balanced()
        for a,c in pairs:
            key=uci(a); eb=board.copy(stack=True); eb.push(known[key]); r['source_pushes']+=1; check(); match(c,eb)
            removal=opponent_removal(state,c)
            if removal!=board.is_capture(known[key]): raise ValueError('capture theorem/source mismatch')
            r['children'][key]=dict(action=str(a),state=record_value(c),source_fen=eb.fen(en_passant='fen'),
              is_capture=board.is_capture(known[key]),is_ep=board.is_en_passant(known[key]),
              gives_check=board.gives_check(known[key]),opponent_removed=removal,
              immutable_noisy=a in old,runtime_noisy=a in old_runtime,adapter_noisy=a in new)
        r.update(immutable_noisy=[uci(a) for a in old],runtime_noisy=[uci(a) for a in old_runtime],adapter_noisy=[uci(a) for a in new],
                 immutable_captures=stats.capture_qactions,runtime_captures=ctx.stats.capture_qactions,adapter_captures=newstats.capture_qactions)
        if r['runtime_pushes']!=r['runtime_pops']: raise ValueError('unbalanced probes')
        check(); r['complete']=True
    except Exception as error: r['error']=f'{type(error).__name__}: {error}'
    finally: SearchPathRuntime.push,SearchPathRuntime.pop=push,pop
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in r['source_sha256'].items())
    save(); print(json.dumps({k:v for k,v in r.items() if k not in ('prefix','root','children','source_sha256')}))


if __name__=='__main__': main()
