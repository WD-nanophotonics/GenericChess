from pathlib import Path
from time import monotonic
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record
from scripts.audit_chess_multimode_source_replay import MANIFEST,MANIFEST_SHA
OUT=ROOT/'docs/research/data/multitype_qtree_preflight_20261006.json'
FEN='7k/8/8/8/8/8/n1b2P2/1K6 w - - 0 1'
SOURCES=('scripts/preflight_multitype_qtree.py','docs/research/MULTITYPE_QTREE_PREFLIGHT_PROTOCOL.md',
 'scripts/research_record.py','scripts/audit_chess_multimode_source_replay.py')


def main():
    if OUT.exists():raise FileExistsError('one preflight; no replacement')
    start=monotonic();r=dict(complete=False,author_pushes=0,author_entries=0,public_transitions=0,
      root_fen=FEN,trees={},noisy_edges=0,evasion_edges=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        if hashlib.sha256(MANIFEST.read_bytes()).hexdigest()!=MANIFEST_SHA:raise ValueError('manifest drift')
        author=MANIFEST.parent/'python-chess/chess/__init__.py'
        entry=next(e for e in json.loads(MANIFEST.read_text())['source_files'] if e['name']=='chess/__init__.py')
        if hashlib.sha256(author.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('author drift')
        sys.path.insert(0,str(author.parent.parent));import chess
        if chess.__version__!='1.11.2' or Path(chess.__file__).resolve()!=author.resolve():raise ValueError('pinned author required')
        r.update(author_sha256=entry['sha256'],manifest_sha256=MANIFEST_SHA)
        def check():
            if monotonic()-start>=15:raise TimeoutError('15sec source cap')
            if r['author_entries']>5000:raise ValueError('source legal-list cap')
        def children(b):
            check();moves=list(b.legal_moves);r['author_entries']+=len(moves);check()
            if r['author_pushes']+len(moves)>128:raise ValueError('pre-materialize source128 cap')
            table={}
            for m in moves:
                cap=b.is_capture(m);c=b.copy(stack=True);c.push(m);r['author_pushes']+=1;check()
                if not c.is_valid():raise ValueError('invalid source child')
                goal=c.outcome(claim_draw=False)
                table[m.uci()]=dict(fen=c.fen(en_passant='fen'),checking=c.is_check(),capture=cap,
                  promotion=bool(m.promotion),source_goal=None if goal is None else dict(termination=goal.termination.name,winner=goal.winner),
                  history_length=len(c.move_stack))
                boards[m.uci()]=c
            return table
        b=chess.Board(FEN);boards={}
        if not b.is_valid() or not b.is_check():raise ValueError('fixed actual Bishop check required')
        roots=children(b);root_boards=dict(boards);r['root_actions']=len(roots)
        r['trees']['root']=roots
        for k,row in roots.items():
            c=root_boards[k]
            if c.is_check():raise ValueError('root child checking exception not admitted')
            boards={};replies=children(c);reply_boards=dict(boards);r['trees'][k]=replies
            for q,rr in replies.items():
                if rr['capture'] or rr['promotion'] or rr['checking'] or rr['source_goal'] is not None:r['noisy_edges']+=1
                if rr['checking']:
                    boards={};evades=children(reply_boards[q]);r['trees'][k+'/'+q]=evades;r['evasion_edges']+=len(evades)
                    if any(x['checking'] and x['source_goal'] is None for x in evades.values()):raise ValueError('hard2 countercheck not admitted')
        r.update(public_edge_upper_bound=r['author_pushes'],score_term_upper_bound=r['author_pushes']*3*5,
          repeated_cached_runtime_D_upper=r['author_pushes']+3*(r['noisy_edges']+r['evasion_edges']))
        if r['score_term_upper_bound']>1500:raise ValueError('public E score admission1500')
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('trees','source_sha256')}))


if __name__=='__main__':main()
