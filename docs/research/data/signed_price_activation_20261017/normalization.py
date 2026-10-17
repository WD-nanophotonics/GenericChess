"""Reproduce fixed-temperature normalization on exact published89leaf inputs."""
from pathlib import Path
import json,sys,hashlib,math
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from generic_chess.learning.material import LearnableMaterialCheckpoint

def run(queries_file,output):
    raw=Path(queries_file).read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='82389eed5674fd6996a1c2c5041fb9cfb3dbe68ce4e841b5d90e778152bf1f3d'
    directory=ROOT/'docs/research/data/aux89_native_candidates_20261017'
    index=json.loads((directory/'index.json').read_bytes());models={};rows=[]
    for e in index['models']:
        if e['label']!='trained':continue
        cp=LearnableMaterialCheckpoint.from_dict(json.loads((directory/e['path']).read_bytes()))
        independent=LearnableMaterialCheckpoint.from_dict(json.loads(json.dumps(cp.to_dict())))
        factor=independent.normalize_and_clip()
        models[e['generator_seed'],e['seed']]=(cp,independent,factor)
        rows.append(dict(rule=e['generator_seed'],seed=e['seed'],factor=factor,
            value_scale_before=cp.value_scale,value_scale_after=independent.value_scale,
            boardP_before=cp.board_weights['P'],boardP_after=independent.board_weights['P']))
    ordinary=changed=0;maximum=joint=0.;by={}
    for line in raw.splitlines():
        q=json.loads(line)
        if not q['complete']or q['pv_terminal']:continue
        cp,norm,f=models[q['generator_seed'],q['seed']];ordinary+=1
        def value(model):return sum(x*(model.board_weights if k=='board'else model.hand_weights)[t]
            for x,(k,t)in zip(q['pv_phi'],q['channels']))
        a=math.tanh(value(cp)/cp.value_scale);b=math.tanh(value(norm)/norm.value_scale)
        co=math.tanh(value(norm)/(f*cp.value_scale));difference=abs(a-b)
        changed+=difference>1e-12;maximum=max(maximum,difference);joint=max(joint,abs(a-co))
    assert len(models)==8 and ordinary==613 and changed==294 and joint<1e-14
    result=dict(status='PASS_REPRODUCED_NORMALIZATION_DIAGNOSTIC',models=rows,
        ordinary_complete_points=ordinary,changed_predictions=changed,
        max_prediction_difference=maximum,co_rescaled_temperature_max_error=joint,
        scope='Fixedeightendpointtables/existing89ordinaryleaves; notnewtraining/fitness. GenuineindependentJSONcopy, fixedvalue_scale10 unchanged bynormalizer. Co-rescalingtemperature preservespredictionhere, notfixedeta learningdynamics. No clippinginthisscope. Servingdoesnotautomaticallycallnormalization.')
    with Path(output).open('x',encoding='utf8')as out:json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps({k:v for k,v in result.items()if k!='models'}))
    return result

if __name__=='__main__':run(sys.argv[1],sys.argv[2])
