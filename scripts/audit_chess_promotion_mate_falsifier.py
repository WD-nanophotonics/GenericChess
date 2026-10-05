"""One new full-history noncutoff mate-exposure falsifier, no external source."""
from dataclasses import asdict,replace
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from scripts.audit_exchange_custody import synthetic_state
from scripts.material_leaf_choice import material_score,one_ply_choice
from scripts.native_chess_contact_intervals import EMPTY_AUX
from scripts.contact_duration_union import duration_union_choice
from scripts.public_goal_intervals import PublicGame
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
OUT=ROOT/'docs/research/data/chess_promotion_mate_falsifier_20261005.json'
PRE=OUT.with_suffix('.selections.json')
SOURCES=('scripts/audit_chess_promotion_mate_falsifier.py','docs/research/CHESS_PROMOTION_MATE_FALSIFIER_PROTOCOL.md',
 'scripts/contact_duration_union.py','scripts/native_chess_contact_intervals.py','scripts/material_leaf_choice.py',
 'scripts/audit_exchange_custody.py','scripts/public_goal_intervals.py','generic_chess/core/transition.py',
 'generic_chess/core/terminal.py','generic_chess/core/semantic_executor.py','generic_chess/rules/western_chess.py')
def friendly(v):
    if isinstance(v,dict):return {str(k):friendly(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [friendly(x) for x in v]
    return str(v) if isinstance(v,F) else v
if __name__=='__main__':
    if OUT.exists() or PRE.exists():raise FileExistsError('frozen public falsifier never rerun')
    start=monotonic();r=dict(complete=False,enumerated=0,public_transitions=0,source_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec public falsifier cap')
    try:
        c=compile_ruleset_for_execution(build_western_chess_ruleset());game=PublicGame(c)
        board=[None]*64
        for sq,owner,t in ((58,0,'K'),(52,0,'P'),(0,1,'K'),(63,1,'Q'),(51,1,'B'),(32,1,'N'),(35,1,'N')):board[sq]=Piece(owner,t,t)
        p=replace(initial_state(c).position,board=tuple(board),side_to_move=0,aux_state=EMPTY_AUX)
        root=synthetic_state(c,p);r['root']=asdict(root)
        def actions(state):
            check();a={str(x):x for x in game.actions(state,check)};r['enumerated']+=len(a)
            if len(a)>128 or r['enumerated']>5000:raise ValueError('full action cap')
            return a
        def successor(state,action,parent_count):
            check()
            if r['public_transitions']>=128:raise ValueError('transition cap')
            r['enumerated']+=parent_count
            if r['enumerated']>5000:raise ValueError('membership enumeration cap')
            r['public_transitions']+=1;child=game.successor(state,action);check();return child
        a=actions(root);r['all_root_actions']=list(a)
        if len(a)!=5:raise ValueError('prospective full root prediction fails')
        children={};r['children']={}
        for key,action in a.items():
            child=successor(root,action,len(a));children[key]=child;r['children'][key]=asdict(child)
        picks={'contact':duration_union_choice(children,game,owner=0,complete=True)}
        for name,v in (('unit',F(1)),('zero',F(0))):
            picks[name]=one_ply_choice(children,game,lambda s:material_score(s.position,{('board',t):v for t in 'PNBRQ'},{'K'},30),owner=0,complete=True)
        r['selections_before_labels']=friendly(picks)
        if not all(x['complete'] and x['selected'] is not None for x in picks.values()):raise ValueError('uncertified prelabel choice')
        PRE.write_text(json.dumps(friendly(r),indent=2)+'\n',encoding='utf-8',newline='\n')
        r['prelabel_sha256']=hashlib.sha256(PRE.read_bytes()).hexdigest();r['reply_tables']={}
        for key in sorted({x['selected'] for x in picks.values()}):
            child=children[key];replies=actions(child)
            rows=[];table=dict(all_actions=list(replies),rows=rows);r['reply_tables'][key]=table
            for rid,action in replies.items():
                after=successor(child,action,len(replies));t=game.terminal(after)
                rows.append(dict(action=rid,state=asdict(after),terminal=asdict(t)))
            table['mating_replies']=[row['action'] for row in rows if row['terminal']['status']=='checkmate' and row['terminal']['winner']==1]
            table['mate_exposure']=bool(table['mating_replies'])
        r['selected_exposure']={name:r['reply_tables'][pick['selected']]['mate_exposure'] for name,pick in picks.items()}
        r['complete']=True
    except Exception as e:r['error']=f'{type(e).__name__}: {e}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    OUT.write_text(json.dumps(friendly(r),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ('root','children','selections_before_labels','reply_tables','source_sha256','all_root_actions')}))
