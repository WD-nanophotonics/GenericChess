"""Prospective complete first-quiet exchange, fixed controllers, bounded once."""
from dataclasses import replace
from pathlib import Path
from time import monotonic
from fractions import Fraction as F
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.actions import action_target_square
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.native_chess_contact_intervals import EMPTY_AUX
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.material_leaf_choice import material_score,one_ply_choice,inventory_features
from scripts.public_goal_intervals import PublicGame
from scripts.outcome_set_order import set_order
from scripts.research_record import record_value,write_record
OUT=ROOT/'docs/research/data/chess_first_quiet_pilot_20261006.json';PRE=OUT.with_suffix('.selections.json')
SOURCES=('scripts/audit_chess_first_quiet_pilot.py','docs/research/CHESS_FIRST_QUIET_PILOT_PROTOCOL.md',
 'scripts/audit_exchange_custody.py','scripts/native_chess_contact_intervals.py',
 'scripts/chess_exact_contact_family.py','scripts/material_leaf_choice.py',
 'scripts/public_goal_intervals.py','scripts/outcome_set_order.py','scripts/research_record.py',
 'generic_chess/rules/western_chess.py','generic_chess/core/transition.py','generic_chess/core/semantic_executor.py',
 'docs/research/data/chess_zero_target_correction_20261005.json')


def pick(i,label,options):
    key=f'GenericChess/first-quiet/v1/proposal/{i}/{label}'
    return options[int.from_bytes(hashlib.sha256(key.encode()).digest(),'big')%len(options)]


