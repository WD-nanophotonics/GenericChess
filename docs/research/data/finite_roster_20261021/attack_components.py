"""Posthoc component diagnosis on frozen first-divergence states; no games."""
from dataclasses import replace
from pathlib import Path
from collections import Counter
import json, time
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits

OUT = Path(__file__).resolve().parent / 'attack-utility'
plan = {'question': 'At actual first-divergence states, is the semantic score difference coverage, anchor heuristics, or both, and does it survive equal completed D1?',
        'selection': 'All eleven candidate-first divergences from the closed 64-slot panel, no replacements, posthoc diagnostic exposure',
        'arms': 'legacy/Core semantic/Native semantic authority x static-only/coverage-only/anchor-only/both; identical Unit profile and zero promotion gain',
        'limits': 'D1/q0/hardq0,100000 total nodes,5s cooperative query cap;120s total; all incomplete retained; no games',
        'decision': 'If authority differences vanish at equal D1, treat original action divergence as deeper/budget-dependent; if they persist, retain actual component witness but no utility/default claim. This diagnoses mechanism, never changes the frozen utility verdict.'}
(OUT/'component-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
games=[json.loads(x) for x in (OUT/'games.jsonl').read_text().splitlines()]
audit=json.loads((OUT/'audit.json').read_text())
rules=json.loads((OUT/'rules.json').read_text())
start=time.perf_counter(); results=[]; cache={}; maps=0; leaf_count=0
for entry in audit['trajectory_pairs']:
    if entry['class']!='candidate_first': continue
    seed=entry['seed']
    if seed not in cache:
        r=next(r for r in rules if r['seed']==seed)
        c=compile_ruleset_for_execution(ruleset_from_dict(r['definition']))
        cfg=EvaluationConfig(promotion_potential_weight=0)
        profile=build_ruleset_profile(c,cfg)
        values={p.type_id:0 if p.is_anchor else 1000 for p in c.piece_types}
        profile=replace(profile,piece_profiles={k:replace(v,normalized_board_value=values[k],normalized_hand_value=values[k],promotion_option_value=0) for k,v in profile.piece_profiles.items()},board_value_by_type=values,hand_value_by_base_type=values,promotion_gain_by_type={k:0 for k in values},median_non_anchor_value=1000)
        evaluators={}
        for component,(mob,anc) in {'static':(0,0),'coverage':(2,0),'anchor':(0,5),'both':(2,5)}.items():
            cfg=replace(cfg,dynamic_mobility_weight=mob,anchor_escape_weight=anc)
            evaluators[component]={a:(Evaluator(c,profile,cfg) if a=='legacy' else SemanticAttackEvaluator(c,profile,cfg,backend=a)) for a in ('legacy','core','native')}
        cache[seed]=(c,evaluators)
    c,evaluators=cache[seed]
    g=next(g for g in games if (g['seed'],g['prefix'],g['candidate_owner'],g['arm'])==(seed,entry['prefix'],entry['owner'],'legacy'))
    rec=deserialize_game_record(json.dumps(g['record']))
    rec=replace(rec,actions=rec.actions[:entry['prefix']+entry['first_different_ply']],resigned_by=None,declaration=None)
    s=GameSession.replay(c,rec);assert s.state.position.side_to_move==entry['owner']
    children=[]
    for action in s.legal_actions():
        child=GameSession.replay(c,rec);child.submit(action); scores={}
        for component,arms in evaluators.items():
            scores[component]={a:e.evaluate(child.state) for a,e in arms.items()}
            assert scores[component]['core']==scores[component]['native']
        for a in ('legacy','core','native'):
            assert scores['both'][a]==scores['coverage'][a]+scores['anchor'][a]-scores['static'][a]
        assert scores['static']['legacy']==scores['static']['core']
        ac=evaluators['both']['core']._attack_maps(child.state)
        an=evaluators['both']['native']._attack_maps(child.state)
        assert ac==an; maps+=1; leaf_count+=1
        children.append({'action':repr(action),'status':child.result.status.value,'winner':child.result.winner,'scores_stm':scores})
    queries=[]
    for component,arms in evaluators.items():
        for authority,evaluator in arms.items():
            if time.perf_counter()-start>=120:
                queries.append({'component':component,'authority':authority,'missing':True});continue
            player=AlphaBetaPlayer(c,evaluator_override=evaluator,use_disk_cache=False,use_tt=False,use_ordering=False,tt_max_entries=0,tuning=SearchTuning(use_root_tactical=False))
            before=time.perf_counter();d=player.choose_action(s,SearchLimits(max_depth=1,max_nodes=100000,max_time_seconds=5,quiescence_max_depth=0,quiescence_hard_max_depth=0))
            queries.append({'component':component,'authority':authority,'action':repr(d.action),'score':d.score,'depth':d.completed_depth,'nodes':d.nodes+d.qnodes,'reason':d.termination_reason,'caller_seconds':time.perf_counter()-before})
    results.append({'seed':seed,'prefix':entry['prefix'],'owner':entry['owner'],'divergence':entry['first_different_ply'],'children':children,'queries':queries})
summary={'states':len(results),'child_observations':leaf_count,'Core_Native_child_map_checks':maps,'queries':sum(len(r['queries']) for r in results),'missing_queries':sum(q.get('missing',False) for r in results for q in r['queries']),'incomplete_queries':sum(q.get('depth')!=1 for r in results for q in r['queries']),'elapsed_seconds':time.perf_counter()-start}
for component in ('static','coverage','anchor','both'):
    diffs=[]
    for r in results:
        q={q['authority']:q for q in r['queries'] if q['component']==component and not q.get('missing')}
        if len(q)!=3:continue
        assert (q['core']['action'],q['core']['score'])==(q['native']['action'],q['native']['score'])
        diffs.append(q['legacy']['action']!=q['core']['action'])
    summary[component+'_D1_action_differences']=sum(diffs)
summary['child_score_delta_nonzero']={k:sum(ch['scores_stm'][k]['legacy']!=ch['scores_stm'][k]['core'] for r in results for ch in r['children']) for k in ('static','coverage','anchor','both')}
(OUT/'components.json').write_text(json.dumps({'plan':plan,'summary':summary,'states':results},indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
