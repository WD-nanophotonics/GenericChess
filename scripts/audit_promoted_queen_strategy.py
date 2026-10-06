"""Source proposes a decreasing-rank strategy; local checkmates certify it."""
from pathlib import Path
from time import monotonic
from collections import Counter
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.identity import position_identity_key
from generic_chess.core.terminal import TerminalResult,TerminalStatus
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.core.semantic_executor import semantic_engine_for
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value,write_record
from scripts.public_goal_intervals import PublicGame
RAW='docs/research/data/threepiece_promotion_use_v2_20261006.json'
OUT=ROOT/'docs/research/data/promoted_queen_strategy_20261006.json'
SOURCES=('scripts/audit_promoted_queen_strategy.py','docs/research/PROMOTED_QUEEN_STRATEGY_PROTOCOL.md',RAW,
 'docs/research/data/threepiece_source_extension_20261006.json','scripts/audit_f24f_western_chess_perft.py',
 'scripts/audit_lichess_complete_children.py','scripts/research_record.py','scripts/public_goal_intervals.py',
 'generic_chess/core/transition.py','generic_chess/core/terminal.py','generic_chess/core/semantic_executor.py',
 'generic_chess/rules/western_chess.py')


def audit(r):
    start=monotonic();source=ROOT/'.local_agent/certificate_source'
    old=json.loads((ROOT/RAW).read_text());qualified=json.loads((ROOT/'docs/research/data/threepiece_source_extension_20261006.json').read_text())
    if not old['complete'] or not qualified['complete']:raise ValueError('complete prior evidence')
    for path,pin in old['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=pin:raise ValueError('prior drift')
    for m in qualified['table_files']:
        if hashlib.sha256((source/'five-mode-threepiece-working'/m['name']).read_bytes()).hexdigest()!=m['sha256']:raise ValueError('table integrity')
    for m in qualified['reader_files']:
        if hashlib.sha256((source/'python-chess'/m['name']).read_bytes()).hexdigest()!=m['sha256']:raise ValueError('reader integrity')
    sys.path.insert(0,str(source/'python-chess'));import chess;import chess.gaviota
    if chess.__version__!='1.11.2' or Path(chess.__file__).resolve()!=(source/'python-chess/chess/__init__.py').resolve():raise ValueError('exact reader')
    compiled=compile_ruleset_for_execution(build_western_chess_ruleset());engine=semantic_engine_for(compiled);game=PublicGame(compiled)
    if compiled.support.max_ply<=15 or compiled.support.repetition_limit<=15:raise ValueError('DAG short-history exclusion')
    r['history_exclusion']=dict(max_absolute_ply=15,max_ply=compiled.support.max_ply,repetition_limit=compiled.support.repetition_limit,
        assumption='synthetic1-ply prefix plus strictly decreasing rank<=14; no50move/source automatic draw imported')
    p=position_from_fen('7k/1P6/8/8/8/2K5/8/8 w - - 0 1',compiled);key=position_identity_key(p,compiled)
    initial=GameState(p,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),))
    def check():
        if monotonic()-start>30:raise TimeoutError('task-specific30sec safety fuse')
        if r['public_transitions']>20000 or r['dtm_calls']>50000:raise ValueError('task-specific safety fuse')
    pairs=list(legal_successors(initial,compiled));r['public_transitions']+=len(pairs)
    state=next(c for a,c in pairs if uci(a)=='b7b8q')
    if record_value(state)!=old['children']['b7b8q']['state']:raise ValueError('exact saved root child')
    board=chess.Board(old['children']['b7b8q']['source_fen']);memo={};cache={}
    def source_key(b):return b.board_fen()+(' w' if b.turn else ' b')
    with chess.gaviota.PythonTablebase() as table:
        table.add_directory(str(source/'five-mode-threepiece-working'))
        def rank(b):
            check();k=source_key(b)
            if k not in cache:r['dtm_calls']+=1;cache[k]=table.probe_dtm(b);check()
            return cache[k]
        def visit(s,b):
            check();pk=position_identity_key(s.position,compiled);bk=source_key(b);dtm=rank(b)
            pieces={i:(x.current_type_id,x.owner) for i,x in enumerate(s.position.board) if x}
            expected={i:(chess.piece_symbol(x.piece_type).upper(),0 if x.color else 1) for i,x in b.piece_map().items()}
            if pieces!=expected or s.position.side_to_move!=(0 if b.turn else 1) or b.castling_rights or b.ep_square is not None or any(v not in (None,0) for _,v in s.position.aux_state):raise ValueError('position/actor/rights/EP association')
            if len(s.history)!=s.ply_count+1 or dict(s.repetition_counts)!=Counter(h.position_key for h in s.history) or s.history[-1].position_key!=pk or s.ply_count>15:raise ValueError('representative full history')
            terminal=game.terminal(s)
            if terminal.is_terminal:
                if terminal.status.value!='checkmate' or terminal.winner!=0 or not b.is_checkmate() or dtm!=0:raise ValueError('only real White mate leaves')
                if pk not in r['nodes']:r['nodes'][pk]=dict(board=bk,rank=0,actor=s.position.side_to_move,terminal='checkmate',winner=0,representative_state=record_value(s),all_actions=[],strategy={})
                return pk
            if b.outcome(claim_draw=False) is not None or not b.is_valid() or (dtm<=0 if b.turn else dtm>=0):raise ValueError('ongoing White-winning source rank')
            if pk in memo:
                if memo[pk]!=(bk,abs(dtm)):raise ValueError('DAG identity/rank conflict')
                r['dag_reuses']+=1;return pk
            memo[pk]=(bk,abs(dtm))
            actions={m.uci():m for m in b.legal_moves};local_pairs=list(legal_successors(s,compiled));r['public_transitions']+=len(local_pairs);r['enumerated']+=len(actions)+len(local_pairs);check()
            local={uci(a):(a,c) for a,c in local_pairs}
            if len(local)!=len(local_pairs) or sorted(local)!=sorted(actions):raise ValueError('all legal defense/action mismatch')
            node=dict(board=bk,rank=abs(dtm),actor=s.position.side_to_move,terminal='ongoing',representative_state=record_value(s),all_actions=sorted(actions),strategy={})
            r['nodes'][pk]=node
            candidates=[]
            for k in sorted(actions):
                bb=b.copy(stack=False);bb.push(actions[k]);r['author_pushes']+=1;d=rank(bb)
                win=(bb.is_checkmate() and d==0) or (not bb.outcome(claim_draw=False) and (d>0 if bb.turn else d<0))
                if win and abs(d)<abs(dtm):candidates.append((k,bb))
                elif not b.turn:raise ValueError('defender has nondecreasing/nonwinning source continuation')
            if not candidates:raise ValueError('no declining winning action')
            selected=candidates[:1] if b.turn else candidates
            for k,bb in selected:
                a,c=local[k]
                if c.history[:-1]!=s.history or c.history[-1].actor!=s.position.side_to_move or c.history[-1].gave_check!=engine.in_check(c.position,c.position.side_to_move):raise ValueError('strategy history prefix/actor/check')
                child=visit(c,bb);node['strategy'][k]=child;r['strategy_edges']+=1
            return pk
        r['root']=visit(state,board)
        if r['nodes'][r['root']]['rank']!=14:raise ValueError('saved14-ply root rank')
    for node in r['nodes'].values():
        if node['terminal']=='ongoing':
            if node['actor']==1 and sorted(node['strategy'])!=node['all_actions']:raise ValueError('missing actual defense')
            if node['actor']==0 and len(node['strategy'])!=1:raise ValueError('one attacker choice')
            if any(r['nodes'][child]['rank']>=node['rank'] for child in node['strategy'].values()):raise ValueError('rank certificate does not decrease')
    for m in qualified['table_files']:
        if hashlib.sha256((source/'five-mode-threepiece-working'/m['name']).read_bytes()).hexdigest()!=m['sha256']:raise ValueError('table after-close drift')
    r.update(complete=True,local_owner_zero_win=True,table_integrity_after_close=True,seconds=monotonic()-start)


if __name__=='__main__':
    if OUT.exists():raise FileExistsError('preserve certificate attempt')
    r=dict(complete=False,nodes={},public_transitions=0,author_pushes=0,dtm_calls=0,enumerated=0,dag_reuses=0,strategy_edges=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    start=monotonic()
    try:audit(r)
    except Exception as e:r['error']=f'{type(e).__name__}: {e}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('nodes','source_sha256')}));print('nodes',len(r['nodes']))
