"""Analytically imported full-history children; only NEW replies materialized."""
from dataclasses import replace
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.transition import initial_state
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.actions import action_to_dict
from generic_chess.core.semantic_executor import semantic_engine_for,SemanticAction,_semantic_public_action
from generic_chess.rules.ir import geometry_candidates
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.native_chess_contact_intervals import EMPTY_AUX
from scripts.contact_duration_union import duration_union_choice
from scripts.material_leaf_choice import material_score,one_ply_choice
from scripts.public_goal_intervals import PublicGame
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/chess_promotion_imported_children_20261005.json'
PRE=OUT.with_suffix('.selections.json')
SOURCES=('scripts/audit_chess_promotion_imported_children.py','scripts/research_record.py',
 'docs/research/CHESS_PROMOTION_IMPORTED_CHILD_SCOPE.md','scripts/audit_chess_promotion_mate_falsifier.py',
 'docs/research/CHESS_PROMOTION_MATE_FALSIFIER_PROTOCOL.md','scripts/contact_duration_union.py',
 'scripts/native_chess_contact_intervals.py','scripts/public_goal_intervals.py','generic_chess/core/transition.py',
 'generic_chess/core/terminal.py','generic_chess/core/semantic_executor.py','generic_chess/rules/western_chess.py')
if __name__=='__main__':
    if OUT.exists() or PRE.exists():raise FileExistsError('frozen imported-child qualifier never rerun')
    start=monotonic();r=dict(complete=False,enumerated=0,public_transitions=0,failed_original_event_upper=5,
      original_lost_count=None,source_queries=0,reply_tables={},
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def save():r['seconds']=monotonic()-start;write_record(OUT,r)
    def check():
        if monotonic()-start>=14:raise TimeoutError('same15sec cap with1sec conservative failed charge')
    save()
    try:
        old=ROOT/'docs/research/data/chess_promotion_mate_falsifier_20261005.json'
        if old.exists() or old.with_suffix('.selections.json').exists():raise ValueError('unexpected recoverable original evidence')
        c=compile_ruleset_for_execution(build_western_chess_ruleset());e=semantic_engine_for(c);game=PublicGame(c)
        board=[None]*64
        for sq,owner,t in ((58,0,'K'),(52,0,'P'),(0,1,'K'),(63,1,'Q'),(51,1,'B'),(32,1,'N'),(35,1,'N')):board[sq]=Piece(owner,t,t)
        root=replace(initial_state(c).position,board=tuple(board),side_to_move=0,aux_state=EMPTY_AUX)
        root_key=repetition_identity_key(root,c);children={};r['imported_children']={}
        for source,target,current,promotion in ((58,51,'K',None),*( (52,60,'P',t) for t in ('B','N','Q','R'))):
            check();patterns=[p for p in c.ir.patterns if p.pattern_id.endswith('k_capture' if current=='K' else 'pawn_one_step')]
            if len(patterns)!=1:raise ValueError('pattern binding not unique')
            pattern=patterns[0]
            gids=[g for g in pattern.geometry_ids if any(d==target for d,path in geometry_candidates(c.ir.geometry[g],'0',source))]
            if len(gids)!=1:raise ValueError('geometry binding not unique')
            public=_semantic_public_action(e,SemanticAction(pattern.pattern_id,source,target,promotion,current,gids[0]))
            key=str(public);child_board=list(board);child_board[source]=None
            child_board[target]=Piece(0,'P',promotion,True) if promotion else Piece(0,'K','K')
            p=replace(root,board=tuple(child_board),side_to_move=1)
            if e.in_check(p,0):raise ValueError('analytical source child unsafe')
            child_key=repetition_identity_key(p,c);counts=tuple(sorted(((root_key,1),(child_key,1))))
            history=(HistoryRecord(root_key,-1,'',False),HistoryRecord(child_key,0,json.dumps(action_to_dict(public),sort_keys=True,separators=(',',':')),e.in_check(p,1)))
            child=GameState(p,1,counts,e.terminal_result(p,1,counts,history),history)
            if game.terminal(child).is_terminal:raise ValueError('prospective ongoing child fails')
            children[key]=child;r['imported_children'][key]=record_value(child)
        picks={'contact':duration_union_choice(children,game,owner=0,complete=True)}
        for name,v in (('unit',F(1)),('zero',F(0))):
            picks[name]=one_ply_choice(children,game,lambda s:material_score(s.position,{('board',t):v for t in 'PNBRQ'},{'K'},30),owner=0,complete=True)
        r['selections_before_labels']=record_value(picks)
        if not all(x['complete'] and x['selected'] is not None for x in picks.values()):raise ValueError('uncertified prelabel selection')
        write_record(PRE,r);r['prelabel_sha256']=hashlib.sha256(PRE.read_bytes()).hexdigest();save()
        for key in sorted({x['selected'] for x in picks.values()}):
            child=children[key];replies={str(a):a for a in game.actions(child,check)};r['enumerated']+=len(replies)
            if len(replies)>128 or r['enumerated']>5000:raise ValueError('reply enumeration cap')
            rows=[];table=dict(all_actions=list(replies),rows=rows);r['reply_tables'][key]=table;save()
            for rid,action in replies.items():
                check()
                if r['public_transitions']+5>=128:raise ValueError('same cumulative event cap')
                r['enumerated']+=len(replies)
                if r['enumerated']>5000:raise ValueError('same membership enumeration cap')
                r['public_transitions']+=1;after=game.successor(child,action);t=game.terminal(after)
                rows.append(dict(action=rid,state=record_value(after),terminal=record_value(t)));save()
            table['mating_replies']=[row['action'] for row in rows if row['terminal']['status']=='checkmate' and row['terminal']['winner']==1]
            table['mate_exposure']=bool(table['mating_replies']);save()
        r['selected_exposure']={name:r['reply_tables'][pick['selected']]['mate_exposure'] for name,pick in picks.items()};r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());save()
    print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','imported_children','selections_before_labels','reply_tables')}))
