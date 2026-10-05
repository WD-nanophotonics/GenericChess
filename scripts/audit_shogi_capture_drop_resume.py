"""Four frozen actual custody paths, full state and action evidence."""
from collections import Counter
from dataclasses import replace
import hashlib, json, sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.public_goal_intervals import PublicGame
from scripts.research_record import record_value,write_record
from scripts.research_state_replay import read_game_state
from scripts.saved_shogi_board_binding import saved_shogi_board_binding
from generic_chess.core.actions import action_source_square,action_target_square,action_promotion_target_id
from scripts.resource_mode_context import resource_ledger
from scripts.material_leaf_choice import inventory_features
from scripts.shogi_board_hand_gap import board_hand_gap
OUT=ROOT/'docs/research/data/shogi_capture_drop_resume_20261005.json'
FAILED=ROOT/'docs/research/data/shogi_capture_drop_coupling_20261005.json'
SOURCES=('scripts/audit_shogi_capture_drop_resume.py','scripts/audit_shogi_capture_drop_coupling.py','scripts/saved_shogi_board_binding.py','docs/research/SHOGI_CAPTURE_DROP_RESUME_SCOPE.md','docs/research/data/shogi_capture_drop_coupling_20261005.json','docs/research/SHOGI_CAPTURE_DROP_COUPLING_PROTOCOL.md',
    'scripts/research_record.py','scripts/audit_exchange_custody.py','scripts/public_goal_intervals.py',
    'scripts/shogi_board_hand_gap.py','scripts/material_leaf_choice.py','scripts/resource_mode_context.py',
    'generic_chess/core/semantic_executor.py','generic_chess/core/transition.py','generic_chess/rules/standard_shogi.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen custody paths')
    start=monotonic();failed=json.loads(FAILED.read_text());r=dict(complete=False,public_transitions=0,enumerated=failed['enumerated'],source_queries=0,rows=[],
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def save():r['seconds']=monotonic()-start;write_record(OUT,r)
    def check():
        if monotonic()-start+failed['seconds']>=15:raise TimeoutError('15sec cap')
    save()
    try:
        c=compile_ruleset_for_execution(build_standard_shogi_ruleset());g=PublicGame(c);e=semantic_engine_for(c)
        stock=Counter(p.base_type_id for p in initial_state(c).position.board if p and p.base_type_id!='K')
        for owner in (0,1):
            transform=(lambda s:s) if owner==0 else (lambda s:80-s)
            for current in ('P','TP'):
                check();board=[None]*81
                for sq,side,base,tid in ((0,owner,'K','K'),(80,1-owner,'K','K'),(39,owner,'P',current),(48,1-owner,'L','L')):
                    board[transform(sq)]=Piece(side,base,tid,base!=tid)
                remaining=stock-Counter(P=1,L=1);hands=[Hands(()),Hands(())]
                hands[owner]=Hands(tuple(sorted(remaining.items())))
                p=replace(initial_state(c).position,board=tuple(board),hands=tuple(hands),side_to_move=1-owner)
                state=read_game_state(failed['rows'][0]['root']) if owner==0 and current=='P' else synthetic_state(c,p);row=dict(victim_owner=owner,victim_current=current,root=record_value(state),steps=[])
                r['rows'].append(row);save()
                for source,target,actor in ((48,39,'L'),(0,1,'K'),(None,30,'P')):
                    check();resource_ledger(c,state.position,'shogi')
                    if g.terminal(state).is_terminal or any(e.in_check(state.position,i) for i in (0,1)):
                        raise ValueError('noncheck ongoing path scope failed')
                    if owner==0 and current=='P' and source==48:
                        actions={key:saved_shogi_board_binding(state,key) for key in failed['rows'][0]['steps'][0]['all_actions']}
                    else:
                        actions={str(a):a for a in g.actions(state,check)};r['enumerated']+=len(actions)
                    step=dict(all_actions=list(actions));row['steps'].append(step);save()
                    found=[]
                    for key,a in actions.items():
                        src=action_source_square(a);dst=action_target_square(a)
                        src=None if src is None else 9*src.rank+src.file;dst=9*dst.rank+dst.file
                        if src==(None if source is None else transform(source)) and dst==transform(target) and action_promotion_target_id(a) is None:
                            found.append((key,a))
                    if len(found)!=1:raise ValueError('frozen unique mechanics absent')
                    if r['enumerated']+len(actions)>5000 or r['public_transitions']>=128:raise ValueError('unchanged event/entry cap')
                    before=inventory_features(state.position,{'K'});key,action=found[0]
                    r['public_transitions']+=1;r['enumerated']+=len(actions)
                    state=g.successor(state,action);after=inventory_features(state.position,{'K'})
                    delta={k:after.get(k,0)-before.get(k,0) for k in before.keys()|after.keys()}
                    delta={k:v for k,v in delta.items() if v}
                    step.update(action=key,state=record_value(state),delta=record_value(delta));save()
                    resource_ledger(c,state.position,'shogi')
                    if g.terminal(state).is_terminal or any(e.in_check(state.position,i) for i in (0,1)):
                        raise ValueError('unqualified resulting leaf')
        r['drop_gap']={law:board_hand_gap(law,normalized=True)['P']['lower'] for law in ('geometric_half','linear_mixture')}
        r['complete']=len(r['rows'])==4 and all(len(row['steps'])==3 for row in r['rows'])
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());save()
    print(json.dumps({k:record_value(v) for k,v in r.items() if k not in ('source_sha256','rows')}))
