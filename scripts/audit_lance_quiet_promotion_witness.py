"""Frozen new preparation path: native L quiet promotion, then lateral capture."""
from dataclasses import asdict, replace
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_shogi_target_role_controls import (
    Piece, Hands, semantic_engine_for, _semantic_public_action, initial_state,
    compile_ruleset_for_execution, build_standard_shogi_ruleset, synthetic_state,
    binding_reward, public_child_reward, trace_tag, PublicGame, resource_ledger,
    action_source_square, action_target_square)
PROTOCOL = 'docs/research/LANCE_QUIET_PROMOTION_WITNESS_PROTOCOL.md'
SHA = '4609910cd955ff5747e9f6415151e95bfc614f02ee6e3d3211460bda8b3d5f4f'

def audit(report):
    start = monotonic()
    def check():
        if monotonic()-start >= 15:
            raise RuntimeError('15-second cap')
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest()!=SHA:
        raise ValueError('protocol drift')
    compiled=compile_ruleset_for_execution(build_standard_shogi_ruleset())
    engine=semantic_engine_for(compiled); game=PublicGame(compiled)
    board=[None]*81
    for square,owner,base in [(0,0,'K'),(71,1,'K'),(40,0,'L'),(59,1,'P'),(21,1,'P')]:
        board[square]=Piece(owner,base,base,False)
    pos=replace(initial_state(compiled).position,board=tuple(board),hands=(Hands(),Hands()),side_to_move=0)
    try:
        resource_ledger(compiled,pos,'shogi')
    except ValueError as error:
        if 'global base inventory' not in str(error):
            raise
    else:
        raise ValueError('sparse inventory wrongly admitted')
    state=synthetic_state(compiled,pos)
    report['root_state']=asdict(state)
    tag=dict(owner=0,base='L',board={40:F(1)},held=F(0),lost=F(0))
    product=1
    def sq(a,target=False):
        s=(action_target_square if target else action_source_square)(a)
        return None if s is None else s.rank*9+s.file
    try:
        for source,destination,promotion in [(40,58,'TL'),(71,80,None),(58,59,None)]:
            check()
            if game.terminal(state).is_terminal:
                raise ValueError('unexpected endpoint')
            actions={}; bindings={}; rewards={}
            def tick():
                check()
                if report['enumerated']>=2000:
                    raise RuntimeError('2000 enumeration cap')
                report['enumerated']+=1
            for a in game.actions(state,check):
                tick(); key=str(a)
                if key in actions or len(actions)>=128:
                    raise ValueError('unique complete public actions required')
                actions[key]=a
            for runtime,binding in engine.iter_legal_action_bindings(state.position,checkpoint=check):
                tick(); key=str(_semantic_public_action(engine,runtime))
                if key in bindings or len(bindings)>=128:
                    raise ValueError('unique complete bindings required')
                bindings[key]=(runtime,binding)
                rewards[key]=binding_reward(engine,state.position,runtime,binding,tag)
            if not actions or actions.keys()!=bindings.keys():
                raise ValueError('full public/binding identity mismatch')
            keys=[k for k,a in actions.items() if sq(a)==source and sq(a,True)==destination and getattr(a,'promotion_target_id',None)==promotion]
            if len(keys)!=1:
                raise ValueError('frozen unique path action missing')
            key=keys[0]; product*=len(actions)
            if report['public_transitions']>=8:
                raise RuntimeError('8 transitions cap')
            child=game.successor(state,actions[key]); report['public_transitions']+=1
            reward=public_child_reward(state.position,child.position,actions[key],tag,compiled.support.type_metadata)
            if reward!=rewards[key]:
                raise AssertionError('reward mismatch')
            runtime,binding=bindings[key]
            tag=trace_tag(engine,state.position,child.position,runtime,binding,tag)
            if child.ply_count!=state.ply_count+1 or len(child.history)!=len(state.history)+1 or game.terminal(child).is_terminal:
                raise ValueError('actual ongoing history required')
            report['steps'].append(dict(actions=list(actions),chosen=key,reward=reward,tag=tag,child_state=asdict(child)))
            state=child; check()
        if [r['reward'] for r in report['steps']]!=[0,0,1] or state.position.board[59].current_type_id!='TL':
            raise AssertionError('promoted native-origin source capture not established')
        report.update(complete=True,conditional_path_lower=F(1,product),common_law_lower=F(1,20*product))
    finally:
        report['seconds']=monotonic()-start

if __name__=='__main__':
    destination=ROOT/'docs/research/data/lance_quiet_promotion_witness_20261004.json'
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError('fresh destination required; no rerun')
    paths=[PROTOCOL,'scripts/audit_lance_quiet_promotion_witness.py','scripts/audit_shogi_target_role_controls.py',
           'scripts/owned_service_reward.py','scripts/owned_tag_trace.py','scripts/public_goal_intervals.py',
           'scripts/audit_exchange_custody.py','scripts/resource_mode_context.py',
           'generic_chess/core/semantic_executor.py','generic_chess/rules/standard_shogi.py']
    report=dict(source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                steps=[],public_transitions=0,enumerated=0,complete=False)
    try:
        audit(report)
    except Exception as error:
        report['error']=f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in report['source_sha256'].items())
    destination.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','steps','root_state')},default=str))
    print(json.dumps([dict(choices=len(s['actions']),chosen=s['chosen'],reward=s['reward']) for s in report['steps']],default=str))
