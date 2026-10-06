from pathlib import Path
from collections import Counter
from time import monotonic
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.identity import position_identity_key
from generic_chess.core.terminal import TerminalResult,TerminalStatus
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.audit_lichess_complete_children import uci
from scripts.audit_chess_multimode_source_replay import fen
from scripts.chess_approx_static_inventory import ChessApproxStaticInventory
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.public_goal_intervals import PublicGame
from scripts.research_record import record_value,write_record
PROTOCOL='docs/research/THREEPIECE_PROMOTION_USE_PROTOCOL.md'
OUT=ROOT/'docs/research/data/threepiece_promotion_use_20261006.json'
FEN='7k/1P6/8/8/8/2K5/8/8 w - - 0 1'
SOURCES=(PROTOCOL,'scripts/audit_threepiece_promotion_use.py','scripts/audit_threepiece_source_extension.py',
 'docs/research/data/threepiece_source_extension_20261006.json','scripts/chess_approx_static_inventory.py',
 'scripts/chess_exact_contact_family.py','scripts/audit_f24f_western_chess_perft.py',
 'scripts/audit_lichess_complete_children.py','scripts/audit_chess_multimode_source_replay.py',
 'scripts/research_record.py','scripts/public_goal_intervals.py','generic_chess/core/transition.py',
 'generic_chess/rules/western_chess.py')


def audit(r):
    start=monotonic();source=ROOT/'.local_agent/certificate_source'
    qualified=json.loads((ROOT/'docs/research/data/threepiece_source_extension_20261006.json').read_text())
    if not qualified['complete']:raise ValueError('complete prior source qualification')
    for m in qualified['table_files']:
        path=source/'five-mode-threepiece-working'/m['name']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=m['sha256']:raise ValueError('table drift')
    for m in qualified['reader_files']:
        if hashlib.sha256((source/'python-chess'/m['name']).read_bytes()).hexdigest()!=m['sha256']:raise ValueError('reader drift')
    sys.path.insert(0,str(source/'python-chess'));import chess;import chess.gaviota
    if chess.__version__!='1.11.2' or Path(chess.__file__).resolve()!=(source/'python-chess/chess/__init__.py').resolve():raise ValueError('exact isolated reader')
    compiled=compile_ruleset_for_execution(build_western_chess_ruleset());game=PublicGame(compiled)
    p=position_from_fen(FEN,compiled);key=position_identity_key(p,compiled)
    root=GameState(p,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),))
    author=chess.Board(FEN)
    if not author.is_valid() or game.terminal(root).is_terminal:raise ValueError('valid ongoing root required')
    def check():
        if monotonic()-start>30:raise TimeoutError('local30sec safety fuse')
        if r['public_transitions']>64 or r['outer_probe_calls']>128 or r['enumerated']>5000:raise ValueError('finite safety fuse')
    moves={m.uci():m for m in author.legal_moves};r['enumerated']+=len(moves);check()
    pairs=list(legal_successors(root,compiled));r['public_transitions']+=len(pairs);r['enumerated']+=len(pairs);check()
    if len(moves)>16 or sorted(moves)!=sorted(uci(a) for a,c in pairs):raise ValueError('complete root set')
    r['root']=record_value(root);children={};boards={}
    for action,child in pairs:
        k=uci(action);b=author.copy(stack=True);b.push(moves[k]);r['source_pushes']+=1;check()
        local=record_value(child)
        if not b.is_valid() or fen(local).split()[0]!=b.board_fen() or child.position.side_to_move!=1 or child.ply_count!=1 or len(child.history)!=2 or tuple(child.history[:-1])!=tuple(root.history) or dict(child.repetition_counts)!=Counter(h.position_key for h in child.history):raise ValueError('child association/history conflict')
        # All root moves preserve no castling/EP; Pawn moves are promotions only.
        if b.castling_rights or b.ep_square is not None or any(v not in (None,0) for _,v in child.position.aux_state):raise ValueError('rights/EP child conflict')
        r['children'][k]=dict(state=local,source_fen=b.fen(en_passant='fen'),local_terminal=game.terminal(child).status.value)
        children[k]=child;boards[k]=b
    weights={law:{m:lo for (_,m),(lo,hi) in exact_chess_contact_intervals(law).items()} for law in ('geometric_half','linear_mixture')}
    weights['unit']={m:1 for m in 'PNBRQ'}
    for law,w in weights.items():
        evaluator=ChessApproxStaticInventory(w);scores={k:-evaluator.evaluate(c) for k,c in children.items()}
        best=max(scores.values());r['policies'][law]=dict(scores=scores,full_ties=sorted(k for k,v in scores.items() if v==best),integer_weights=evaluator.weights)
    r['choices_frozen_before_probes']=True;r['seconds']=monotonic()-start;write_record(OUT,r)
    with chess.gaviota.PythonTablebase() as table:
        table.add_directory(str(source/'five-mode-threepiece-working'))
        for k,b in boards.items():
            check();r['outer_probe_calls']+=1;dtm=table.probe_dtm(b);check()
            r['outer_probe_calls']+=1;wdl=table.probe_wdl(b);check()
            if dtm and (1 if dtm>0 else -1)!=wdl:raise ValueError('source sign conflict')
            outcome=b.outcome(claim_draw=False)
            r['children'][k].update(signed_dtm_child=dtm,wdl_child=wdl,source_root_utility=-wdl,
                source_terminal=None if outcome is None else dict(termination=outcome.termination.name,winner=outcome.winner))
    optimum=max(x['source_root_utility'] for x in r['children'].values());r['source_root_optimum']=optimum
    for policy in r['policies'].values():
        values={k:r['children'][k]['source_root_utility'] for k in policy['full_ties']}
        policy.update(tied_source_utilities=values,utility_interval=[min(values.values()),max(values.values())],regret_interval=[optimum-max(values.values()),optimum-min(values.values())])
    r.update(complete=True,seconds=monotonic()-start)


if __name__=='__main__':
    if OUT.exists():raise FileExistsError('one development trial; no replacement')
    r=dict(complete=False,children={},policies={},enumerated=0,public_transitions=0,source_pushes=0,outer_probe_calls=0,
      scope='adaptive source-adjudicated depth1 development control, no F24F/general quality claim',
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    start=monotonic()
    try:audit(r)
    except Exception as e:r['error']=f'{type(e).__name__}: {e}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('root','children','source_sha256')}))
