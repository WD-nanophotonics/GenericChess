"""Scoped full-typed renaming on the existing mixed lifecycle, not an API.

Checks exactly roots4/5/6 plus their complete depth2 trees. No whole-game,
all-domain, learned-transfer or WDL claim follows from this comparison.
"""
import argparse,json,time
from collections import Counter
from fractions import Fraction
from dataclasses import replace
from pathlib import Path
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove,action_to_dict,action_from_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.transition import legal_successors
from generic_chess.rules.schema import ruleset_to_dict,ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution,lower_legacy_to_ir
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.price_regions import Budget,build_tree,response
from scripts.price_regions_mixed import fixture,counts,project,CONFIG
from scripts.research_record import record_value,write_record

RENAME={'K':'anchor_z','R':'z_rook','TP':'a_promoted'}
SINGLE={'type_id','base_type_id','current_type_id','actor_type_id','promotion_target_id','explicit_promotion_type'}
MANY={'type_ids','promotion_target_ids'}
MAPS={'drop_allowed','promotion_allowed','promotion_forced'}

def typed(v,key='',rename=RENAME):
    if key in SINGLE and v is not None:return rename[v]
    if key in MANY:return [rename[t] for t in v]
    if key in MAPS:return {rename[k]:typed(x,rename=rename) for k,x in v.items()}
    if isinstance(v,dict):return {k:typed(x,k,rename) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [typed(x,rename=rename) for x in v]
    return v


def run(source,output):
    if output.exists():raise FileExistsError(output)
    saved=json.loads(source.read_text());rule=fixture();new_rule=ruleset_from_dict(typed(ruleset_to_dict(rule)))
    oldc,newc=map(compile_ruleset_for_execution,(rule,new_rule));identity={t:t for t in RENAME.values()}
    baselines={id(c):{p.pattern_id:p for p in lower_legacy_to_ir(c._legacy_compiled).patterns} for c in (oldc,newc)}
    def descriptor(c,p,rename):
        d=record_value(p);d.pop('name');d.pop('pattern_id');geometry=[]
        for gid in p.geometry_ids:
            g=record_value(c.ir.geometry[gid]);g.pop('geometry_id');g.pop('paths')
            if g['atom_source'] is not None:g['atom_source'][0]=rename[g['atom_source'][0]]
            geometry.append(g)
        d['geometry_ids']=geometry
        # Provenance IDs are renumbered too: compare the actual suppressed baseline descriptors.
        d['replaced_pattern_ids']=[descriptor(c,baselines[id(c)][pid],rename) for pid in p.replaced_pattern_ids]
        return json.dumps(typed(d,rename=rename),sort_keys=True)
    patterns={};geometries={}
    for p in oldc.ir.patterns:
        q,=[q for q in newc.ir.patterns if descriptor(oldc,p,RENAME)==descriptor(newc,q,identity)]
        patterns[p.pattern_id]=q.pattern_id
        for a,b in zip(p.geometry_ids,q.geometry_ids):
            assert a not in geometries or geometries[a]==b;geometries[a]=b
    assert len(set(patterns.values()))==len(patterns) and len(set(geometries.values()))==len(geometries)
    def action(a):
        common=dict(pattern_id=patterns[a.pattern_id],geometry_id=geometries[a.geometry_id])
        if isinstance(a,SemanticBoardMove):return replace(a,**common,actor_type_id=RENAME[a.actor_type_id],
            promotion_target_id=None if a.promotion_target_id is None else RENAME[a.promotion_target_id])
        if isinstance(a,SemanticDropMove):return replace(a,**common,base_type_id=RENAME[a.base_type_id])
        raise AssertionError(type(a))
    keys={};inverse={};stats=Counter();budget=Budget(90,25000);start=time.perf_counter()
    def compare(a,b,depth):
        budget.check();stats['states']+=1
        board=tuple(None if p is None else Piece(p.owner,RENAME[p.base_type_id],RENAME[p.current_type_id],p.promoted) for p in a.position.board)
        hands=tuple(Hands(tuple(sorted((RENAME[t],n) for t,n in h.counts))) for h in a.position.hands)
        assert replace(a.position,board=board,hands=hands,ruleset_fingerprint=newc.ruleset_fingerprint)==b.position
        assert a.terminal_status==b.terminal_status and a.ply_count==b.ply_count and len(a.history)==len(b.history)
        for x,y in zip(a.history,b.history):
            keys.setdefault(x.position_key,y.position_key);inverse.setdefault(y.position_key,x.position_key)
            assert keys[x.position_key]==y.position_key and inverse[y.position_key]==x.position_key
            assert (x.actor,x.gave_check)==(y.actor,y.gave_check)
            assert (action_to_dict(action(action_from_dict(json.loads(x.action_signature)))) if x.action_signature else None)==(
                json.loads(y.action_signature) if y.action_signature else None)
        assert sorted((keys[k],n) for k,n in a.repetition_counts)==sorted(b.repetition_counts)
        if depth==0 or a.terminal_status.is_terminal:return
        old=legal_successors(a,oldc);new=dict(legal_successors(b,newc));assert {action(x) for x,_ in old}==set(new)
        for x,child in old:
            stats['edges']+=1
            stats['drops']+=isinstance(x,SemanticDropMove)
            stats['explicit_target_actions']+=getattr(x,'promotion_target_id',None) is not None
            # A semantic promote effect can leave the action target field empty.
            stats['promotion_effects']+=sum(p is not None and p.promoted for p in child.position.board)>sum(p is not None and p.promoted for p in a.position.board)
            stats['hand_changes']+=a.position.hands!=child.position.hands
            stats['aux_changes']+=a.position.aux_state!=child.position.aux_state
            compare(child,new[action(x)],depth-1)
    oldprofile,_=build_semantic_opportunity_profile(oldc,CONFIG);newprofile,_=build_semantic_opportunity_profile(newc,CONFIG)
    profile_equal={RENAME[t]:v for t,v in oldprofile.board_value_by_type.items()}==dict(newprofile.board_value_by_type)
    report=dict(scope=__doc__,renaming=RENAME,new_rule=ruleset_to_dict(new_rule),
        declaration=dict(roots=[4,5,6],depth=2,nodes=25000,seconds=90,table_r=[250,1000,4000],tp=1000,hand_fraction='9/10',
            public_seconds=5,q=0,tt=False,ordering=False),profile_renaming_equal=profile_equal,roots=[])
    write_record(output,report)
    for row in saved['roots']:
        rec=deserialize_game_record(json.dumps(row['record']));old=GameSession.replay(oldc,rec);new=GameSession(newc)
        for x in rec.actions:new.submit(action(x))
        compare(old.state,new.state,2);checks=[]
        forms=set();tree=build_tree(old.state,oldc,2,old.state.position.side_to_move,budget,forms,leaf_features=counts)
        projected=project(tree,900,set())
        for r in (250,1000,4000):
            table={'K':0,'R':r,'TP':1000};hand={'K':0,'R':r*9//10,'TP':900}
            decisions=[]
            for c,s,p,t,h in ((oldc,old,oldprofile,table,hand),(newc,new,newprofile,{RENAME[k]:v for k,v in table.items()},{RENAME[k]:v for k,v in hand.items()})):
                ev=Evaluator(c,replace(p,board_value_by_type=t,hand_value_by_base_type=h,promotion_gain_by_type={k:0 for k in t}),CONFIG)
                pl=AlphaBetaPlayer(c,evaluator_override=ev,use_disk_cache=False,use_tt=False,use_ordering=False,
                    use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
                before=s.state;d=pl.choose_action(s,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=5,
                    quiescence_max_depth=0,quiescence_hard_max_depth=0));assert s.state==before and d.completed_depth==2
                decisions.append(d)
            a,b=decisions;assert a.score==b.score
            expected,actions=response(projected,Fraction(r,1000))
            assert a.score==expected and str(a.action) in actions
            assert b.action in {action(x) for x in old.legal_actions() if str(x) in actions}
            mapped=action(a.action);same=mapped==b.action
            checks.append(dict(r=r,old=record_value(a),new=record_value(b),mapped_old_action=record_value(mapped),same_tied_selection=same,expected_actions=actions))
        report['roots'].append(dict(ply=old.state.ply_count,source_record=row['record'],
            new_record=json.loads(serialize_game_record(new.to_record())),aux=record_value(old.state.position.aux_state),checks=checks))
        write_record(output,report)
    report.update(stats=dict(stats),position_key_bijection=len(keys),wall_seconds=time.perf_counter()-start)
    write_record(output,report);print(report['stats'],profile_equal,report['position_key_bijection'],report['wall_seconds'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.source,a.output)
