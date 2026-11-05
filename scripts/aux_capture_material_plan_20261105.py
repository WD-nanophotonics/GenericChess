"""Freeze a changed-input pilot for the existing AUX episode runner.

Consumes ordinary newly committed capture-rich RuleSets only; never imports
retired capture-order sources or reopens PRIMARY's32 NOT_RUN fitness slots.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, subprocess
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from scripts.aux_material_episode_20261105 import code_sha,write
from generic_chess.learning.incremental import FixedScaleSessionEnv
SOURCE='de018b631cb8ac774565b702aab58a4f0effeea5'
INPUT='docs/research/data/leaper_capture_admission_20261105/inputs.json.gz'
def freeze(out):
    out.mkdir(exist_ok=False)
    raw=subprocess.check_output(['git','show',SOURCE+':'+INPUT]);data=json.loads(gzip.decompress(raw))
    worlds={};admission=[]
    for f in (0,1,2):
        worlds[str(f)]={}
        for layout,phase in ((0,'train'),(1,'eval')):
            row=next(r for r in data['rows'] if r['family']==f and r['layout']==layout)
            worlds[str(f)][phase]=row
            env=FixedScaleSessionEnv(restore(L.compile_rule(L.ruleset_from_dict(row['RuleSet'])),row['record']),unit_type='A')
            assert env.names==(('board','A'),('board','B'),('board','C'),('hand','A'),('hand','B'),('hand','C'))
            assert env.terminal() is None
            admission.append(dict(family=f,phase=phase,legal_actions=len(env.actions()),root_phi=env.features(),names=env.names))
    slots=[]
    for f in (0,1,2):
        for role in (0,1):
            slots.append(dict(id=len(slots),phase='train',family=f,role=role,rep=0,arm='TD',seed=2026115010+f))
    for f in (0,1,2):
        for arm,role in (('Unit',0),('TD',0),('TD',1)):
            slots.append(dict(id=len(slots),phase='eval',family=f,role=role,rep=0,arm=arm,seed=2026116010+f))
    cfg=dict(source=SOURCE,input_path=INPUT,input_sha256=hashlib.sha256(raw).hexdigest(),producer_sha256=code_sha(),
        worlds=worlds,admission=admission,slots=slots,initial=[1.,1.,1.,0.,0.,0.],eta=.05,lam=.95,scale=10.,
        depth=2,query_nodes=2048,game_nodes=65536,game_seconds=30.,total_seconds=600.,total_queries=1024,total_nodes=1200000,horizon=64,
        opponent_policy='Unit',opponent='Frozen Unit model with the SAME public q0D2 and query service, both TRAIN and EVAL; no stochastic policy or human material prior.',
        question='Do new committed capture-rich geometries and Unit-q0 opponent supply actual free-feature/terminal TD evidence and change frozen-model play on the other literal quantity layout?',
        changed_premise='New de018b capture-rich complete-input source, not the older quiet q-bound families or closed natural-prefixMobility/D4/Static study. No input outcome is used to select families or training starts.',
        selection='Exactly source-order families0/1/2,layout0TRAIN/layout1EVAL. Both layouts were published as ADMITTED. Families4/6/7 contain known invalid rows and are not replacements; PRIMARYqualification remains CLOSED/all32NOT_RUN. No source producer, capture-order feature or archivedtestedcode is executed.',
        scope='6TRAIN+9EVALphysicalgames maxima, separate family models, no pooling. One Unit/Unit EVAL baseline per family reused for two seatviews, not independent duplicated games. Skip allEVALforanexactlyunchangedfamilymodel without claiming its WDL. No extra TRAINreplicas, replacements/refills/reversecontrols or tuning.',
        outcomes='Actual W/L/D only, UNKNOWN neverDRAW. Changed actions/weights not quality; exposed DEVELOPMENT input/opponent/quantity transfer only, not independent rules or intrinsic prices.',
        service='Whole600s includes shared compilation and serialization. Per-game30s and nodes pay both candidate and opponent; whole1024query slack above15x64maximum960. Cooperative limits, no extra worker or hard preemption.',
        frozen_source_history='Earlier original runner version is preserved in prior published acad59ac; new optional Unit policy uses the same unchanged public learner/play code. Old36slots and subsequent2+9controls remain CLOSED with their source/limits.')
    write(out/'plan.json',cfg);print(json.dumps(dict(output=str(out),slots=len(slots),admission=admission),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);freeze(p.parse_args().output)
