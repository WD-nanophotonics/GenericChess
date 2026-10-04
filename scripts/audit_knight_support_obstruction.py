"""Frozen new physical-coalition obstruction root, complete counterstrategy."""
from dataclasses import asdict,replace
from fractions import Fraction as F
from collections import Counter
from pathlib import Path
from time import monotonic
import sys,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_shogi_target_role_controls import (
    Piece,Hands,semantic_engine_for,_semantic_public_action,initial_state,
    compile_ruleset_for_execution,build_standard_shogi_ruleset,synthetic_state,
    binding_reward,public_child_reward,trace_tag,PublicGame,resource_ledger,
    action_source_square,action_target_square)

PROTOCOL='docs/research/KNIGHT_SUPPORT_OBSTRUCTION_PROTOCOL.md'
SHA='78d559b9317007a83ff6948330c08e1eddc12a218008bb5a2f5c1daeced849fb'


class Limit(Exception):pass


def audit(report):
    start=monotonic()
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest()!=SHA:
        raise ValueError('frozen protocol drift')

    def check():
        if monotonic()-start>=15:raise Limit('15-second cap')

    compiled=compile_ruleset_for_execution(build_standard_shogi_ruleset())
    game=PublicGame(compiled);engine=semantic_engine_for(compiled)

    def table(state,tag):
        if game.terminal(state).is_terminal:raise ValueError('unexpected terminal frontier')
        public={};bindings={};rewards={}

        def tick():
            check()
            if report['enumerated']>=5000:raise Limit('5000 enumeration cap')
            report['enumerated']+=1
        for a in game.actions(state,check):
            tick();k=str(a)
            if k in public or len(public)>=128:raise ValueError('public identity/bound')
            public[k]=a
        for r,b in engine.iter_legal_action_bindings(state.position,checkpoint=check):
            tick();k=str(_semantic_public_action(engine,r))
            if k in bindings or len(bindings)>=128:raise ValueError('binding identity/bound')
            bindings[k]=(r,b);rewards[k]=binding_reward(engine,state.position,r,b,tag)
        if not public or public.keys()!=bindings.keys():raise ValueError('complete public/binding correspondence')
        return public,bindings,rewards

    def square(a,target=False):
        s=(action_target_square if target else action_source_square)(a)
        return None if s is None else 9*s.rank+s.file

    def step(state,source,target,choices,key):
        check()
        if report['public_transitions']>=128:raise Limit('128 shared transitions cap')
        child=game.successor(state,choices[0][key]);report['public_transitions']+=1
        r,b=choices[1][key]
        reward=public_child_reward(state.position,child.position,choices[0][key],source,compiled.support.type_metadata)
        if reward!=choices[2][key]:raise AssertionError('public/binding reward mismatch')
        s=trace_tag(engine,state.position,child.position,r,b,source)
        t=trace_tag(engine,state.position,child.position,r,b,target)
        if child.ply_count!=state.ply_count+1 or len(child.history)!=len(state.history)+1:
            raise AssertionError('actual history mismatch')
        if game.terminal(child).is_terminal:raise ValueError('unqualified early terminal')
        check();return child,s,t,reward

    def unique(choices,predicate):
        keys=[k for k,a in choices[0].items() if predicate(a)]
        if len(keys)!=1:raise ValueError('frozen unique action absent')
        return keys[0]

    try:
        board=[None]*81
        for p,o,b in [(0,0,'K'),(62,1,'K'),(54,0,'R'),(58,0,'P'),(49,1,'P'),(59,1,'P')]:
            board[p]=Piece(o,b,b,False)
        pos=replace(initial_state(compiled).position,board=tuple(board),hands=(Hands((('N',1),)),Hands()),side_to_move=0)
        state=synthetic_state(compiled,pos)
        try:resource_ledger(compiled,pos,'shogi')
        except ValueError as e:
            if 'global base inventory' not in str(e):raise
        else:raise ValueError('sparse stock incorrectly accepted')
        stock=Counter(p.base_type_id for p in compiled.initial_position.board if p)
        actual=Counter(p.base_type_id for p in board if p);actual.update(dict(pos.hands[0].items()))
        report['missing_tokens']=sum((stock-actual).values())
        if report['missing_tokens']!=33:raise ValueError('resource deficit mismatch')
        source=dict(owner=0,base='N',board={},held=F(1),lost=F(0))
        target=dict(owner=1,base='P',board={59:F(1)},held=F(0),lost=F(0))
        report['root_state']=asdict(state)
        root=table(state,source);report['root_actions']=list(root[0])
        selected={}
        for k,a in root[0].items():
            p,q=square(a),square(a,True)
            if p is None and getattr(a,'base_type_id',None)=='N':
                if q in (31,33,40,42):
                    if q in selected:raise ValueError('nonunique candidate drop')
                    selected[q]=k
                else:report['pruned'][k]='not a native-N preimage of f7/f6'
            elif p in (0,54,58):report['pruned'][k]='non-source first move leaves last source drop unable to capture'
            else:raise ValueError('unsupported first action invalidates pruning')
        if set(selected)!={31,33,40,42}:raise ValueError('complete four-drop set required')
        report['root_coverage_complete']=True
        for p in (31,33,40,42):
            row=dict(square=p,first=selected[p],complete=False,interval=[0,1]);report['rows'].append(row)
            child,s,t,reward=step(state,source,target,root,selected[p])
            if reward!=0 or s['board']!={p:F(1)}:raise AssertionError('held drop trace')
            enemy=table(child,s);row['enemy_actions']=list(enemy[0])
            if p in (31,33):
                reply=unique(enemy,lambda a:square(a)==62 and square(a,True)==71)
            else:
                reply=unique(enemy,lambda a:square(a)==59 and square(a,True)==50)
            row['counterreply']=reply
            last,s,t,_=step(child,s,t,enemy,reply)
            row.update(source=s,target=t,after_counterreply=asdict(last))
            own=table(last,s);row['last_own_actions']=list(own[0])
            target_point=next(iter(t['board']))
            if any(square(a)==p and square(a,True)==target_point for a in own[0].values()):
                raise ValueError('source capture refutes frozen counterstrategy')
            if s['board']!={p:F(1)} or t['lost']!=0 or last.position.board[58]!=board[58]:
                raise AssertionError('physical interference/tag proof mismatch')
            row.update(complete=True,interval=[0,0],proof='complete last own set lacks designated source capture')
        report['root_value_interval']=[0,0];report['all_controls_complete']=True
    finally:report['seconds']=monotonic()-start


if __name__=='__main__':
    destination=ROOT/'docs/research/data/knight_support_obstruction_20261005.json'
    if destination.exists() or not destination.parent.is_dir():raise ValueError('fresh output preflight prevents rerun')
    paths=[PROTOCOL,'scripts/audit_knight_support_obstruction.py','scripts/audit_shogi_target_role_controls.py',
           'scripts/owned_service_reward.py','scripts/owned_tag_trace.py','scripts/public_goal_intervals.py',
           'scripts/audit_exchange_custody.py','scripts/resource_mode_context.py',
           'generic_chess/core/semantic_executor.py','generic_chess/rules/standard_shogi.py']
    report=dict(source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                public_transitions=0,enumerated=0,rows=[],pruned={},root_coverage_complete=False,
                root_value_interval=[0,1],all_controls_complete=False)
    try:audit(report)
    except Exception as e:report['error']=f'{type(e).__name__}: {e}'
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in report['source_sha256'].items())
    destination.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','root_state','root_actions','rows','pruned')},default=str))
    print(json.dumps([dict(square=r['square'],complete=r['complete'],enemy_choices=len(r.get('enemy_actions',[])),
                          last_own_choices=len(r.get('last_own_actions',[])),value=r['interval']) for r in report['rows']]))
