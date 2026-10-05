"""New full-root mate window with active opponent; no external game source."""
from dataclasses import replace
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.native_chess_contact_intervals import EMPTY_AUX
from scripts.contact_duration_union import duration_union_choice
from scripts.material_leaf_choice import material_score,one_ply_choice
from scripts.public_goal_intervals import PublicGame
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/chess_pinned_queen_mate_20261005.json';PRE=OUT.with_suffix('.selections.json')
SOURCES=('scripts/audit_chess_pinned_queen_mate.py','docs/research/CHESS_PINNED_QUEEN_MATE_PROTOCOL.md',
 'scripts/research_record.py','scripts/native_chess_contact_intervals.py','scripts/contact_duration_union.py',
 'scripts/material_leaf_choice.py','scripts/public_goal_intervals.py','scripts/audit_exchange_custody.py',
 'generic_chess/rules/western_chess.py','generic_chess/core/transition.py','generic_chess/core/terminal.py')
if __name__=='__main__':
    if OUT.exists() or PRE.exists():raise FileExistsError('frozen new public root never rerun')
    start=monotonic();r=dict(complete=False,public_transitions=0,enumerated=0,source_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def save():r['seconds']=monotonic()-start;write_record(OUT,r)
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec mate-window total cap')
    save()
    try:
        c=compile_ruleset_for_execution(build_western_chess_ruleset());game=PublicGame(c);engine=semantic_engine_for(c)
        board=[None]*64
        for sq,owner,t in ((44,0,'K'),(53,0,'P'),(63,0,'R'),(32,0,'N'),(59,1,'K'),(62,1,'Q'),(36,1,'N')):board[sq]=Piece(owner,t,t)
        p=replace(initial_state(c).position,board=tuple(board),side_to_move=0,aux_state=EMPTY_AUX)
        root=synthetic_state(c,p);r['root']=record_value(root)
        if engine.in_check(p,0) or engine.in_check(p,1):raise ValueError('prospective safe root fails')
        def actions(state):
            check();table={str(a):a for a in game.actions(state,check)};r['enumerated']+=len(table)
            if len(table)>128 or r['enumerated']>5000:raise ValueError('full action cap')
            return table
        def apply(state,action,parent_count):
            check();r['enumerated']+=parent_count
            if r['enumerated']>5000 or r['public_transitions']>=128:raise ValueError('same event/membership cap')
            r['public_transitions']+=1;child=game.successor(state,action);check();return child
        all_root=actions(root);r['all_root_actions']=list(all_root);r['children']={};save();children={}
        for key,action in all_root.items():
            children[key]=apply(root,action,len(all_root));r['children'][key]=record_value(children[key]);save()
        picks={'contact':duration_union_choice(children,game,owner=0,complete=True)}
        for name,value in (('unit',F(1)),('zero',F(0))):
            picks[name]=one_ply_choice(children,game,lambda s:material_score(s.position,{('board',t):value for t in 'PNBRQ'},{'K'},30),owner=0,complete=True)
        r['selections_before_labels']=record_value(picks)
        if not all(x['complete'] and x['selected'] is not None for x in picks.values()):raise ValueError('uncertified selection')
        write_record(PRE,r);r['prelabel_sha256']=hashlib.sha256(PRE.read_bytes()).hexdigest();r['candidate_replies']=[];save()
        candidate=children[picks['contact']['selected']];reply=actions(candidate);r['candidate_all_replies']=list(reply);save()
        for key,action in reply.items():
            after=apply(candidate,action,len(reply));own=actions(after)
            row=dict(enemy_action=key,enemy_child=record_value(after),all_own_replies=list(own));r['candidate_replies'].append(row);save()
            mating=[(k,a) for k,a in own.items() if getattr(a,'actor_type_id',None)=='Q' and getattr(a,'to_square',None)==(3,7)]
            if len(mating)!=1:raise ValueError('prescribed Qd8 not unique')
            end=apply(after,mating[0][1],len(own));row['own_action']=mating[0][0];row['terminal_state']=record_value(end);save()
            if game.terminal(end).status.value!='checkmate' or game.terminal(end).winner!=0:raise ValueError('candidate mate-window fails')
        r['baseline_counterbranches']={};save()
        for selected in sorted({picks[name]['selected'] for name in ('unit','zero')}):
            state=children[selected];table=actions(state)
            branch=dict(all_enemy_replies=list(table),own_rows=[]);r['baseline_counterbranches'][selected]=branch;save()
            counter=[(k,a) for k,a in table.items() if getattr(a,'actor_type_id',None)=='Q' and getattr(a,'from_square',None)==(6,7) and getattr(a,'to_square',None)==(7,7)]
            if len(counter)!=1:raise ValueError('prescribed Qxh8 not legal/unique')
            after=apply(state,counter[0][1],len(table));own=actions(after);branch.update(enemy_action=counter[0][0],enemy_child=record_value(after),all_own_replies=list(own));save()
            for key,action in own.items():
                end=apply(after,action,len(own));t=game.terminal(end)
                branch['own_rows'].append(dict(action=key,state=record_value(end)));save()
                if t.status.value=='checkmate' and t.winner==0:raise ValueError('baseline has mating counterresponse')
        if not reply:raise ValueError('candidate ongoing enemy reply table empty')
        r['window_values']=dict(contact=1,unit=0,zero=0);r['game_value_intervals']=dict(contact=[1,1],unit=[-1,1],zero=[-1,1]);r['full_goal_regret']=dict(contact=[0,0],unit=[0,2],zero=[0,2]);r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());save()
    print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','root','all_root_actions','children','selections_before_labels','candidate_replies','baseline_counterbranches','candidate_all_replies')}))
