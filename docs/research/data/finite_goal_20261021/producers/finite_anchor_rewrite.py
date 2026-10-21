"""Finite whole-game control: replace legacy anchor atoms by equivalent DSL.

A scoped representation change, not new rules/solver or a tie-breaking patch.
The full reachable max_ply6 tree, attacks, hands and event histories are checked.
"""
from pathlib import Path
from dataclasses import replace
import argparse,json,time
from collections import Counter
from generic_chess.rules.schema import ruleset_from_dict,ruleset_to_dict,RuleSemanticAction,RuleGeometrySpec,RuleReplaceSelector,RuleActionEffect,RuleSquareRef,RuleInvariant
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.actions import SemanticBoardMove,action_from_dict,action_to_dict
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.benchmark.runner import play_game,RunConfig
from generic_chess.ai.benchmark.profiles import PROFILES
from scripts.price_regions import CONFIG,Budget
from scripts.research_record import record_value,write_record


def run(source_path,output):
    if output.exists():raise FileExistsError(output)
    source=json.loads(source_path.read_text());oldrule=ruleset_from_dict(source['rule']);actions=[]
    for relation in ('empty','enemy'):
        effects=() if relation=='empty' else (RuleActionEffect('remove',square_ref=RuleSquareRef('target'),piece_owner='opponent'),)
        actions.append(RuleSemanticAction(name='anchor_'+relation,type_ids=('K',),
            geometry=RuleGeometrySpec('legacy_atoms',atom_kind='leap'),target_relation=relation,
            composition='replace_legacy',replace_selector=RuleReplaceSelector(type_ids=('K',),action_family='board',
                target_relation=relation,geometry_kind='leap',replace_all_matching=True),
            effects=effects+(RuleActionEffect('move',from_ref=RuleSquareRef('source'),to_ref=RuleSquareRef('target')),),
            invariants=(RuleInvariant('own_anchor_safe'),)))
    newrule=replace(oldrule,semantic_actions=oldrule.semantic_actions+tuple(actions))
    oldc,newc=map(compile_ruleset_for_execution,(oldrule,newrule));oldpatterns={p.pattern_id:p for p in oldc.ir.patterns}
    repl={rel:next(p.pattern_id for p in newc.ir.patterns if p.name=='anchor_'+rel) for rel in ('empty','enemy')}
    def action(a):
        if isinstance(a,SemanticBoardMove) and a.actor_type_id=='K':
            rel=oldpatterns[a.pattern_id].target.kind.removeprefix('target_')
            return replace(a,pattern_id=repl[rel])
        return a
    keys={};inverse={};counts=Counter();budget=Budget(90,100000);start=time.perf_counter()
    engines=[semantic_engine_for(x) for x in (oldc,newc)]
    def compare(a,b):
        budget.check();counts['states']+=1
        assert replace(a.position,ruleset_fingerprint=newc.ruleset_fingerprint)==b.position
        assert a.ply_count==b.ply_count and a.terminal_status==b.terminal_status and len(a.history)==len(b.history)
        for x,y in zip(a.history,b.history):
            keys.setdefault(x.position_key,y.position_key);inverse.setdefault(y.position_key,x.position_key)
            assert keys[x.position_key]==y.position_key and inverse[y.position_key]==x.position_key
            assert (x.actor,x.gave_check)==(y.actor,y.gave_check)
            assert (action_to_dict(action(action_from_dict(json.loads(x.action_signature)))) if x.action_signature else None)==(json.loads(y.action_signature) if y.action_signature else None)
        assert sorted((keys[k],v) for k,v in a.repetition_counts)==sorted(b.repetition_counts)
        for side in (0,1):
            assert engines[0].attacked_squares(a.position,side)==engines[1].attacked_squares(b.position,side)
            counts['attack_maps']+=1
        if a.terminal_status.is_terminal:counts['terminals']+=1;return
        old=legal_successors(a,oldc);new=dict(legal_successors(b,newc));assert {action(x) for x,_ in old}==set(new)
        for x,child in old:counts['edges']+=1;compare(child,new[action(x)])
    compare(GameSession(oldc).state,GameSession(newc).state)
    report=dict(scope=__doc__,declaration=dict(tree_seconds=90,tree_nodes=100000,depths=[2,3],
        configs=['material','mobility2','mobility2_escape5'],scale=1,hand=0,q=0,tt=False,ordering=False,
        public_nodes=100000,public_seconds=5,games=2,game_root=3,fixed_foe_depth=3,game_nodes=4096,game_seconds=1),
        rule=ruleset_to_dict(newrule),replacement_patterns=repl,whole_tree=dict(counts),key_bijection=len(keys),checks=[],games=[])
    write_record(output,report)
    roots=[]
    for i,row in enumerate(source['roots']):
        old=GameSession.replay(oldc,deserialize_game_record(json.dumps(row['record'])));new=GameSession(newc)
        for x in old.to_record().actions:new.submit(action(x))
        if old.state.terminal_status.is_terminal:continue
        truth={x['action']:x['wdl'] for x in row['true_actions']};mapped_truth={str(action(x)):truth[str(x)] for x in old.legal_actions()}
        roots.append((i,old,new,truth,mapped_truth))
    def make(c,cfg,scale):
        profile,_=build_semantic_opportunity_profile(c,CONFIG)
        profile=replace(profile,board_value_by_type={'K':0,'H':scale,'B':scale},hand_value_by_base_type={'K':0,'H':0,'B':0},promotion_gain_by_type={'K':0,'H':0,'B':0})
        return AlphaBetaPlayer(c,evaluator_override=SemanticAttackEvaluator(c,profile,cfg,backend='core'),
            use_disk_cache=False,use_tt=False,use_ordering=False,use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
    for i,old,new,truth,mapped_truth in roots:
        for name,cfg in (('material',CONFIG),('mobility2',replace(CONFIG,dynamic_mobility_weight=2)),
                         ('mobility2_escape5',replace(CONFIG,dynamic_mobility_weight=2,anchor_escape_weight=5))):
            for depth in (2,3):
                pair=[]
                for c,s,w in ((oldc,old,truth),(newc,new,mapped_truth)):
                    before=s.state;pl=make(c,cfg,1);d=pl.choose_action(s,SearchLimits(max_depth=depth,max_nodes=100000,
                        max_time_seconds=5,quiescence_max_depth=0,quiescence_hard_max_depth=0))
                    assert d.completed_depth==depth and s.state==before
                    pair.append(dict(action=str(d.action),selected_wdl=w[str(d.action)],decision=record_value(d)))
                assert pair[0]['decision']['score']==pair[1]['decision']['score']
                report['checks'].append(dict(root=i,config=name,depth=depth,old=pair[0],rewritten=pair[1]))
        write_record(output,report)
    class Depth:
        def __init__(self,c,cfg,scale,depth):self.inner=make(c,cfg,scale);self.depth=depth;self.session=None
        def choose_action(self,s,limits):
            self.session=s;return self.inner.choose_action(s,replace(limits,max_depth=self.depth,quiescence_max_depth=0,quiescence_hard_max_depth=0))
    _,old,new,_,_=next(x for x in roots if x[0]==3)
    for label,c,s in (('original',oldc,old),('rewritten',newc,new)):
        candidate=Depth(c,replace(CONFIG,dynamic_mobility_weight=2),1,2);foe=Depth(c,CONFIG,1000,3)
        outcome,events=play_game(c,s.to_record().actions,label,'tie-mechanism',0,candidate,foe,
            RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),seconds=1,nodes=4096,max_plies=6))
        final=candidate.session or foe.session;assert final.state.terminal_status.is_terminal
        assert GameSession.replay(c,final.to_record()).state==final.state
        report['games'].append(dict(encoding=label,outcome=record_value(outcome),events=record_value(events),terminal=record_value(final.state.terminal_status),record=json.loads(serialize_game_record(final.to_record()))))
    report['wall_seconds']=time.perf_counter()-start;write_record(output,report)
    print(report['whole_tree']);print([(r['root'],r['config'],r['depth'],r['old']['selected_wdl'],r['rewritten']['selected_wdl']) for r in report['checks']]);print([(g['encoding'],g['outcome']['result']) for g in report['games']])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.source,a.output)
