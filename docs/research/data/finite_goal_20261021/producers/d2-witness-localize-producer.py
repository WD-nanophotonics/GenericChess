"""Localize the saved731505/policy2/ply18 D1-invariant D2 witness."""
from pathlib import Path
from fractions import Fraction
from dataclasses import replace
import json,time
import numpy as np
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.material_choice_sensitivity import vector
from scripts.price_regions import CONFIG,Budget,build_tree,partition,response
from scripts.research_record import record_value,write_record

output=Path('artifacts/price-regions-20261021/d2-witness-localized.json')
if output.exists():raise FileExistsError(output)
source=json.loads(Path('docs/research/data/finite_roster_20261021/calibration-result.json').read_text())
sens=json.loads(Path('artifacts/price-regions-20261021/sensitivity.json').read_text())
row=next(x for x in sens['rows'] if x.get('seed')==731505 and x.get('policy')==2 and x.get('ply')==18)
witness=next(x for x in json.loads(Path('artifacts/price-regions-20261021/d2-invariant-witnesses.json').read_text())['rows'] if x['seed']==731505 and x['policy']==2 and x['ply']==18)
definition=next(x['definition'] for x in source['rules'] if x['seed']==731505)
c=compile_ruleset_for_execution(ruleset_from_dict(definition));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
features=tuple(map(tuple,row['features']));baseline=np.array([1000]*5+[900]*5);profile,_=build_semantic_opportunity_profile(c,CONFIG)
budget=Budget(90,150000);start=time.perf_counter();forms=set()
tree=build_tree(s.state,c,2,s.state.position.side_to_move,budget,forms,leaf_features=lambda state,owner:tuple(map(int,vector(state,owner,features))))
result=dict(scope=__doc__,rule=definition,record=row['record'],features=features,
    d1_actions=row['actions'],d1_child_vectors=row['child_vectors'],d1_fullbox_certificate=row['certificates']['full'],
    declaration=dict(axes='All10coefficients vary singly over original box; others fixedUnit1000/900',
        verification_vectors=['baseline','corner_witness','one_step_interior_witness','handP4000_others_baseline'],
        q=0,tt=False,ordering=False,depth=2,public_seconds=5,public_nodes=100000),axes=[],public=[])
for axis in range(len(features)):
    forms=set()
    def project(node):
        if node[0]=='leaf':
            v=node[1]
            if len(v)==2:form=v
            else:
                a=int(v[axis]);b=int(np.array(v)@baseline-a*baseline[axis]);form=(a,b)
            forms.add(form);return 'leaf',form
        return node[0],tuple((a,project(child)) for a,child in node[1])
    projected=project(tree);low=125 if axis<5 else 0
    regions=partition(projected,forms,Fraction(low),Fraction(4000))
    result['axes'].append(dict(feature=features[axis],regions=regions))
corner=np.array(witness['witness']['weights']);lo=np.array([125]*5+[0]*5);hi=np.array([4000]*10);interior=np.minimum(hi-1,np.maximum(lo+1,corner));single=baseline.copy();single[features.index(('hand','P'))]=4000
for label,weights in (('baseline',baseline),('corner',corner),('interior',interior),('handP_only',single)):
    board={t:0 for t in c.support.type_metadata};hand=board.copy()
    for (kind,t),w in zip(features,weights):(board if kind=='board' else hand)[t]=int(w)
    p=replace(profile,board_value_by_type=board,hand_value_by_base_type=hand,promotion_gain_by_type={t:0 for t in board})
    for native in (False,True):
        before=s.state;pl=AlphaBetaPlayer(c,evaluator_override=Evaluator(c,p,CONFIG),use_disk_cache=False,use_tt=False,use_ordering=False,
            use_native_semantic_legality=native,tuning=SearchTuning(use_root_tactical=False))
        d=pl.choose_action(s,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=5,quiescence_max_depth=0,quiescence_hard_max_depth=0))
        assert d.completed_depth==2 and s.state==before
        pv=GameSession.replay(c,s.to_record())
        for a in d.principal_variation:pv.submit(a)
        result['public'].append(dict(label=label,requested_native_legality=native,weights=weights.tolist(),decision=record_value(d),
            action=str(d.action),pv_record=record_value(pv.to_record())))
    a,b=result['public'][-2:];assert (a['action'],a['decision']['score'])==(b['action'],b['decision']['score'])
result.update(tree_nodes=budget.edges,wall_seconds=time.perf_counter()-start);write_record(output,result)
print('axes with changed optimal sets',[(x['feature'],len({tuple(r['actions']) for r in x['regions']})) for x in result['axes']])
print([(x['label'],x['requested_native_legality'],x['action'],x['decision']['score'],x['decision']['native_legality_calls'],x['decision']['native_legality_fallbacks']) for x in result['public']])
