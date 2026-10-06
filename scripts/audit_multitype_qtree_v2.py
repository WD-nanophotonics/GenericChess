from pathlib import Path
from time import monotonic
from collections import Counter
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.identity import position_identity_key
from generic_chess.core.terminal import TerminalResult,TerminalStatus
from generic_chess.core.transition import legal_successors
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.ai.alphabeta.search import terminal_score
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.audit_lichess_complete_children import uci
from scripts.audit_chess_multimode_source_replay import fen
from scripts.chess_approx_static_inventory import ChessApproxStaticInventory
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.chess_complete_child_noisy import opponent_removal
from scripts.research_record import write_record,record_value
OLD='docs/research/data/multitype_qtree_preflight_20261006.json'
OUT=ROOT/'docs/research/data/multitype_qtree_v2_20261006.json'
SOURCES=('scripts/audit_multitype_qtree_v2.py','docs/research/MULTITYPE_QTREE_EXECUTION_PROTOCOL.md','docs/research/MULTITYPE_QTREE_V2_CORRECTION.md','docs/research/data/multitype_qtree_import_failure_20261006.json',OLD,
 'scripts/audit_f24f_western_chess_perft.py','scripts/audit_lichess_complete_children.py',
 'scripts/audit_chess_multimode_source_replay.py','scripts/chess_approx_static_inventory.py',
 'scripts/chess_exact_contact_family.py','scripts/chess_complete_child_noisy.py','scripts/research_record.py',
 'generic_chess/core/transition.py','generic_chess/core/semantic_executor.py','generic_chess/rules/western_chess.py',
 'docs/research/data/chess_zero_target_correction_20261005.json')


def main():
    if OUT.exists():raise FileExistsError('one public-tree execution')
    start=monotonic();r=dict(complete=False,public_transitions=0,entries=0,new_author_pushes=0,runtime_pushes=0,
      score_terms=0,nodes={},edges={},policies={},source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def save():r['seconds']=monotonic()-start;write_record(OUT,r)
    save()
    try:
        old=json.loads((ROOT/OLD).read_text())
        if not old['complete'] or not old['source_hashes_unchanged']:raise ValueError('qualified sole preflight root required')
        for p,pin in old['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('preflight source drift')
        def check():
            if monotonic()-start+old['seconds']>=15:raise TimeoutError('combined15sec cap')
            if r['entries']>5000 or r['score_terms']>1500:raise ValueError('arithmetic/list cap')
        compiled=compile_ruleset_for_execution(build_western_chess_ruleset());r['compilations']=1
        engine=semantic_engine_for(compiled);ir=engine.ir
        p=position_from_fen(old['root_fen'],compiled);key=position_identity_key(p,compiled)
        root=GameState(p,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),))
        states={'root':root};r['nodes']['root']=dict(state=record_value(root),source_fen=old['root_fen'],source_goal=None)
        slots={p.name:p.slot_guards[0].slot_id for p in ir.patterns if p.name.startswith('castle_')}
        ep_slots={e.slot_id for p in ir.patterns for e in p.effects if e.kind=='set_token'}
        if len(ep_slots)!=1 or len(slots)!=4:raise ValueError('native slot contract')
        for parent,source_rows in old['trees'].items():
            check();s=states[parent]
            if r['public_transitions']+len(source_rows)>128:raise ValueError('pre-materialization128 cap')
            r['public_transitions']+=len(source_rows);r['entries']+=len(source_rows);check()
            pairs=list(legal_successors(s,compiled));r['entries']+=len(pairs);check()
            if sorted(uci(a) for a,c in pairs)!=sorted(source_rows):raise ValueError('complete source/public move-set mismatch')
            edge={}
            for a,c in pairs:
                k=uci(a);src=source_rows[k];path=k if parent=='root' else parent+'/'+k
                view=record_value(c);parts=src['fen'].split();observed=fen(view).split()
                if observed[:2]!=parts[:2]:raise ValueError('source board/actor mismatch')
                if any(engine._slot_value(c.position,slot,0) for slot in slots.values()) or parts[2]!='-':raise ValueError('fixed no-castling contract')
                ep=engine._slot_value(c.position,next(iter(ep_slots)),0)
                expected=None if parts[3]=='-' else (ord(parts[3][0])-97,int(parts[3][1])-1)
                if ep!=expected:raise ValueError('forced EP mismatch')
                checked=engine.in_check(c.position,c.position.side_to_move)
                if checked!=src['checking'] or opponent_removal(s,c)!=src['capture']:raise ValueError('capture/check semantic mismatch')
                if len(c.history)!=src['history_length']+1 or c.ply_count!=src['history_length']:raise ValueError('full synthetic path length')
                if c.history[:-1]!=s.history or c.history[-1].actor!=s.position.side_to_move or c.history[-1].gave_check!=checked:raise ValueError('prefix actor/check history mismatch')
                ck=position_identity_key(c.position,compiled)
                if c.history[-1].position_key!=ck or dict(c.repetition_counts)!=dict(Counter(h.position_key for h in c.history)):raise ValueError('complete exact identity/count consistency')
                states[path]=c;r['nodes'][path]=dict(state=view,source_fen=src['fen'],source_goal=src['source_goal'],checking=checked)
                edge[k]=dict(child=path,capture=src['capture'],promotion=src['promotion'],checking=checked)
            r['edges'][parent]=edge;save()
        if r['public_transitions']!=old['public_edge_upper_bound']:raise ValueError('entire source tree not materialized')
        weights={law:{m:lo for (_,m),(lo,hi) in exact_chess_contact_intervals(law).items()} for law in ('geometric_half','linear_mixture')}
        weights['unit']={m:1 for m in 'PNBRQ'}
        for law,w in weights.items():
            evaluator=ChessApproxStaticInventory(w);trace={}
            def evaluate(path):
                check()
                if r['score_terms']+5>1500:raise ValueError('pre-score term cap')
                r['score_terms']+=5;return evaluator.evaluate(states[path])
            def q(path,d):
                check();s=states[path]
                if s.terminal_status.is_terminal:return terminal_score(s.terminal_status,s.position.side_to_move,s.ply_count)
                checking=r['nodes'][path]['checking']
                if checking:
                    if d>=2:raise ValueError('ongoing hard2 check; no static fallback')
                    values={k:-q(e['child'],d+1) for k,e in r['edges'][path].items()}
                else:
                    values={'stand_pat_approximation':evaluate(path)}
                    if d<1:
                        values.update({k:-q(e['child'],d+1) for k,e in r['edges'][path].items()
                          if e['capture'] or e['promotion'] or e['checking'] or states[e['child']].terminal_status.is_terminal})
                score=max(values.values());trace[path]=dict(depth=d,in_check=checking,branch_scores=values,score=score)
                return score
            scores={k:-q(e['child'],0) for k,e in r['edges']['root'].items()}
            static={k:-evaluate(e['child']) for k,e in r['edges']['root'].items()};best=max(scores.values())
            ties=sorted(k for k,v in scores.items() if v==best)
            r['policies'][law]=dict(scores=scores,full_ties=ties,canonical=ties[0],static_scores=static,
              static_full_ties=sorted(k for k,v in static.items() if v==max(static.values())),integer_weights=evaluator.weights,trace=trace)
            save()
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    save();print(json.dumps({k:v for k,v in r.items() if k not in ('nodes','edges','policies','source_sha256')}))
    print(json.dumps({k:{f:v[f] for f in ('scores','full_ties','static_full_ties')} for k,v in r['policies'].items()}))


if __name__=='__main__':main()
