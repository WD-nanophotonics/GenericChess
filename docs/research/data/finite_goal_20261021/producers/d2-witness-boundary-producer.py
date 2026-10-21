"""Complete two-coordinate slice for the natural saved D2 counterexample."""
from pathlib import Path
from dataclasses import replace
import json
import numpy as np
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import legal_successors
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.material_choice_sensitivity import vector
from scripts.price_regions import CONFIG
from scripts.research_record import record_value,write_record
r=json.loads(Path('artifacts/price-regions-20261021/d2-witness-localized.json').read_text());c=compile_ruleset_for_execution(ruleset_from_dict(r['rule']));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['record'])));features=tuple(map(tuple,r['features']));owner=s.state.position.side_to_move
output=Path('artifacts/price-regions-20261021/d2-witness-boundary.json')
if output.exists():raise FileExistsError(output)
rows=[]
for action,child in sorted(legal_successors(s.state,c),key=lambda x:str(x[0])):
    replies=[dict(action=str(a),vector=vector(leaf,owner,features).tolist(),terminal=record_value(leaf.terminal_status)) for a,leaf in sorted(legal_successors(child,c),key=lambda x:str(x[0]))]
    assert all(x['terminal']['status']=='ongoing' for x in replies)
    rows.append(dict(action=str(action),replies=replies,distinct_vectors=sorted(set(tuple(x['vector']) for x in replies))))
# All leaf vectors are directly enumerated; only P-board/hand vary. Verify the
# reduction itself, not just chosen sample outputs, using each distinct affine form.
quiet,capture=rows
assert quiet['action']=='legacy_026:g20:d2-c4' and capture['action']=='legacy_053:g7:b1-c2'
baseline=np.array([1000]*5+[900]*5);ip=features.index(('board','P'));ih=features.index(('hand','P'))
forms=[]
for row in rows:
    f=set()
    for v in row['distinct_vectors']:
        v=np.array(v);f.add((int(v[ip]),int(v[ih]),int(v@baseline-v[ip]*baseline[ip]-v[ih]*baseline[ih])))
    forms.append(sorted(f))
assert forms[0]==[(0,0,-7800),(0,0,-6000),(0,0,-5900)]
assert forms[1]==[(-1,-1,-4000),(0,0,-5900),(0,0,-4100),(0,0,-4000)]
# Thus Vquiet=-7800 and Vcapture=min(-5900,-4000-p-h) everywhere in the
# prespecified nonnegative, unclipped rectangle, including all boundary ties.
checks=[];profile,_=build_semantic_opportunity_profile(c,CONFIG)
for handp in (2799,2800,2801):
    p=replace(profile,board_value_by_type={t:0 if m.is_anchor else 1000 for t,m in c.support.type_metadata.items()},
        hand_value_by_base_type={t:0 if m.is_anchor else handp if t=='P' else 900 for t,m in c.support.type_metadata.items()},
        promotion_gain_by_type={t:0 for t in c.support.type_metadata})
    for native in (False,True):
        pl=AlphaBetaPlayer(c,evaluator_override=Evaluator(c,p,CONFIG),use_disk_cache=False,use_tt=False,use_ordering=False,
            use_native_semantic_legality=native,tuning=SearchTuning(use_root_tactical=False))
        before=s.state;d=pl.choose_action(s,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=5,quiescence_max_depth=0,quiescence_hard_max_depth=0));assert before==s.state and d.completed_depth==2
        expected=max(-7800,min(-5900,-5000-handp));assert d.score==expected
        checks.append(dict(handP=handp,native_requested=native,decision=record_value(d),action=str(d.action)))
write_record(output,dict(scope='Single saved root, exact complete-D2 material slice, other board1000/hand900; no WDL or coefficient fit.',
    features=features,record=r['record'],reply_vectors=rows,affine_forms=forms,
    equation=dict(quiet='-7800',capture='min(-5900,-4000-boardP-handP)',boundary='boardP+handP=3800'),public=checks))
print('complete forms',forms);print([(x['handP'],x['native_requested'],x['action'],x['decision']['score']) for x in checks])
