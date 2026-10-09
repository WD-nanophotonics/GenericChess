"""Final coefficient repair leaves raw geometry/board scale intact on frozen rules.
Compare actual53e41df builder source against final product, two density laws,
Chess/Shogi/internal-Xiangqi/cannon. This is scope/representation qualification,
not evidence for the remaining legacy hand scale or material usefulness.
"""
from pathlib import Path
from dataclasses import replace
import sys,subprocess,hashlib
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from rule_semantics_ir_fixtures import cannon_ruleset
from scripts.research_record import write_record
folder=Path(__file__).parent;out=folder/'profile-boundary-transfer.json';assert not out.exists()
source=subprocess.check_output(['git','show','53e41df5af3b5d805b6fb7e7b8b2a6c8e59ca0a1:generic_chess/ai/evaluation/semantic.py'])
ns={'__name__':'generic_chess.ai.evaluation._frozen_boundary','__package__':'generic_chess.ai.evaluation'}
exec(compile(source,'frozen_semantic_builder','exec'),ns)
result=dict(scope=__doc__,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),baseline_source_sha256=hashlib.sha256(source).hexdigest(),rows=[])
configs=[EvaluationConfig(),EvaluationConfig(density_points=(.1,.3,.7),density_weights=(.2,.3,.5))]
for name,builder in [('Chess',build_western_chess_ruleset),('Shogi',build_standard_shogi_ruleset),('internal_Xiangqi',build_xiangqi_diagnostic_ruleset),('cannon',cannon_ruleset)]:
    c=compile_ruleset_for_execution(builder())
    for index,config in enumerate(configs):
        old,os=ns['build_semantic_opportunity_profile'](c,config)
        new,ss=build_semantic_opportunity_profile(c,config)
        assert old.board_value_by_type==new.board_value_by_type and old.promotion_gain_by_type==new.promotion_gain_by_type
        assert os['types']==ss['types']
        if ss['hand_policy']=='zero_proved_inert':assert all(v==0 for v in new.hand_value_by_base_type.values())
        else:assert old.hand_value_by_base_type==new.hand_value_by_base_type
        result['rows'].append(dict(rule=name,law=index,board_equal=True,raw_scope_equal=True,
            policy=ss['hand_policy'],old_hands=old.hand_value_by_base_type,new_hands=new.hand_value_by_base_type))
result['complete']=True;write_record(out,result);print([(r['rule'],r['law'],r['policy']) for r in result['rows']])
