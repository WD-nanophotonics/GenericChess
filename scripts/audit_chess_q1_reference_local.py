"""Prospectively frozen independent-reference root; no outcome labels read here."""
from pathlib import Path
from time import monotonic
from dataclasses import asdict
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import generic_chess.ai.alphabeta.search as search
from generic_chess.core.identity import position_identity_key
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import legal_successors
from generic_chess.core.terminal import TerminalResult,TerminalStatus
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.audit_lichess_complete_children import uci
from scripts.audit_chess_multimode_source_replay import fen,MANIFEST,MANIFEST_SHA
from scripts.public_goal_intervals import PublicGame
from scripts.chess_complete_child_noisy import native_chess_noisy
from scripts.chess_capture_effect_hint_v3 import ChessCaptureEffectHintV3
from scripts.chess_approx_static_inventory import ChessApproxStaticInventory
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.chess_q1_root import complete_q1_root
from scripts.research_record import record_value,write_record
OUT=ROOT/'docs/research/data/chess_q1_reference_local_20261006.json'
FEN='7k/8/8/8/3p4/8/2P5/K7 w - - 0 1'
SOURCES=('scripts/audit_chess_q1_reference_local.py','scripts/chess_q1_root.py','docs/research/CHESS_Q1_REFERENCE_PREFLIGHT.md',
 'scripts/chess_complete_child_noisy.py','scripts/chess_capture_effect_hint_v3.py','scripts/chess_approx_static_inventory.py',
 'scripts/chess_exact_contact_family.py','scripts/audit_f24f_western_chess_perft.py','scripts/audit_lichess_complete_children.py',
 'scripts/audit_chess_multimode_source_replay.py','scripts/public_goal_intervals.py','scripts/research_record.py',
 'generic_chess/core/search_runtime.py','generic_chess/ai/alphabeta/search.py','generic_chess/core/transition.py',
 'generic_chess/rules/western_chess.py','docs/research/data/chess_zero_target_correction_20261005.json')


