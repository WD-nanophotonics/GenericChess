"""One frozen changed-premise held-P pin-support strategy; complete adversary, no valuation labels."""
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
PROTOCOL = 'docs/research/HELD_P_PIN_SUPPORT_CERTIFICATE_PROTOCOL.md'
SHA = '81eb8e68e909598b28b63c8e05ebcda04cd961dd5320f4b36f612d8baeadf596'

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
        if report['public_transitions'] >= 64:
            raise Limit('64 transitions cap')
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
        board = [None]*81
        for square,owner,base in [(0,0,'K'),(53,1,'K'),(45,0,'R'),(49,1,'P'),(59,1,'P')]:
            board[square] = Piece(owner,base,base,False)
        pos = replace(initial_state(compiled).position, board=tuple(board), hands=(Hands((('P',1),)),Hands()), side_to_move=0)
        state = synthetic_state(compiled,pos)
        try:
            resource_ledger(compiled,pos,'shogi')
        except ValueError as error:
            if 'global base inventory' not in str(error):
                raise
        else:
            raise ValueError('sparse stock wrongly accepted')
        stock = Counter(p.base_type_id for p in compiled.initial_position.board if p)
        actual = Counter(p.base_type_id for p in pos.board if p); actual.update(dict(pos.hands[0].items()))
        report['missing_tokens'] = sum((stock-actual).values())
        if report['missing_tokens'] != 34:
            raise ValueError('declared sparse stock mismatch')
        source = dict(owner=0,base='P',board={},held=F(1),lost=F(0))
        target = dict(owner=1,base='P',board={49:F(1)},held=F(0),lost=F(0))
        report['root_state'] = asdict(state)
        choices = table(state,source); report['root_actions'] = list(choices[0])
        key = select(choices,lambda a:sq(a) is None and sq(a,True)==40 and getattr(a,'base_type_id',None)=='P')
        report['strategy_first_action'] = key
        state,source,target,_ = step(state,source,target,choices,key)
        choices = table(state,source); report['first_enemy_actions'] = list(choices[0])
        for key in choices[0]:
            row = {'enemy_first':key,'leaves':[],'complete':False}; report['branches'].append(row)
            child,s,t,_ = step(state,source,target,choices,key)
            if len(t['board']) != 1 or sum(t['board'].values()) != 1:
                raise ValueError('target not unambiguous/live after first reply')
            destination = next(iter(t['board']))
            own = table(child,s); row['own_actions'] = list(own[0])
            capture = select(own,lambda a:sq(a)==40 and sq(a,True)==destination and getattr(a,'promotion_target_id',None) is None)
            row['own_capture'] = capture
            after,s,t,reward = step(child,s,t,own,capture)
            if reward != 1 or t['lost'] != 1 or sum(s['board'].values()) != 1:
                raise AssertionError('designated removal by source not established')
            final = table(after,s); row['enemy_final_actions'] = list(final[0])
            for reply in final[0]:
                leaf,ls,lt,_ = step(after,s,t,final,reply)
                alive = sum(ls['board'].values())+ls['held']
                success = alive == 1 and lt['lost'] == 1
                row['leaves'].append(dict(enemy_final=reply,state_sha256=digest(leaf),source=ls,target=lt,success=success))
                if not success:
                    raise ValueError('fixed strategy refuted by actual leaf')
            row['complete'] = True
        report['strategy_interval'] = [1,1]
        report['task_value_interval'] = [1,1]
        report['all_adversary_branches_complete'] = True
    finally:
        report['seconds'] = monotonic()-start

if __name__ == '__main__':
    destination = ROOT/'docs/research/data/held_p_pin_support_certificate_20261004.json'
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError('destination preflight prevents rerun')
    paths = [PROTOCOL,'scripts/audit_held_p_pin_support_certificate.py','scripts/audit_shogi_target_role_controls.py',
             'scripts/owned_service_reward.py','scripts/owned_tag_trace.py','scripts/public_goal_intervals.py',
             'scripts/audit_exchange_custody.py','scripts/resource_mode_context.py',
             'generic_chess/core/semantic_executor.py','generic_chess/rules/standard_shogi.py']
    report = dict(source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                  public_transitions=0,enumerated=0,branches=[],strategy_interval=[0,1],task_value_interval=[0,1],
                  all_adversary_branches_complete=False)
    try:
        audit(report)
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in report['source_sha256'].items())
    destination.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','branches','root_state','root_actions','first_enemy_actions')},default=str))
    print(json.dumps(dict(root_choices=len(report.get('root_actions',[])),first_replies=len(report.get('first_enemy_actions',[])),
                          final_leaves=sum(len(r['leaves']) for r in report['branches']))))
