"""Frozen matched board/held Knight support pair; complete adversary, no valuation labels."""
from collections import Counter
from dataclasses import asdict, replace
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_shogi_target_role_controls import (
    Piece, Hands, semantic_engine_for, _semantic_public_action, initial_state,
    compile_ruleset_for_execution, build_standard_shogi_ruleset, synthetic_state,
    binding_reward, public_child_reward, trace_tag, PublicGame, resource_ledger,
    action_source_square, action_target_square)
PROTOCOL = 'docs/research/KNIGHT_MODE_SUPPORT_PAIR_PROTOCOL.md'
SHA = 'cd532bd4415355c7f48db77c30dbb31f87014f1a9f472d946c4be281c1007b7c'

class Limit(Exception):
    pass

def audit(report):
    start = monotonic()
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest() != SHA:
        raise ValueError('frozen protocol drift')
    def check():
        if monotonic()-start >= 15:
            raise Limit('15-second cap')
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    game = PublicGame(compiled); engine = semantic_engine_for(compiled)
    def table(state, tag):
        terminal = game.terminal(state)
        if terminal.is_terminal:
            raise ValueError('expected ongoing state; no endpoint inference')
        public = {}; bindings = {}; rewards = {}
        def tick():
            check()
            if report['enumerated'] >= 5000:
                raise Limit('5000 enumeration cap')
            report['enumerated'] += 1
        for a in game.actions(state, check):
            tick(); key = str(a)
            if key in public or len(public) >= 128:
                raise ValueError('public action bound/identity')
            public[key] = a
        for runtime, binding in engine.iter_legal_action_bindings(state.position, checkpoint=check):
            tick(); key = str(_semantic_public_action(engine, runtime))
            if key in bindings or len(bindings) >= 128:
                raise ValueError('binding bound/identity')
            bindings[key] = (runtime, binding)
            rewards[key] = binding_reward(engine, state.position, runtime, binding, tag)
        if not public or public.keys() != bindings.keys():
            raise ValueError('unsupported claim or incomplete action match')
        return public, bindings, rewards
    def sq(a, target=False):
        s = (action_target_square if target else action_source_square)(a)
        return None if s is None else 9*s.rank+s.file
    def select(choices, predicate):
        keys = [k for k,a in choices[0].items() if predicate(a)]
        if len(keys) != 1:
            raise ValueError('unique frozen strategy action absent')
        return keys[0]
    def digest(state):
        return hashlib.sha256(json.dumps(asdict(state), sort_keys=True, default=str).encode()).hexdigest()
    def step(state, source, target, choices, key):
        check()
        if report['public_transitions'] >= 128:
            raise Limit('128 shared transitions cap')
        child = game.successor(state, choices[0][key]); report['public_transitions'] += 1
        runtime, binding = choices[1][key]
        reward = public_child_reward(state.position, child.position, choices[0][key], source, compiled.support.type_metadata)
        if reward != choices[2][key]:
            raise AssertionError('public/binding reward mismatch')
        new_source = trace_tag(engine, state.position, child.position, runtime, binding, source)
        new_target = trace_tag(engine, state.position, child.position, runtime, binding, target)
        if child.ply_count != state.ply_count+1 or len(child.history) != len(state.history)+1:
            raise AssertionError('actual history drift')
        endpoint = game.terminal(child)
        if endpoint.is_terminal:
            raise ValueError('early endpoint unsupported in this actual witness')
        check()
        return child,new_source,new_target,reward
    try:
        for location in ('board','held'):
            row=dict(location=location,branches=[],complete=False,strategy_interval=[0,1],task_value_interval=[0,1])
            report['rows'].append(row)
            board=[None]*81
            for square,owner,base in [(0,0,'K'),(62,1,'K'),(54,0,'R'),(49,1,'P'),(59,1,'P')]:
                board[square]=Piece(owner,base,base,False)
            if location=='board':
                board[40]=Piece(0,'N','N',False)
            hands=(Hands(),Hands()) if location=='board' else (Hands((('N',1),)),Hands())
            pos=replace(initial_state(compiled).position,board=tuple(board),hands=hands,side_to_move=0)
            state=synthetic_state(compiled,pos)
            try:
                resource_ledger(compiled,pos,'shogi')
            except ValueError as error:
                if 'global base inventory' not in str(error):raise
            else:raise ValueError('sparse inventory incorrectly accepted')
            stock=Counter(p.base_type_id for p in compiled.initial_position.board if p)
            actual=Counter(p.base_type_id for p in pos.board if p);actual.update(dict(pos.hands[0].items()))
            row['missing_tokens']=sum((stock-actual).values())
            if row['missing_tokens']!=34:raise ValueError('resource deficit mismatch')
            source=dict(owner=0,base='N',board={40:F(1)} if location=='board' else {},held=F(int(location=='held')),lost=F(0))
            target=dict(owner=1,base='P',board={59:F(1)},held=F(0),lost=F(0))
            row['root_state']=asdict(state)
            choices=table(state,source);row['root_actions']=list(choices[0])
            if location=='board':
                first=select(choices,lambda a:sq(a)==40 and sq(a,True)==59 and getattr(a,'promotion_target_id',None) is None)
            else:
                first=select(choices,lambda a:sq(a) is None and sq(a,True)==42 and getattr(a,'base_type_id',None)=='N')
            row['first_action']=first
            state,source,target,reward=step(state,source,target,choices,first)
            if reward!=int(location=='board'):raise AssertionError('fixed first reward mismatch')
            row['first_reward']=reward
            enemy=table(state,source);row['enemy_first_actions']=list(enemy[0])
            for first_reply in enemy[0]:
                branch=dict(enemy_first=first_reply,leaves=[],complete=False);row['branches'].append(branch)
                child,src,tgt,_=step(state,source,target,enemy,first_reply)
                own=table(child,src);branch['own_actions']=list(own[0])
                if location=='board':
                    second=select(own,lambda a:sq(a)==0 and sq(a,True)==1 and getattr(a,'promotion_target_id',None) is None)
                else:
                    if tgt['board']!={59:F(1)}:raise ValueError('designated target moved despite frozen pin')
                    second=select(own,lambda a:sq(a)==42 and sq(a,True)==59 and getattr(a,'promotion_target_id',None) is None)
                branch['second_action']=second
                after,src,tgt,reward=step(child,src,tgt,own,second)
                if reward!=int(location=='held') or tgt['lost']!=1:raise AssertionError('completion reward mismatch')
                final=table(after,src);branch['enemy_final_actions']=list(final[0])
                for final_reply in final[0]:
                    leaf,ls,lt,_=step(after,src,tgt,final,final_reply)
                    success=sum(ls['board'].values())+ls['held']==1 and lt['lost']==1
                    branch['leaves'].append(dict(enemy_final=final_reply,state_sha256=digest(leaf),source=ls,target=lt,success=success))
                    if not success:raise ValueError('fixed strategy refuted')
                branch['complete']=True
            row.update(complete=True,strategy_interval=[1,1],task_value_interval=[1,1])
        report['all_controls_complete']=True
    finally:
        report['seconds'] = monotonic()-start

if __name__ == '__main__':
    destination = ROOT/'docs/research/data/knight_mode_support_pair_20261005.json'
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError('destination preflight prevents rerun')
    paths = [PROTOCOL,'scripts/audit_knight_mode_support_pair.py','scripts/audit_shogi_target_role_controls.py',
             'scripts/owned_service_reward.py','scripts/owned_tag_trace.py','scripts/public_goal_intervals.py',
             'scripts/audit_exchange_custody.py','scripts/resource_mode_context.py',
             'generic_chess/core/semantic_executor.py','generic_chess/rules/standard_shogi.py']
    report = dict(source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                  public_transitions=0,enumerated=0,rows=[],all_controls_complete=False)
    try:
        audit(report)
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in report['source_sha256'].items())
    destination.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','rows')},default=str))
    print(json.dumps([dict(location=r['location'],complete=r['complete'],root_choices=len(r.get('root_actions',[])),first_replies=len(r.get('enemy_first_actions',[])),leaves=sum(len(b['leaves']) for b in r['branches']),value=r['task_value_interval']) for r in report['rows']]))
