"""Frozen complete two-root source opportunity, no external outcomes."""
from dataclasses import asdict,replace
from fractions import Fraction as F
import hashlib,json
from pathlib import Path
import sys
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.chess_certificate_request import chess_certificate_request
from scripts.contact_rb_choice import rb_contact_choice
from scripts.material_leaf_choice import material_score,one_ply_choice
from scripts.public_goal_intervals import PublicGame
OUT=ROOT/'docs/research/data/chess_double_check_20261005.selections.json'
SOURCES=('scripts/audit_chess_double_check_prelabel.py','docs/research/CHESS_DOUBLE_CHECK_SOURCE_PROTOCOL.md',
 'scripts/chess_certificate_request.py','scripts/contact_rb_choice.py','scripts/material_leaf_choice.py',
 'scripts/audit_exchange_custody.py','scripts/public_goal_intervals.py','generic_chess/core/transition.py',
 'generic_chess/rules/western_chess.py','generic_chess/rules/compiler.py')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('prelabel freeze never rerun')
    start=monotonic();report=dict(complete=False,rows=[],enumerated=0,public_transitions=0,source_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec cumulative active computation cap')
    try:
        source=ROOT/'.local_agent/certificate_source'
        sys.path.insert(0,str(source/'python-chess'));import chess
        excluded=set()
        def current(fen):return ' '.join(fen.split()[:4])
        def collect(v):
            if isinstance(v,dict):
                for k,x in v.items():
                    if k=='fen' and isinstance(x,str):
                        b=chess.Board(x)
                        for variant in (b,b.mirror(),b.transform(chess.flip_horizontal),b.mirror().transform(chess.flip_horizontal)):
                            excluded.add(current(variant.fen()))
                    else:collect(x)
            elif isinstance(v,list):
                for x in v:collect(x)
        for name in ('small_certificate_first_probe_20261004','small_selector_diagnostic_20261004','chess_contact_scoped_use_20261005','cutoff_safety_use_20261005'):
            collect(json.loads((ROOT/f'docs/research/data/{name}.json').read_text()))
        report['excluded_current_fens']=sorted(excluded)
        c=compile_ruleset_for_execution(build_western_chess_ruleset());game=PublicGame(c)
        def full_actions(s):
            a=list(game.actions(s,check));report['enumerated']+=len(a)
            if len(a)>128 or report['enumerated']>5000:raise ValueError('action cap')
            return a
        for owner in (0,1):
            board=[None]*64
            for sq,side,t in ((8,0,'K'),(18,1,'K'),(16,1,'R'),(1,1,'B')):
                if owner:sq=56-8*(sq//8)+sq%8;side=1-side
                board[sq]=Piece(side,t,t)
            p=replace(initial_state(c).position,board=tuple(board),side_to_move=owner,
              aux_state=(((0,-1),0),((1,-1),0),((2,-1),None),((3,-1),0),((4,-1),0)))
            s=synthetic_state(c,p);packet=chess_certificate_request(s,c)
            if current(packet['fen']) in excluded:raise ValueError('exposed root; no replacement')
            choices=full_actions(s)
            if len(choices)!=2 or any('capture' not in str(a) for a in choices):raise ValueError('capture-only prediction fails')
            children={};row=dict(owner=owner,weight='1/2',root=packet,all_root_actions=[str(a) for a in choices],children={})
            for action in choices:
                check()
                if report['public_transitions']>=128:raise ValueError('transition cap')
                child=game.successor(s,action);report['public_transitions']+=1;key=str(action);children[key]=child
                request=chess_certificate_request(child,c)
                if current(request['fen']) in excluded:raise ValueError('exposed child; no replacement')
                signature=''.join(sorted(p.current_type_id for p in child.position.board if p))
                if signature not in ('BKK','KKR'):raise ValueError('installed source not covered')
                row['children'][key]=dict(request=request,state=asdict(child),all_actions=[str(a) for a in full_actions(child)],signature=signature)
            selections={'contact_family':rb_contact_choice(children,game,owner=owner,complete=True)}
            for name,value in (('unit',F(1)),('zero',F(0))):
                selected=one_ply_choice(children,game,lambda x:material_score(x.position,{('board','R'):value,('board','B'):value},{'K'},30),owner=owner,complete=True)
                best=selected['score'];selected['tie_set']=sorted(k for k,v in selected['scores'].items() if v==best)
                selections[name]=selected
            if not all(x['complete'] for x in selections.values()):raise ValueError('incomplete selection')
            row['selections_before_labels']=selections;report['rows'].append(row)
        report['complete']=len(report['rows'])==2
    except Exception as e:report['error']=f'{type(e).__name__}: {e}'
    report['seconds']=monotonic()-start
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in report['source_sha256'].items())
    OUT.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','source_sha256','excluded_current_fens')}))
