"""One prospective count-conditioned representation control, no new search."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from scripts.aux_material_episode_20261105 import code_sha,write
from generic_chess.learning.incremental import FixedScaleSessionEnv

def freeze(baseline,out):
    out.mkdir(exist_ok=False)
    cfg=json.loads((baseline/'plan.json').read_bytes())
    admission=[]
    for f,worlds in cfg['worlds'].items():
        for phase,w in worlds.items():
            env=FixedScaleSessionEnv(restore(L.compile_rule(L.ruleset_from_dict(w['RuleSet'])),w['record']),unit_type='A',feature_mode='count_pairs')
            assert len(env.names)==27 and env.names[0]==('board','A')
            admission.append(dict(family=int(f),phase=phase,names=env.names,root_phi=env.features(),legal_actions=len(env.actions())))
    slots=[]
    for f in (0,1,2):
        for role in (0,1):
            slots.append(dict(id=len(slots),phase='train',family=f,role=role,rep=0,arm='PairTD',seed=2026115010+f))
    for f in (0,1,2):
        for role in (0,1):
            slots.append(dict(id=len(slots),phase='eval',family=f,role=role,rep=0,arm='PairTD',seed=2026116010+f))
    cfg.update(producer_sha256=code_sha(),feature_mode='count_pairs',admission=admission,slots=slots,
        initial=[1.,1.,1.,0.,0.,0.]+[0.]*21,total_queries=832,total_nodes=1200000,total_seconds=600.,
        baseline_revision='805e793f392c990d9eb7b0557e10e2305f0dd31b',baseline_artifacts=str(baseline),
        baseline_games_sha256=hashlib.sha256((baseline/'games.jsonl').read_bytes()).hexdigest(),
        question='Can mechanically derived same-owner count-pair material interactions, initialized0, improve actual frozen-policy play relative to the existing linearTD and Unit baselines under identical TDLeaf/q0/Unitfoe service?',
        changed_premise='One opt-in representation change only: same-owner unordered actor-pair counts, including boardCURRENT and handBASE channels;antisymmetric owner0minusowner1. Selfpairs use n(n-1)/2, never oneactorwithitself. No humanprices/positionalbonuses/rule-specificlogic or pair-additivity assumption.',
        selection='Exact same three new capture-rich families/layouts and seeds as published linear baseline; exposed development/model-class comparison, no independentholdout or model-selectionstrength claim.',
        scope='6newTRAIN+6newPairTDEVALphysicalgames maxima; reuse all3Unitbaselinegames and6linearTDseatviews exactly, not newgames. Same scalar hyperparameters/fixedAlinearunit;27weights,21pairweightsinitial0. Unitfoe has allpairweights0. Familymodels separate. No extratrainingepisodes/tuning/replacements/refills/checkpointselection.',
        outcomes='Literal actualterminalWDL/UNKNOWN, physicalchoices, coefficients and service separate. Interactions make conditionalcontributions, not intrinsic globalprices. Different training trajectories after first update are part of the fullalgorithm treatment.',
        service='Same queryD2/2048nodes and game30s/65536nodes as reused baseline; whole600s/832queries/1.2Mnodes includesconstruction/returnpacking, queryslack above12x64=768. Featureoverhead paid. First-role0TRAINepisode in EACHfamily starts with zero pairweights; compare its completeworkload to linearfirstepisode before reporting descriptive timing, no stable speedclaim.',
        forecast='OwnABC-chain actual costs retained; newengineering/tests/analysis/delivery forecast25/cap35minutes from12:24UTC, combinedunder120minutes. No H6capreset or retiredPRIMARYpanelreopen. Stop if the changed-feature interface needs a new search/default/identity framework.')
    write(out/'plan.json',cfg);print(json.dumps(dict(slots=len(slots),features=27,baseline=str(baseline),newtraining=6,neweval=6),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('baseline',type=Path);p.add_argument('output',type=Path);a=p.parse_args();freeze(a.baseline,a.output)
