"""Raw selected-leaf predictor versus dequantized Native leaf score."""
from pathlib import Path
import json,math,sys
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
D=R/'.local_agent/static-input-objective-20261018';errors=[]
for q in map(json.loads,(D/'queries.jsonl').read_bytes().splitlines()):
 if q['status']=='USABLE_NATIVE_RETURN'and not q['leaf_actual_terminal']:errors.append(abs(math.tanh(q['score']/256/10)-q['leaf_prediction']))
result=dict(scope='The savedgradient is derivative of frozen RAWCOEFFICIENT tanh predictor at ACTUALNative-selectedleaf, conditionalonthatleaf. It is NOT derivative throughintegerrounding/searchargmax/ties. Decoder recomputescheckpointfloatweights, matching currentproduct tdleaf/selfplay source convention; no learner/gradientthroughNative implemented orclaimed.',raw_definition='Rawcoefficient here means checkpointfloat derivedfromexistingnormalized/rounded/clippedstaticprofile, notrawmovementcapability.',ordinary_point_count=len(errors),ordinary_prediction_quantized_decoder_max_abs_difference=max(errors),ordinary_prediction_quantized_decoder_mean_abs_difference=sum(errors)/len(errors),relation='Nativeintegerleafscore isindependentlycheckedagainstquantizedweights, not assumedidenticaltotherawtanhprediction. Terminal own-gradientconstant0 andpasteligibilitydistinction preserved.',source_read_only=['generic_chess/learning/selfplay.py:_normalized_value at returnedfeatures','generic_chess/learning/tdleaf.py:values andgrad_scale'],no_product_bug_or_change_claim=True)
write_json(D/'gradient-convention-erratum.json',result);print('CONVENTION',len(errors),max(errors),flush=True)
