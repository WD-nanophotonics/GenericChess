"""Read-only support/Jacobian census through the existing actual learner.

No model update, training episode or Player call occurs. The one board A unit
is fixed; its sole other channel is unreachable hand A. All legal positions
in the supplied full Core closure therefore have zero free material gradient.
"""
from collections import Counter
from scripts import leaper_design as L
from scripts.leaper_cooperative_certificate import decode_position
from generic_chess.learning.incremental import compile_channels,_material_features,Model,FixedScaleSessionEnv
import json,hashlib


def analyze(graph,c,docs,truth):
    names=compile_channels(c,unit_type='A')
    if names!=(('board','A'),('hand','A')):raise ValueError('one-type fixed-unit channel contract differs')
    models=[Model((1,w),fixed=0,scale=scale)for w in(-3,0,2)for scale in(1,10)]
    positions=Counter();history=Counter();derivatives=Counter()
    for raw in graph['positions']:
        position=decode_position(raw,c.initial_position);phi=_material_features(position,c,names)
        positions[str(tuple(phi))]+=1
        if len(phi)!=2 or phi[1]!=0:raise ValueError('hand or extra material signal became active')
        for model in models:
            gradient=model.gradient(phi);derivatives[str(tuple(gradient))]+=1
            if any(gradient):raise ValueError('claimed inactive feature has a real learner gradient')
    for row in truth['rows']:
        game=json.loads(docs['forward/'+row['source_receipt']]);s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(game['initial_record'])))
        for q in game['queries']:
            if L.state_sha(s.state)!=q['state_sha256']:raise ValueError('gradient actual history differs')
            env=FixedScaleSessionEnv(s,unit_type='A');phi=env.features();history[str(tuple(phi))]+=1
            if phi!=_material_features(s.state.position,c,names)or any(models[0].gradient(phi)):
                raise ValueError('actual learner consumer differs from support/Jacobian premise')
            s.submit(L.match_action(s,q['action']))
    return dict(verified=True,names=names,Core_qualified_position_features=dict(positions),actual_full_history_features=dict(history),model_gradient_checks=dict(derivatives),models_checked=len(models),Player_queries=0,training_episodes=0,model_updates=0,claim='Foranyfinitehandcoefficientandpositivescale, thefixedboardgradientis0byModelcontractandthehandgradientis0becauseitsfeatureisunreachable. EveryTDLeafeligibility/updateformedfromthesefrozenmaterialgradientsiszero, regardlessofnonzeroTDerror. Stochasticchanceheadroomdoesnotactivatearelativepriceaxis. Thisisnotauniversalclaimaboutotherlearners,geometryfeaturesorA/Binputs.')


def split_type_zero_crossing(directory):
    """Zero VALUE is not zero free gradient on existing unfiltered A/B roots."""
    from pathlib import Path
    from scripts.leaper_explorer_truth import load
    from scripts.leaper_h6_initial_truth import admit
    directory=Path(directory);inputs=load(directory/'inputs.json.gz');counts=Counter();rows=[]
    for family in inputs['families']:
        if family['status']=='MU_UNAVAILABLE':continue
        group=[r for r in inputs['rows']if r['family']==family['family']];c=admit(family,group[0]);local=Counter()
        for source in group:
            s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(source['full_record'])))
            if L.state_sha(s.state)!=source['state_sha256']:raise ValueError('old A/B actual root differs')
            env=FixedScaleSessionEnv(s,unit_type='A');phi=env.features()
            model=Model((1,1,0,0),fixed=0,scale=10)
            if env.names!=(('board','A'),('board','B'),('hand','A'),('hand','B'))or tuple(phi)!=(1,-1,0,0):raise ValueError('old opposed A/B feature scope differs')
            value=model.prediction(phi);gradient=model.gradient(phi)
            if value!=0 or gradient!=(0.0,-0.1,0.0,0.0):raise ValueError('zero-valued but active gradient control differs')
            local['actual_roots']+=1;local['zero_value_nonzero_free_gradient']+=1
        counts.update(local);rows.append(dict(family=family['family'],fingerprint=c.ruleset_fingerprint,counts=dict(local)))
    algebra=dict(same_owner_AB='Withphi=(1,1)andfixedA=1,theconditionV=0forcesB=-1 inthisno-biaslinear/tanhmodel; thisisoffsetcompensationforacomposition,notintrinsicnegativepiecevalue.',opposed_AB='Withphi=(1,-1), B=1givesV=0butdV/dB=-1/scale,nonzero. A zero-valued leaf crossing is not an inactive parameter or a reason to require a fifth actor.')
    return dict(verified=True,counts=dict(counts),families=rows,algebra=algebra,Player_queries=0,training_episodes=0,model_updates=0,scope='OnlysavedcompleteA/Binitialrecords,allavailablefamilies/unfilteredroots;notnewmu/training,legalitysampling,benefitreplicationorapriceadoption. Thealgebradoesnotestablishlegalfrontierrealizationorpolicygain;neitherpositivegain noranonzerocrossingisrequiredtoallowaboundedlearningtest.')
