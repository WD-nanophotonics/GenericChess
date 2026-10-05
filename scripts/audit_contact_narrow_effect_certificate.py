"""Analytic full-list effect/escape certificate; no public enemy successors."""
from fractions import Fraction as F
import hashlib,json,re,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.research_state_replay import read_game_state
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/contact_narrow_effect_certificate_20261005.json'
SOURCES=('scripts/audit_contact_narrow_effect_certificate.py','docs/research/CONTACT_NARROW_EFFECT_CERTIFICATE_PROTOCOL.md','docs/research/data/contact_narrow_width_20261005.json','scripts/chess_exact_contact_family.py','scripts/research_state_replay.py','generic_chess/rules/western_chess.py')
def square(file,rank):return ord(file)-97+8*(int(rank)-1)
def king_escape(board):
    king=next(i for i,p in enumerate(board) if p== (0,'K'))
    enemy=next(i for i,p in enumerate(board) if p== (1,'K'))
    rook=next(i for i,p in enumerate(board) if p== (1,'R'))
    for df in (-1,0,1):
        for dr in (-1,0,1):
            f,r=king%8+df,king//8+dr
            if (df,dr)==(0,0) or not(0<=f<8 and 0<=r<8):continue
            dest=f+8*r
            if board[dest] and board[dest][0]==0:continue
            if max(abs(f-enemy%8),abs(r-enemy//8))<=1:continue
            if dest!=rook and (f==rook%8 or r==rook//8):
                step=8 if r<rook//8 else -8 if r>rook//8 else 1 if f<rook%8 else -1
                interior=range(dest+step,rook,step)
                if not any(q!=king and board[q] is not None for q in interior):continue
            return dest
    return None
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('saved complete effect certificate never rerun')
    start=monotonic();r=dict(complete=False,rows=[],new_public_transitions=0,new_enumerated_actions=0,source_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        raw=json.loads((ROOT/SOURCES[2]).read_text());assert raw['complete'] and raw['public_transitions']==8 and not raw['depth2_fits']
        weights={law:{k[1]:v[0] for k,v in exact_chess_contact_intervals(law).items()} for law in ('geometric_half','linear_mixture')}
        weights.update(unit={t:F(1) for t in 'PNBRQ'},zero={t:F(0) for t in 'PNBRQ'})
        for root in raw['rows']:
            row=dict(branches={},models={});r['rows'].append(row)
            for key,branch in root['branches'].items():
                state=read_game_state(branch['state']);p=state.position
                if state.ply!=1 or p.aux_state!=(( 'castling_rights',0),('ep_square',-1)):
                    # Explicit representation is separately qualified by the frozen Western scope.
                    from scripts.native_chess_contact_intervals import EMPTY_AUX
                    if state.ply!=1 or p.aux_state!=EMPTY_AUX:raise ValueError('early fresh zero-aux premise')
                board=[None if piece is None else (piece.owner,piece.current_type_id) for piece in p.board]
                if sorted(x for x in board if x)!=[(0,'K'),(0,'N'),(1,'K'),(1,'R')]:raise ValueError('four native premise')
                projected=[];row['branches'][key]=projected
                for action in branch['all_enemy_actions']:
                    if monotonic()-start+raw['seconds']>=15:raise TimeoutError('same15sec cumulative')
                    m=re.fullmatch(r'([^:]+):([^:]+):([a-h])([1-8])-([a-h])([1-8])',action)
                    if not m:raise ValueError('ordinary saved action required')
                    src,dst=square(m[3],m[4]),square(m[5],m[6]);actor=board[src]
                    if actor not in ((1,'K'),(1,'R')) or board[dst] and board[dst]!=(0,'N'):raise ValueError('unsupported effect')
                    after=list(board);after[src]=None;after[dst]=actor;escape=king_escape(after)
                    if escape is None:raise ValueError('no analytic safe King witness')
                    projected.append(dict(action=action,source=src,target=dst,actor=actor[1],removed_knight=board[dst]==(0,'N'),king_escape=escape))
            for name,w in weights.items():
                scores={key:min((w['N']*(not leaf['removed_knight'])-w['R'])/31 for leaf in leaves) for key,leaves in row['branches'].items()}
                best=max(scores.values());ties=sorted(k for k,v in scores.items() if v==best)
                row['models'][name]=dict(scores=scores,tie_set=ties,selected=ties[0])
        r['analytic_reply_effects']=sum(len(v) for row in r['rows'] for v in row['branches'].values())
        r['charged_public_transitions']=raw['public_transitions'];r['charged_enumerated_actions']=raw['enumerated'];r['complete']=r['analytic_reply_effects']==122
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+0.078;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());write_record(OUT,r)
    print(json.dumps({k:v for k,v in r.items() if k not in ('rows','source_sha256')}))