def main():
    if OUT.exists():raise FileExistsError('fixed complete research root never rerun')
    start=monotonic();r=dict(complete=False,public_transitions=0,runtime_pushes=0,runtime_pops=0,
      entries=0,source_pushes=0,source_entries=0,qnodes=0,children={},policies={},synthetic_initial_fen=FEN,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    oldclass=search._runtime_noisy_actions;oldq=search._quiescence_runtime
    push,pop,legal=SearchPathRuntime.push,SearchPathRuntime.pop,SearchPathRuntime.legal_actions
    expected={}
    def save():r['seconds']=monotonic()-start;write_record(OUT,r)
    def check():
        if monotonic()-start>=15:raise TimeoutError('whole15sec cap')
        if r['public_transitions']+r['runtime_pushes']>128 or r['entries']>5000:raise ValueError('local caps')
        if r['source_pushes']>128 or r['source_entries']>5000 or r['qnodes']>128:raise ValueError('source/aggregate q cap')
    def counted_push(self,a,*args,**kwargs):
        check()
        if r['public_transitions']+r['runtime_pushes']>=128:raise ValueError('pre-push cap')
        parent=self.position;r['runtime_pushes']+=1;result=push(self,a,*args,**kwargs)
        child=expected[parent][uci(a)]
        if self.position!=child.position or self.ply_count!=child.ply_count or self.terminal_status!=child.terminal_status:
            raise ValueError('actual runtime edge/saved public child mismatch')
        return result
    def counted_pop(self,*args,**kwargs):
        result=pop(self,*args,**kwargs);r['runtime_pops']+=1;return result
    def counted_legal(self,*args,**kwargs):
        check();result=legal(self,*args,**kwargs);r['entries']+=len(result);check();return result
    def counted_q(*args,**kwargs):
        check()
        if r['qnodes']>=128:raise ValueError('pre-q cap')
        r['qnodes']+=1;return oldq(*args,**kwargs)
    def adapter(ctx,actions):
        if any(h.total() for h in ctx.runtime.position.hands):raise ValueError('empty-hand scope')
        captures=[];quiet=[]
        for a in actions:
            if hint.legal_pattern_captures(a.pattern_id):captures.append(a);ctx.stats.capture_qactions+=1
            else:quiet.append(a)
        return captures+oldclass(ctx,quiet)
    save()
    try:
        if hashlib.sha256(MANIFEST.read_bytes()).hexdigest()!=MANIFEST_SHA:raise ValueError('manifest drift')
        author=MANIFEST.parent/'python-chess/chess/__init__.py'
        entry=next(e for e in json.loads(MANIFEST.read_text())['source_files'] if e['name']=='chess/__init__.py')
        if hashlib.sha256(author.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('author drift')
        sys.path.insert(0,str(author.parent.parent));import chess
        if Path(chess.__file__).resolve()!=author.resolve() or chess.__version__!='1.11.2':raise ValueError('pinned source required')
        r.update(author_sha256=entry['sha256'],manifest_sha256=MANIFEST_SHA)
        # Preflight source tree first; reuse every counted author push.
        board=chess.Board(FEN); source_trees={}
        def source_children(b):
            moves={m.uci():m for m in b.legal_moves};r['source_entries']+=len(moves)
            if r['source_entries']>5000 or r['source_pushes']+len(moves)>128:raise ValueError('source preflight cap')
            result={}
            for k,m in moves.items():
                bb=b.copy(stack=True);bb.push(m);r['source_pushes']+=1;check()
                if not bb.is_valid() or bb.is_check() or bb.outcome(claim_draw=False) is not None:raise ValueError('preflight ongoing nonchecking scope')
                result[k]=bb
            source_trees[b.fen(en_passant='fen')]=result
            return result
        if not board.is_valid() or board.is_check() or board.outcome(claim_draw=False) is not None:raise ValueError('preflight initial scope')
        first=source_children(board)
        for bb in first.values():source_children(bb)
        reply_count=sum(len(source_trees[b.fen(en_passant='fen')]) for b in first.values())
        bound=len(first)+reply_count+3*reply_count
        r['preflight']=dict(root_actions=len(first),all_replies=reply_count,combined_event_upper_bound=bound,
          source_trees_qualified=True,external_labels_read=False)
        save()
        if bound>128:raise ValueError('preflight whole public/runtime128 admission')
        compiled=compile_ruleset_for_execution(build_western_chess_ruleset());r['compilations']=1
        game=PublicGame(compiled);engine=semantic_engine_for(compiled);ir=engine.ir
        hint=ChessCaptureEffectHintV3(compiled.ruleset_fingerprint,ir.patterns,ir.geometry)
        p=position_from_fen(FEN,compiled);key=position_identity_key(p,compiled)
        root=GameState(p,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),));board=chess.Board(FEN)
        castles={p.name:p.slot_guards[0].slot_id for p in ir.patterns if p.name.startswith('castle_')}
        ep_slots={e.slot_id for p in ir.patterns for e in p.effects if e.kind=='set_token'}
        if len(ep_slots)!=1 or len(castles)!=4:raise ValueError('native slot scope')
        def match(s,b):
            check()
            if not b.is_valid() or b.outcome(claim_draw=False) is not None or b.is_check() or game.terminal(s).is_terminal:raise ValueError('ongoing nonchecking source scope')
            if fen(record_value(s)).split()[0]!=b.board_fen() or b.turn!=(s.position.side_to_move==0):raise ValueError('board/actor mismatch')
            if len(s.history)!=len(b.move_stack)+1 or s.ply_count!=len(b.move_stack):raise ValueError('full synthetic history mismatch')
            for name,slot in castles.items():
                color=chess.WHITE if '_w_' in name else chess.BLACK
                want=b.has_kingside_castling_rights(color) if name.endswith('_ks') else b.has_queenside_castling_rights(color)
                if bool(engine._slot_value(s.position,slot,0))!=want:raise ValueError('rights mismatch')
            ep=engine._slot_value(s.position,next(iter(ep_slots)),0)
            if (None if ep is None else ep[0]+8*ep[1])!=b.ep_square:raise ValueError('EP mismatch')
        def complete_pairs(s,b):
            moves={m.uci():m for m in b.legal_moves};r['source_entries']+=len(moves)
            check()
            if r['public_transitions']+r['runtime_pushes']+len(moves)>128:raise ValueError('pre-materialize cap')
            r['public_transitions']+=len(moves);r['entries']+=len(moves);check()
            pairs=list(legal_successors(s,compiled));r['entries']+=len(pairs);check()
            if sorted(uci(a) for a,c in pairs)!=sorted(moves):raise ValueError('complete source/legal set')
            expected[s.position]={uci(a):c for a,c in pairs}
            sources={}
            for a,c in pairs:
                bb=source_trees[b.fen(en_passant='fen')][uci(a)];match(c,bb)
                if hint.legal_pattern_captures(a.pattern_id)!=b.is_capture(moves[uci(a)]):raise ValueError('metadata/source capture mismatch')
                sources[uci(a)]=bb
            return pairs,sources
        match(root,board);r['root']=record_value(root)
        roots,root_sources=complete_pairs(root,board)
        if len(roots)!=r['preflight']['root_actions']:raise ValueError('complete prospectively qualified root contract')
        root_map={uci(a):c for a,c in roots};reply_map={};noisy_map={}
        for a,c in roots:
            k=uci(a);pairs,sources=complete_pairs(c,root_sources[k]);reply_map[k]=pairs
            noisy_map[k]=native_chess_noisy(c,pairs,compiled)
            source_moves={m.uci():m for m in root_sources[k].legal_moves};r['source_entries']+=len(source_moves);check()
            r['children'][k]=dict(state=record_value(c),source_fen=root_sources[k].fen(en_passant='fen'),
              replies={uci(x):dict(state=record_value(y),source_fen=sources[uci(x)].fen(en_passant='fen'),
                  capture=root_sources[k].is_capture(source_moves[uci(x)]),ep=root_sources[k].is_en_passant(source_moves[uci(x)])) for x,y in pairs},
              noisy=[uci(x) for x in noisy_map[k]])
            save()
        weights={law:{m:lo for (_,m),(lo,hi) in exact_chess_contact_intervals(law).items()} for law in ('geometric_half','linear_mixture')}
        weights['unit']={m:1 for m in 'PNBRQ'}
        SearchPathRuntime.push,SearchPathRuntime.pop,SearchPathRuntime.legal_actions=counted_push,counted_pop,counted_legal
        search._runtime_noisy_actions,search._quiescence_runtime=adapter,counted_q
        for law,w in weights.items():
            evaluator=ChessApproxStaticInventory(w);reference={};static={}
            for k,c in root_map.items():
                stand=evaluator.evaluate(c);static[k]=-stand
                reply_values=[-evaluator.evaluate(y) for x,y in reply_map[k] if x in noisy_map[k]]
                reference[k]=-max([stand]+reply_values)
            before=(r['runtime_pushes'],r['entries'],r['qnodes'])
            scores,ties,stats=complete_q1_root(root_map,compiled,evaluator,check,lambda:max(.001,15-(monotonic()-start)))
            if scores!=reference:raise ValueError('actual root/full-table mismatch')
            r['policies'][law]=dict(scores=scores,full_ties=ties,canonical=ties[0],reference=reference,
                static_scores=static,integer_weights=evaluator.weights,statistics={k:asdict(v) for k,v in stats.items()},
                runtime_pushes=r['runtime_pushes']-before[0],entries=r['entries']-before[1],qnodes=r['qnodes']-before[2])
            save()
        if r['runtime_pushes']!=r['runtime_pops']:raise ValueError('unbalanced runtime')
        check();r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    finally:
        search._runtime_noisy_actions,search._quiescence_runtime=oldclass,oldq
        SearchPathRuntime.push,SearchPathRuntime.pop,SearchPathRuntime.legal_actions=push,pop,legal
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in r['source_sha256'].items())
    save();print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','root','children','policies')}))
    print(json.dumps({k:{f:v[f] for f in ('scores','full_ties','runtime_pushes','entries','qnodes')} for k,v in r['policies'].items()}))


if __name__=='__main__':main()
