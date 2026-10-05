"""Complete prospective projected action superset with independent King escapes."""
from dataclasses import replace
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.pieces import Piece
from scripts.research_state_replay import read_game_state
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/shogi_promotion_goal_exclusion_20261005.json'
SOURCES=('scripts/audit_shogi_promotion_goal_exclusion.py','docs/research/SHOGI_PROMOTION_GOAL_REDUCTION.md','docs/research/data/shogi_promotion_use_20261005.json','docs/research/data/shogi_promotion_use_20261005.selections.json','scripts/research_state_replay.py','generic_chess/rules/standard_shogi.py','generic_chess/core/semantic_executor.py')
def neighbors(source):
    for df in (-1,0,1):
        for dr in (-1,0,1):
            f,r=source%9+df,source//9+dr
            if (df or dr) and 0<=f<9 and 0<=r<9:yield f+9*r
def pawn_moves(source,kind):
    offsets=((0,1),) if kind=='P' else ((0,1),(-1,1),(1,1),(-1,0),(1,0),(0,-1))
    for df,dr in offsets:
        f,r=source%9+df,source//9+dr
        if not(0<=f<9 and 0<=r<9):continue
        modes=('TP',) if kind=='P' and r==8 else ('P','TP') if kind=='P' and (source//9>=6 or r>=6) else (kind,)
        for mode in modes:yield f+9*r,mode
def coordinate_attacked(board,target):
    for source,piece in enumerate(board):
        if piece is None or piece.owner!=0:continue
        kind=piece.current_type_id
        if kind=='K' and target in neighbors(source):return True
        if kind in ('P','TP') and any(dest==target for dest,_ in pawn_moves(source,kind)):return True
        if kind=='R':
            sf,sr=source%9,source//9;tf,tr=target%9,target//9
            if sf!=tf and sr!=tr:continue
            step=9 if tr>sr else -9 if tr<sr else 1 if tf>sf else -1
            if all(board[i] is None for i in range(source+step,target,step)):return True
    return False
def projected_own_actions(board):
    for source,piece in enumerate(board):
        if piece is None or piece.owner!=0:continue
        if piece.current_type_id=='K':destinations=((d,'K') for d in neighbors(source))
        elif piece.current_type_id in ('P','TP'):destinations=pawn_moves(source,piece.current_type_id)
        else:raise ValueError('unexpected own board mode')
        for dest,kind in destinations:
            if board[dest] is not None:continue # all others are anchors in this premise
            after=list(board);after[source]=None;after[dest]=Piece(0,piece.base_type_id,kind,kind=='TP')
            yield dict(family='board',source=source,target=dest,result=kind),after
    for dest,piece in enumerate(board):
        if piece is None:
            after=list(board);after[dest]=Piece(0,'R','R');yield dict(family='drop',source=None,target=dest,result='R'),after
def coordinate_escape(board):
    source=next(i for i,p in enumerate(board) if p and p.owner==1 and p.current_type_id=='K')
    for dest in neighbors(source):
        victim=board[dest]
        if victim and (victim.owner==1 or victim.current_type_id=='K'):continue
        after=list(board);after[source]=None;after[dest]=board[source]
        if not coordinate_attacked(after,dest):return dest,after
    return None,None
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('new exclusion certificate never rerun')
    start=monotonic();r=dict(complete=False,rows=[],quiet_counterreplies=[],new_public_transitions=0,source_queries=0,projected_actions=0,virtual_escape_positions=0,compiled_attack_checks=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start+0.406>=15:raise TimeoutError('same cumulative15sec cap')
        if r['projected_actions']+557>5000:raise ValueError('conservative5000 enumeration cap')
    try:
        raw=json.loads((ROOT/SOURCES[2]).read_text());assert raw['complete'] and raw['goal_over_budget'] and raw['public_transitions']==48
        assert hashlib.sha256((ROOT/SOURCES[3]).read_bytes()).hexdigest()==raw['prelabel_sha256']
        compiled=compile_ruleset_for_execution(build_standard_shogi_ruleset());engine=semantic_engine_for(compiled)
        values={}
        for key,branch in raw['branches'].items():
            if key.startswith('legacy_029:'):
                for reply,data in branch['leaves'].items():
                    state=read_game_state(data['state']);p=state.position;check()
                    pieces=sorted((x.owner,x.base_type_id,x.current_type_id,x.promoted) for x in p.board if x)
                    expected=[(0,'K','K',False),(0,'P','TP' if key.endswith('=TP') else 'P',key.endswith('=TP')),(1,'K','K',False)]
                    assert pieces==expected and state.ply_count==2 and p.side_to_move==0 and p.aux_state==()
                    assert list(p.hands[0].items())==[('R',1)] and p.hands[1].total()==0
                    row=dict(root_action=key,enemy_reply=reply,witnesses=[]);r['rows'].append(row)
                    for action,board in projected_own_actions(p.board):
                        check();r['projected_actions']+=1;escape,escaped=coordinate_escape(board)
                        if escaped is None:raise ValueError('no coordinate King escape in full action superset')
                        position=replace(p,board=tuple(escaped),side_to_move=1);r['virtual_escape_positions']+=1;r['compiled_attack_checks']+=1
                        if engine.in_check(position,1):raise ValueError('independent escape conflicts with compiled attacks')
                        row['witnesses'].append(dict(action=action,king_escape=escape))
                    write_record(OUT,r)
                values[key]=0
            else:
                matches=[]
                for reply,data in branch['leaves'].items():
                    state=read_game_state(data['state']);p=state.position
                    if sorted((x.owner,x.current_type_id) for x in p.board if x)==[(0,'K'),(1,'K'),(1,'R')] and p.hands[0].total()==0 and list(p.hands[1].items())==[('P',1)]:matches.append((reply,state))
                if not matches:raise ValueError('bare-King counterreply absent')
                reply,state=min(matches,key=lambda x:x[0]);assert state.ply_count==2 and state.position.side_to_move==0
                r['quiet_counterreplies'].append(dict(root_action=key,enemy_reply=reply,proof='only bare King/no hand; legal royal move cannot deliver check'))
                values[key]=0
        r['window_values']=values;r['all_root_window_values_equal']=set(values.values())=={0}
        r['paired_window_margins']={name:0 for name in ('unit','zero')};r['eventual_goal_intervals']={key:[-1,1] for key in values}
        r['charged_public_transitions']=48;r['conservative_enumeration_charge']=557+r['projected_actions']
        r['complete']=len(r['rows'])==12 and len(r['quiet_counterreplies'])==3 and len(values)==5 and r['all_root_window_values_equal']
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+0.406;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','quiet_counterreplies','source_sha256')}))