def proposal(i):
    k=pick(i,'K',[8*y+x for y in range(2,6) for x in range(2,6)])
    adjacent=[8*(k//8+dy)+k%8+dx for dx in (-1,0,1) for dy in (-1,0,1) if dx or dy]
    entries=[(k,0,'K')]
    for mode in ('N','B'):
        sq=pick(i,mode,adjacent);adjacent.remove(sq);entries.append((sq,1,mode))
    occupied={sq for sq,_,_ in entries}
    king=pick(i,'enemy-K',[sq for sq in (0,7,56,63) if sq not in occupied]);entries.append((king,1,'K'));occupied.add(king)
    entries.append((pick(i,'own-R',[sq for sq in range(64) if sq not in occupied]),0,'R'))
    return entries


def ordinary(state):return sum(p is not None and p.current_type_id!='K' for p in state.position.board)


def main():
    if OUT.exists() or PRE.exists():raise FileExistsError('closed pilot never rerun')
    start=monotonic();r=dict(complete=False,proposals=0,enumerated=0,public_transitions=0,source_queries=0,
       rejection_counts={},nodes={},leaves={},policies={},outcomes={},compilations=0,
       source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def save():r['seconds']=monotonic()-start;write_record(OUT,r)
    def check():
        if monotonic()-start>=30:raise TimeoutError('30sec whole family cap')
    def actions(state):
        table={}
        for action in game.actions(state,check):
            check()
            if r['enumerated']>=5000 or len(table)>=128:raise ValueError('enumeration/list cap')
            key=str(action)
            if key in table:raise ValueError('canonical collision')
            table[key]=action;r['enumerated']+=1
        return table
    def apply(state,action,count):
        check()
        if r['public_transitions']>=128 or r['enumerated']+count>5000:raise ValueError('128 transitions/5000 membership cap')
        r['enumerated']+=count;r['public_transitions']+=1
        return game.successor(state,action)
    save()
    try:
        compiled=compile_ruleset_for_execution(build_western_chess_ruleset());r['compilations']=1
        game=PublicGame(compiled);engine=semantic_engine_for(compiled);template=initial_state(compiled).position
        root=None
        for i in range(128):
            check();r['proposals']+=1;entries=proposal(i);board=[None]*64
            for sq,owner,mode in entries:board[sq]=Piece(owner,mode,mode)
            p=replace(template,board=tuple(board),side_to_move=0,aux_state=EMPTY_AUX)
            reason=None
            if engine.in_check(p,1):reason='previous_mover_check'
            elif not engine.in_check(p,0):reason='not_checked'
            else:
                candidate=synthetic_state(compiled,p)
                if game.terminal(candidate).is_terminal:reason='terminal_root'
                else:
                    table=actions(candidate)
                    if len(table) not in (2,3):reason='branch_count'
                    else:
                        captured=set()
                        for a in table.values():
                            t=action_target_square(a);piece=None if t is None else board[t.rank*8+t.file]
                            if piece and piece.owner==1 and piece.current_type_id!='K':captured.add(piece.current_type_id)
                        if len(captured)<2:reason='two_capture_types'
                        else:root=candidate;r['proposal_index']=i;r['root_entries']=entries;break
            r['rejection_counts'][reason]=r['rejection_counts'].get(reason,0)+1
        if root is None:raise ValueError('no eligible root within128 proposals')
        r['root']=record_value(root);weights={}
        for law in ('geometric_half','linear_mixture'):
            weights[law]={key:lo for key,(lo,hi) in exact_chess_contact_intervals(law).items() if lo==hi}
        for law,value in (('unit',F(1)),('zero',F(0))):weights[law]={('board',mode):value for mode in 'PNBRQ'}
        def visit(state,path,table=None):
            check();terminal=game.terminal(state)
            if terminal.is_terminal:
                r['leaves'][path]=dict(kind='terminal',state=record_value(state),terminal=record_value(terminal));return
            table=actions(state) if table is None else table;children={k:apply(state,a,len(table)) for k,a in table.items()}
            if not children:raise ValueError('ongoing empty choice set')
            r['nodes'][path]=dict(state=record_value(state),all_actions=list(table),children={k:record_value(s) for k,s in children.items()})
            if state.position.side_to_move==0:
                policy={}
                for law,w in weights.items():
                    choice=one_ply_choice(children,game,lambda s,w=w:material_score(s.position,w,{'K'},30),owner=0,complete=True)
                    if not choice['complete']:raise ValueError('unqualified controller')
                    choice['tie_set']=sorted(k for k,v in choice['scores'].items() if v==choice['score']);policy[law]=choice
                r['policies'][path]=record_value(policy)
            if path=='root':
                r['selections_before_labels']=r['policies'][path]
                write_record(PRE,r);r['prelabel_sha256']=hashlib.sha256(PRE.read_bytes()).hexdigest()
            save()
            for key,child in children.items():
                cp=path+'/'+key;terminal=game.terminal(child);delta=ordinary(state)-ordinary(child)
                if terminal.is_terminal:
                    r['leaves'][cp]=dict(kind='terminal',state=record_value(child),terminal=record_value(terminal))
                elif delta==0:
                    features=inventory_features(child.position,{'K'})
                    if any(loc!='board' or mode not in 'PNBRQ' for loc,mode in features):raise ValueError('unqualified quiet inventory')
                    r['leaves'][cp]=dict(kind='quiet',state=record_value(child),vector=[features.get(('board',mode),0) for mode in 'PNBRQ'],information_increment=child.ply_count>1)
                elif delta==1:visit(child,cp)
                else:raise ValueError('capture finiteness premise violated')
                save()
        visit(root,'root',table)
        def outcomes(path,law,ties):
            if path in r['leaves']:return {path:r['leaves'][path]}
            node=r['nodes'][path];keys=node['all_actions']
            if node['state']['position']['side_to_move']==0:
                policy=r['policies'][path][law];keys=policy['tie_set'] if ties else [policy['selected']]
            result={}
            for key in keys:result.update(outcomes(path+'/'+key,law,ties))
            return result
        for law in weights:
            r['outcomes'][law]={}
            for kind,ties in (('canonical',False),('all_ties',True)):
                leaves=outcomes('root',law,ties);r['outcomes'][law][kind]=dict(paths=list(leaves),
                    vectors={p:v['vector'] for p,v in leaves.items() if v['kind']=='quiet'},
                    terminals={p:v['terminal'] for p,v in leaves.items() if v['kind']=='terminal'},
                    future_information=sum(v.get('information_increment',False) for v in leaves.values()))
        r['comparisons']={}
        for law in ('geometric_half','linear_mixture'):
            for base in ('unit','zero'):
                for kind in ('canonical','all_ties'):
                    a=r['outcomes'][law][kind];b=r['outcomes'][base][kind]
                    r['comparisons'][law+'/'+base+'/'+kind]=dict(unknown='mixed terminal classes') if a['terminals'] or b['terminals'] else dict(forward=set_order(a['vectors'],b['vectors']),reverse=set_order(b['vectors'],a['vectors']))
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in r['source_sha256'].items());save()
    print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','nodes','leaves','policies','outcomes','comparisons')},default=str))
    print(json.dumps({law:{kind:{k:v for k,v in row.items() if k not in ('paths','vectors')} for kind,row in value.items()} for law,value in r['outcomes'].items()}))


if __name__=='__main__':main()
