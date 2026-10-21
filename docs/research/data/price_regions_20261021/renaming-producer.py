"""Full finite-game type-renaming control, not a general isomorphism API."""
from dataclasses import replace
from fractions import Fraction
import json
import sys,hashlib
from pathlib import Path
from generic_chess.rules.schema import ruleset_from_dict,ruleset_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove,action_from_dict,action_to_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.limits import SearchLimits
from scripts.price_regions import CONFIG,Budget
from scripts.research_record import write_record,record_value

source=json.loads(Path('artifacts/price-regions-20261021/goal-census.json').read_text())
rule=ruleset_from_dict(source['rule'])
rename=(dict(p.split('=') for p in sys.argv[1].split(',')) if len(sys.argv)>1 else {'B':'Z','H':'H','K':'K'})
assert set(rename)=={'B','H','K'} and len(set(rename.values()))==3
output=Path(sys.argv[2]) if len(sys.argv)>2 else Path('artifacts/price-regions-20261021/goal-type-renaming.json')
if output.exists():raise FileExistsError(output)
new=replace(rule,piece_types=tuple(replace(p,type_id=rename[p.type_id],
        promotion_target_ids=tuple(rename[t] for t in p.promotion_target_ids)) for p in rule.piece_types),
    initial_position=tuple(tuple(None if p is None else Piece(p.owner,rename[p.base_type_id],rename[p.current_type_id],p.promoted)
        for p in row) for row in rule.initial_position),
    drop_allowed={rename[t]:v for t,v in rule.drop_allowed.items()},
    semantic_actions=tuple(replace(a,type_ids=tuple(rename[t] for t in a.type_ids)) for a in rule.semantic_actions))
oldc,newc=map(compile_ruleset_for_execution,(rule,new))

def descriptor(c,p,transform):
    d=record_value(p);d.pop('name');d.pop('pattern_id')
    gs=[]
    for gid in p.geometry_ids:
        g=record_value(c.ir.geometry[gid]);g.pop('geometry_id');g.pop('paths')
        if g['atom_source'] is not None:g['atom_source'][0]=transform[g['atom_source'][0]]
        gs.append(g)
    d['geometry_ids']=gs
    def types(v):
        if isinstance(v,dict):
            return {k:(transform[x] if k in ('type_id','explicit_promotion_type') and x is not None
                       else [transform[t] for t in x] if k=='type_ids' else types(x)) for k,x in v.items()}
        if isinstance(v,list):return [types(x) for x in v]
        return v
    d=types(d)
    # This scoped mapping renames typed references, not display names;
    # the full finite-tree check below validates the actual executable result.
    return json.dumps(d,sort_keys=True)

idmap={t:t for t in rename.values()};pm={};gm={}
for p in oldc.ir.patterns:
    candidates=[q for q in newc.ir.patterns if descriptor(oldc,p,rename)==descriptor(newc,q,idmap)]
    q,=candidates
    pm[p.pattern_id]=q.pattern_id
    for a,b in zip(p.geometry_ids,q.geometry_ids):
        assert a not in gm or gm[a]==b
        gm[a]=b
assert len(set(pm.values()))==len(pm)
assert len(set(gm.values()))==len(gm)

def action(a,patterns=pm,geometries=gm,types=rename):
    if isinstance(a,SemanticBoardMove):
        return replace(a,pattern_id=patterns[a.pattern_id],geometry_id=geometries[a.geometry_id],
            actor_type_id=types[a.actor_type_id])
    if isinstance(a,SemanticDropMove):
        return replace(a,pattern_id=patterns[a.pattern_id],geometry_id=geometries[a.geometry_id],
            base_type_id=types[a.base_type_id])
    raise AssertionError('Authored semantic world emitted an unhandled action type')

budget=Budget(90,100000);keys={};inversekeys={};counts={'nodes':0,'edges':0,'terminals':0}

def compare(a,b):
    budget.check();counts['nodes']+=1
    board=tuple(None if p is None else Piece(p.owner,rename[p.base_type_id],rename[p.current_type_id],p.promoted)
                for p in a.position.board)
    hands=tuple(Hands(tuple(sorted((rename[t],n) for t,n in h.counts))) for h in a.position.hands)
    assert replace(a.position,board=board,hands=hands,ruleset_fingerprint=newc.ruleset_fingerprint)==b.position
    assert a.ply_count==b.ply_count and a.terminal_status==b.terminal_status
    assert len(a.history)==len(b.history)
    for x,y in zip(a.history,b.history):
        keys.setdefault(x.position_key,y.position_key);inversekeys.setdefault(y.position_key,x.position_key)
        assert keys[x.position_key]==y.position_key and inversekeys[y.position_key]==x.position_key
        assert (x.actor,x.gave_check)==(y.actor,y.gave_check)
        if x.action_signature:
            assert action_to_dict(action(action_from_dict(json.loads(x.action_signature))))==json.loads(y.action_signature)
        else:assert not y.action_signature
    assert sorted((keys[k],n) for k,n in a.repetition_counts)==sorted(b.repetition_counts)
    if a.terminal_status.is_terminal:
        counts['terminals']+=1;return
    successors=legal_successors(a,oldc);target=dict(legal_successors(b,newc))
    assert {action(x) for x,_ in successors}==set(target)
    for x,child in successors:
        counts['edges']+=1
        compare(child,target[action(x)])

compare(GameSession(oldc).state,GameSession(newc).state)
oldprofile,_=build_semantic_opportunity_profile(oldc,CONFIG)
newprofile,_=build_semantic_opportunity_profile(newc,CONFIG)
assert {rename[t]:v for t,v in oldprofile.board_value_by_type.items()}==dict(newprofile.board_value_by_type)
pm_inv={v:k for k,v in pm.items()};gm_inv={v:k for k,v in gm.items()};types_inv={v:k for k,v in rename.items()}
profile=replace(newprofile,board_value_by_type={rename['K']:0,rename['H']:1000,rename['B']:1000},
    hand_value_by_base_type={t:0 for t in rename.values()},promotion_gain_by_type={t:0 for t in rename.values()})
rows=[]
for r in source['roots']:
    rec=deserialize_game_record(json.dumps(r['record']))
    s=GameSession(newc)
    for a in rec.actions:s.submit(action(a))
    if s.state.terminal_status.is_terminal:continue
    player=AlphaBetaPlayer(newc,evaluator_override=Evaluator(newc,profile,CONFIG),use_disk_cache=False,
        use_tt=False,use_ordering=False,use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
    d=player.choose_action(s,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=3,
        quiescence_max_depth=0,quiescence_hard_max_depth=0))
    assert d.completed_depth==2
    mapped=action(d.action,pm_inv,gm_inv,types_inv)
    truth={a['action']:a['wdl'] for a in r['true_actions']}
    old=next(x for x in r['public'] if x['H']==1000)
    rows.append(dict(mass=r['mass'],old_decision=old['decision'],old_wdl=old['selected_wdl'],
        renamed_decision=record_value(d),mapped_back_action=str(mapped),renamed_selected_wdl=truth[str(mapped)]))
write_record(output,
    dict(scope='Complete reachable max_ply6 game-tree type-renaming control on one authored3x3 world only.',
        producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),new_rule=ruleset_to_dict(new),renaming=rename,geometry_map=gm,pattern_map=pm,full_tree=counts,
        identity_bijection_size=len(keys),profile_renaming_equal=True,policy_roots=rows))
print(counts)
print([(r['mass'],r['old_wdl'],r['renamed_selected_wdl'],r['mapped_back_action']) for r in rows])
