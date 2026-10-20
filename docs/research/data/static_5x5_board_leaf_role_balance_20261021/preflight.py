from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
root=Path(__file__).resolve().parents[4]
here=Path(__file__).resolve().parent
sys.path.insert(0,str(root)); sys.path.insert(0,str(here))
from producer import PLAN, checkpoint, make_opening, sha, _opening_state
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.session.session import GameSession
used={}; plan_files=[]
for path in sorted((root/'docs/research/data').rglob('plan.json')):
    if path.parent==here: continue
    try:
        obj=json.loads(path.read_text(encoding='utf-8'))
        seeds=obj.get('rules',{}).get('seeds',[])
        if seeds:
            plan_files.append(path.relative_to(root).as_posix())
            for seed in seeds: used.setdefault(str(seed),[]).append(path.relative_to(root).as_posix())
    except Exception: pass
seeds=[str(s) for s in PLAN['rules']['seeds']]
overlap={s:used[s] for s in seeds if s in used}
if overlap: raise AssertionError(f'SEED_OVERLAP:{overlap}')
(here/'seed-preflight.json').write_text(json.dumps({'schema':'primary-static-seed-preflight-v1','result':'PASS','existing_plan_count':len(plan_files),'existing_seed_occurrences':sum(map(len,used.values())),'existing_plan_seeds':sorted(used,key=int),'candidate_seeds':seeds,'overlap':overlap},indent=2,sort_keys=True)+'\n',encoding='utf-8')
features=[]; roots=[]
for i,seed_s in enumerate(seeds):
    seed=int(seed_s)
    cfg=GeneratorConfig(seed=seed,board_size=5,setup_preset=PLAN['rules']['setups_by_seed_order'][i%3],movement_symmetry=PLAN['rules']['movement_symmetry_by_seed_order'][i%2],allow_hybrid=True,require_promotable_type=True,require_nonpromotable_type=True,max_generation_attempts=16,require_no_opening_win_in_one=False)
    generated=generate_game(cfg); compiled=compile_legacy_ruleset_for_semantic_execution(generated.ruleset); profile=build_ruleset_profile(compiled,EvaluationConfig())
    u=checkpoint(compiled,profile,'unit'); st=checkpoint(compiled,profile,'static_v2')
    assert st.hand_weights==u.hand_weights
    assert not st.dynamic_weights and not st.spatial_occupancy_weights and not st.localized_control_weights and not st.compact_nonlinear
    assert st.board_weights=={t:v/1000.0 for t,v in profile.board_value_by_type.items()}
    features.append({'seed':seed,'fingerprint':compiled.ruleset_fingerprint,'unit_checkpoint_id':u.checkpoint_id,'static_board_checkpoint_id':st.checkpoint_id,'unit_hand_equal':True,'optional_terms_empty':True})
    for family,plies in enumerate(PLAN['roots']['prefix_plies_by_family']):
        prefix_seed=seed*1_000_000+family
        opening=make_opening(compiled,prefix_seed,plies)
        session=GameSession(compiled)
        for action in opening: session.submit(action)
        expected_side=1 if plies==3 else 0 if plies==4 else None
        actual_side=session.state.position.side_to_move
        assert len(opening)==plies or session.result.status.value!='ongoing'
        if len(opening)==plies: assert actual_side==expected_side
        roots.append({'root_id':f'{seed}-{family}','seed':seed,'family':family,'prefix_seed':prefix_seed,'planned_plies':plies,'actual_plies':len(opening),'side_to_move':actual_side,'root_sha256':sha(_opening_state(compiled,opening)),'opening':[str(a) for a in opening]})
assert len(features)==8 and len({f['fingerprint'] for f in features})==8
assert len(roots)==16 and {r['planned_plies'] for r in roots}=={3,4}
assert all(r['side_to_move']==(1 if r['planned_plies']==3 else 0) for r in roots if r['actual_plies']==r['planned_plies'])
plan_sha=hashlib.sha256((here/'plan.json').read_bytes()).hexdigest()
(here/'feature-preflight.json').write_text(json.dumps({'schema':'primary-static-board-role-feature-preflight-v1','plan_sha256':plan_sha,'result':'PASS','rule_count':len(features),'distinct_fingerprints':len({f['fingerprint'] for f in features}),'all_static_board_arms_hold_unit_hand':all(f['unit_hand_equal'] for f in features),'all_optional_dynamic_spatial_compact_terms_empty':all(f['optional_terms_empty'] for f in features),'rules':features},indent=2,sort_keys=True)+'\n',encoding='utf-8')
(here/'root-preflight.json').write_text(json.dumps({'schema':'primary-static-board-role-root-preflight-v1','plan_sha256':plan_sha,'result':'PASS','root_count':len(roots),'plies_by_family':PLAN['roots']['prefix_plies_by_family'],'side_to_move_counts':{str(side):sum(r['side_to_move']==side for r in roots) for side in (0,1)},'roots':roots},indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'seed_overlap':overlap,'existing_plan_count':len(plan_files),'fresh_rules':len(features),'distinct_fingerprints':len({f['fingerprint'] for f in features}),'fresh_roots':len(roots),'plies_by_family':PLAN['roots']['prefix_plies_by_family'],'side_to_move_counts':{str(s):sum(r['side_to_move']==s for r in roots) for s in (0,1)},'unit_hand_equal':True,'optional_terms_empty':True},indent=2))
