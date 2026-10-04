"""One frozen public-noise root; own max, complete uniform enemy choices."""
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
from scripts.public_task_intervals import public_choice_bound

PROTOCOL = 'docs/research/HELD_KNIGHT_PUBLIC_NOISE_PROTOCOL.md'
SHA = '2f8b415d9f0b0d07643b25ca287248c4419812fb04abb4099eb0cc3e478d8486'
SQUARES = (31, 33, 40, 42)


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
        if game.terminal(state).is_terminal:
            raise ValueError('unexpected terminal; unresolved task frontier')
        public = {}; bindings = {}; rewards = {}

        def tick():
            check()
            if report['enumerated'] >= 5000:
                raise Limit('5000 enumeration cap')
            report['enumerated'] += 1

        for a in game.actions(state, check):
            tick(); key = str(a)
            if key in public or len(public) >= 128:
                raise ValueError('public choice identity/bound')
            public[key] = a
        for runtime, binding in engine.iter_legal_action_bindings(state.position, checkpoint=check):
            tick(); key = str(_semantic_public_action(engine, runtime))
            if key in bindings or len(bindings) >= 128:
                raise ValueError('binding identity/bound')
            bindings[key] = (runtime, binding)
            rewards[key] = binding_reward(engine, state.position, runtime, binding, tag)
        if not public or public.keys() != bindings.keys():
            raise ValueError('complete public/binding correspondence required')
        return public, bindings, rewards

    def sq(a, target=False):
        s = (action_target_square if target else action_source_square)(a)
        return None if s is None else 9*s.rank+s.file

    def step(state, source, target, choices, key):
        check()
        if report['public_transitions'] >= 128:
            raise Limit('128 global transitions cap')
        child = game.successor(state, choices[0][key]); report['public_transitions'] += 1
        runtime, binding = choices[1][key]
        reward = public_child_reward(state.position, child.position, choices[0][key], source,
                                    compiled.support.type_metadata)
        if reward != choices[2][key]:
            raise AssertionError('binding/public reward mismatch')
        src = trace_tag(engine, state.position, child.position, runtime, binding, source)
        tgt = trace_tag(engine, state.position, child.position, runtime, binding, target)
        if child.ply_count != state.ply_count+1 or len(child.history) != len(state.history)+1:
            raise AssertionError('actual history advancement required')
        if game.terminal(child).is_terminal:
            raise ValueError('early terminal remains unknown')
        check()
        return child, src, tgt, reward

    def digest(state):
        return hashlib.sha256(json.dumps(asdict(state), sort_keys=True, default=str).encode()).hexdigest()

    try:
        board = [None]*81
        for point,owner,base in [(0,0,'K'),(62,1,'K'),(49,1,'P'),(59,1,'P')]:
            board[point] = Piece(owner,base,base,False)
        pos = replace(initial_state(compiled).position, board=tuple(board),
                      hands=(Hands((('N',1),)),Hands()), side_to_move=0)
        state = synthetic_state(compiled,pos)
        try:
            resource_ledger(compiled,pos,'shogi')
        except ValueError as error:
            if 'global base inventory' not in str(error):
                raise
        else:
            raise ValueError('sparse root incorrectly accepted by stock guard')
        stock = Counter(p.base_type_id for p in compiled.initial_position.board if p)
        actual = Counter(p.base_type_id for p in board if p)
        actual.update(dict(pos.hands[0].items()))
        report['missing_tokens'] = sum((stock-actual).values())
        if report['missing_tokens'] != 35:
            raise ValueError('unexpected resource deficit')
        source = dict(owner=0,base='N',board={},held=F(1),lost=F(0))
        target = dict(owner=1,base='P',board={59:F(1)},held=F(0),lost=F(0))
        report['root_state'] = asdict(state)
        root = table(state,source); report['root_actions'] = list(root[0])
        selected = {}
        for key,a in root[0].items():
            p,q = sq(a),sq(a,True)
            if p is None and getattr(a,'base_type_id',None)=='N':
                if q in SQUARES:
                    if q in selected:
                        raise ValueError('nonunique source drop')
                    selected[q] = key
                else:
                    report['pruned'][key] = 'drop not a native-N preimage of target f7/f6 on last own move'
            elif p==0 and getattr(a,'promotion_target_id',None) is None:
                report['pruned'][key] = 'first King move leaves held source unable to capture on last drop'
            else:
                raise ValueError('unsupported first action invalidates pruning proof')
        if set(selected) != set(SQUARES):
            raise ValueError('all four frozen legal first drops required')
        report['root_coverage_complete'] = True
        for point in SQUARES:
            row = dict(square=point, first=selected[point], branches={}, complete=False,
                       value_interval=[F(0),F(1)])
            report['rows'].append(row)
            after,src,tgt,reward = step(state,source,target,root,row['first'])
            if reward!=0 or src['board']!={point:F(1)}:
                raise AssertionError('actual held drop trace mismatch')
            enemy = table(after,src); row['enemy_first_actions'] = list(enemy[0])
            row['branches'] = {k:dict(interval=[F(0),F(1)], leaves=[], complete=False) for k in enemy[0]}
            for reply,branch in row['branches'].items():
                child,s,t,_ = step(after,src,tgt,enemy,reply)
                branch.update(source=s,target=t,state_sha256=digest(child))
                if s['lost']==1:
                    branch.update(interval=[F(0),F(0)],complete=True,proof='physical source lost')
                    continue
                if s['board']!={point:F(1)} or t['board'] not in ({59:F(1)},{50:F(1)}):
                    raise ValueError('target/source geometry outside frozen proof')
                own = table(child,s); branch['own_actions'] = list(own[0])
                target_point = next(iter(t['board']))
                capture = [k for k,a in own[0].items() if sq(a)==point and sq(a,True)==target_point
                           and getattr(a,'promotion_target_id',None) is None]
                if not capture:
                    # Native-N second move cannot capture otherwise; promoted alternatives
                    # use the same source/target displacement before optional promotion.
                    if any(sq(a)==point and sq(a,True)==target_point for a in own[0].values()):
                        raise ValueError('promotion-only capture invalidates native pruning')
                    branch.update(interval=[F(0),F(0)],complete=True,proof='complete last-own-turn capture set empty')
                    continue
                if len(capture)!=1:
                    raise ValueError('nonunique unpromoted capture')
                branch['own_capture'] = capture[0]
                end,s2,t2,reward = step(child,s,t,own,capture[0])
                if reward!=1 or t2['lost']!=1 or sum(s2['board'].values())+s2['held']!=1:
                    raise AssertionError('source capture did not complete designated task')
                final = table(end,s2); branch['enemy_final_actions'] = list(final[0])
                for last in final[0]:
                    leaf,ls,lt,_ = step(end,s2,t2,final,last)
                    success = lt['lost']==1 and sum(ls['board'].values())+ls['held']==1
                    branch['leaves'].append(dict(action=last,success=success,source=ls,target=lt,state_sha256=digest(leaf)))
                    if not success:
                        raise ValueError('selected strategy not all-one; own max unresolved')
                branch.update(interval=[F(1),F(1)],complete=True,proof='all final replies1; binary own-max domination')
            row['complete'] = True
        report['all_controls_complete'] = True
    finally:
        # Preserve complete denominators and unknown unvisited branches even on interruption.
        for row in report['rows']:
            if row['branches']:
                row['value_interval'] = [sum((b['interval'][i] for b in row['branches'].values()),F(0))/len(row['branches'])
                                         for i in (0,1)]
        bounds = {str(r['square']):r['value_interval'] for r in report['rows']}
        if report['pruned']:
            bounds['geometrically_pruned'] = [F(0),F(0)]
        report['root_value_interval'] = public_choice_bound(bounds,maximize=True,
                                            complete=report['root_coverage_complete'] and len(report['rows'])==4)
        report['seconds'] = monotonic()-start


if __name__ == '__main__':
    destination = ROOT/'docs/research/data/held_knight_public_noise_20261005.json'
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError('fresh output preflight prevents rerun')
    paths = [PROTOCOL,'scripts/audit_held_knight_public_noise.py','scripts/audit_shogi_target_role_controls.py',
             'scripts/owned_service_reward.py','scripts/owned_tag_trace.py','scripts/public_goal_intervals.py',
             'scripts/audit_exchange_custody.py','scripts/resource_mode_context.py','scripts/public_task_intervals.py',
             'generic_chess/core/semantic_executor.py','generic_chess/rules/standard_shogi.py']
    report = dict(source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                  public_transitions=0,enumerated=0,rows=[],pruned={},root_coverage_complete=False,
                  root_value_interval=[0,1],all_controls_complete=False)
    try:
        audit(report)
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
                                         for p,h in report['source_sha256'].items())
    destination.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','rows','pruned','root_actions','root_state')},default=str))
    print(json.dumps([dict(square=r['square'],replies=len(r['branches']),good=sum(b['interval']==[1,1] for b in r['branches'].values()),
                           leaves=sum(len(b['leaves']) for b in r['branches'].values()),value=r['value_interval'],complete=r['complete'])
                      for r in report['rows']],default=str))
