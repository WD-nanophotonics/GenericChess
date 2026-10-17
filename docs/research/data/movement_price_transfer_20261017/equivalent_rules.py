from pathlib import Path
import json,sys,time
sys.path.insert(0,str(Path.cwd()))
from tools.local_agent.common import write_json
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
D=Path('.local_agent/movement-transfer-20261017');p=json.loads((D/'plan.json').read_bytes());mapping={'K':'T7','P':'T3','X':'T19','A':'T2'};out=[];start=time.perf_counter()
def rename(x):
 if isinstance(x,dict):return {mapping.get(k,k):rename(v)for k,v in x.items()}
 if isinstance(x,list):return [rename(v)for v in x]
 return mapping.get(x,x)if isinstance(x,str)else x
for rid in p['rules']:
 original=json.loads((D/f'rule-{rid}.json').read_bytes());other=rename(original);other['piece_types'].reverse()
 cc=[compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(r))for r in [original,other]];pp=[build_ruleset_profile(c,EvaluationConfig())for c in cc]
 for t,new in mapping.items():
  a,b=pp[0].piece_profiles[t],pp[1].piece_profiles[new]
  for k in ['movement_signature','raw_capability_score','normalized_board_value','normalized_hand_value','promotion_option_value','drop_freedom_ratio','drop_mobility','is_anchor','is_promotable']:assert getattr(a,k)==getattr(b,k),(rid,t,k)
 assert cc[0].ruleset_fingerprint!=cc[1].ruleset_fingerprint
 out.append(dict(rule=rid,all4pieceprofile_fields_equal_after_inverse_rename=True,declared_type_order_reversed=True,fingerprint_changed=True))
write_json(D/'equivalent-rule-price-control.json',dict(status='PASS_ALL16_RENAME_AND_REORDER_ONLY_STATIC_PRICE_CONTROLS',mapping=mapping,rows=out,seconds=time.perf_counter()-start,scope='Finite explicit typeID renaming+declaration reorder, all profile fields inverse-map exactly. No gameplay/wholetypedactionequivalence proof or new policy; NOT claiming A movementreplacement is equivalent. Model numeric table rebinding remains an experiment-specific recipe, not name-based value semantics. No humanlabelsfit.'))
print('PASS all16 equivalent naming/order static profile controls')
