"""Actual learner channels on the newest committed four-actor input.

No Player, update or truth selection. Complete original roots and saved D1/D2
frontiers are consumed; positive-cone material order is an algebraic limit,
not a gate on learning or proof of whole-game value/strength.
"""
from pathlib import Path
from collections import Counter
import json,time
from scripts import leaper_design as L
from scripts.leaper_two_type_packet import read_packet
from scripts.leaper_ab_learner_exposure import restore,write
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model


def run(output):
    tick=time.perf_counter();directory=Path('docs/research/data/leaper_default_conversion_20261024')
    docs=read_packet(directory/'packet.json.gz',directory/'manifest.json');world=json.loads(docs['next/inputs.json']);front=json.loads(docs['next/frontier.json']);c=L.compile_rule(L.ruleset_from_dict(world['rule']))
    assert c.ruleset_fingerprint=='173bd8ad8bc61414547559bea1bd9196f9d03f8fb5f3e0f35673f14c5108df77'
    model=Model((1,1,0,0));roots=[];features=Counter();terminals=Counter();edges=0
    def inspect(record):
        s=restore(c,record);env=FixedScaleSessionEnv(s,unit_type='A')
        if s.state.terminal_status.is_terminal:
            terminals[str(s.result)]+=1;return None
        assert env.names==(('board','A'),('board','B'),('hand','A'),('hand','B'))
        phi=env.features();assert phi[2:]==(0,0)
        assert tuple(phi)in((1,-1,0,0),(1,0,0,0),(0,-1,0,0),(0,0,0,0))
        features[str(phi)]+=1
        return dict(phi=phi,raw=model.raw(phi),prediction=model.prediction(phi),gradient=model.gradient(phi))
    for root in world['roots']:
        obs=inspect(root['record']);assert obs['phi']==(1,-1,0,0)and obs['raw']==0 and obs['gradient'][1]==-.1
        roots.append(dict(index=root['index'],state_sha256=root['state_sha256'],**obs))
    for row in front['rows']:
        for arm in row['arms']:
            inspect(arm['record']);edges+=1
            for reply in arm['replies']:inspect(reply['record']);edges+=1
    assert edges==front['edges']==576
    result=dict(verified=True,source='56560fb3e24102792f72a005c5c5bdb52526943f',packet_sha256=L.sha(directory/'packet.json.gz'),fingerprint=c.ruleset_fingerprint,roots=roots,frontier_edges=edges,feature_counts=dict(features),terminal_counts=dict(terminals),seconds=time.perf_counter()-tick,Player_queries=0,training_updates=0,
        algebra='In this one-A0/one-B1 removal scope, nonterminal board values are {1-B,1,-B,0}. Within the positive mate-dominated range, leaf weak orders are constant separately below1, at1, and above1. Finite exact min/max preserves order, but this does not equate timed search cost or deeper root actions across cells. Root raw0 at B1 has actual free B Jacobian-.1.',
        scope='All8published original safe roots and all576 saved D1/D2 edges; no sampler or PRIMARY forward campaign, truth filtering, new Player/training, dynamic feature/default adoption, deeper-support or terminal-utility claim. Separate new source input, not current old-input depth-panel denominator.')
    write(output,result);return result
