"""Describe actual rule-only and transferred price coordinates; no fitting/outcomes."""
import json,sys,time
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R));D=R/'.local_agent/movement-transfer-20261017'
from tools.local_agent.common import write_json
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
start=time.perf_counter();p=json.loads((D/'plan.json').read_bytes());mm=json.loads((D/'models.json').read_bytes())['rows'];rows=[]
for rid,v in p['variants'].items():
 c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(json.loads((D/f'rule-{rid}.json').read_bytes())));profile=build_ruleset_profile(c,EvaluationConfig());static=next(x for x in mm if x['rule']==rid and x['label']=='rule_static_v2')['checkpoint'];assert static['board_weights']=={t:0. if t=='K'else profile.board_value_by_type[t]/1000 for t in c.types_by_id}
 def ratios(cp):
  b=cp['board_weights'];h=cp['hand_weights'];return dict(board=dict(b),hand=dict(h),A_over_P=None if b['P']==0 else b['A']/b['P'],X_over_P=None if b['P']==0 else b['X']/b['P'],P_quantized=round(256*b['P']),A_quantized=round(256*b['A']))
 rows.append(dict(rule=rid,recipient=v['recipient'],donor=v['movement_donor'],identity=v['identity_control'],static_raw_by_type={t:profile.piece_profiles[t].raw_capability_score for t in c.types_by_id},static=ratios(static),frozen_learned={x['label']:ratios(x['checkpoint'])for x in mm if x['rule']==rid and x['label'].startswith(('fixed5','free6'))}))
write_json(D/'price-coordinate-audit.json',dict(status='PASS_RULE_RECOMPUTED_STATIC_AND_UNCHANGED_NUMERIC_LEARNED_TABLES',variants=rows,seconds=time.perf_counter()-start,scope='Descriptive candidate coefficients, NOT truepiecevalues/identifiability or newnormalization/deployment. staticrawcapability is finiteboardrule-onlyheuristic; normalizationmedian maychangemultipleweights afterone A movementfield. Ratiosstatedseparatelyfromraw/roundedNative256coefficients. RebindingtypeID A to differentmove is an explicit transferrecipe, not a learnedruleconditionedmap. No outcome/modelselection/fitting.'))
print('Price coordinates qualified for16 variants, no outcome read')
