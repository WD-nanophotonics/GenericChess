"""One preselected original-mu four-actor library learner cost episode.

The committed sampler is consumed without WDL/outcome selection. This is a
single cost/signal case, not PRIMARY's forward comparison or an EVAL panel.
"""
from pathlib import Path
from dataclasses import asdict
import argparse,json,random,time
from scripts import leaper_design as L
from scripts.leaper_two_type_packet import read_packet
from scripts.leaper_ab_learner_exposure import restore,write
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,TDLeafEpisode,play_episode,BudgetEnd

SOURCE='fcd2021cc751736ab0f7166ce24a74d95632863e'
INPUT_SOURCE='56560fb3e24102792f72a005c5c5bdb52526943f'
DIRECTORY=Path('docs/research/data/leaper_default_conversion_20261024')

def plan(output):
    output.mkdir(parents=True,exist_ok=False)
    docs=read_packet(DIRECTORY/'packet.json.gz',DIRECTORY/'manifest.json')
    world=json.loads(docs['next/inputs.json'])
    cfg=dict(source=SOURCE,input_source=INPUT_SOURCE,producer_sha256=L.sha(Path(__file__)),
        input_packet_sha256=L.sha(DIRECTORY/'packet.json.gz'),world=world,
        question='Does the unchanged material TDLeaf learner obtain actual returned targets, a free-B update and terminal utility at measured cost on the new four-actor rule?',
        selection='Original sampler order root0/learnerrole0/seed202610240312. Fixed before any Player or outcome. Other seven roots remain eligible for future questions; no oracle, gradient or outcome filtering.',
        root=0,role=0,seed=202610240312,initial=[1.,1.,0.,0.],
        search=dict(backend='mainline',depth=4,nodes=8192,qdepth=0,query_seconds=5.,fresh_player_per_query=True,equal_capture_ordering=True,tt=True),
        learner=dict(eta=.05,lam=.95,scale=10.,unit='A'),
        game_seconds=180,game_nodes=1000000,horizon=64,whole_seconds=200,
        expected_seconds=120,
        stop='Exactly one actual episode; no retries/refill, outcome-selected expansion, best checkpoint or automatic wider training. Preserve partial/UNKNOWN. >=120min aggregate experiment requires mailbox assessment.',
        opponent='One actual seeded uniform-legal stream; each foe action sampled from complete sorted current Core choices, full RNG retained. No default/static PRIMARY controller.')
    write(output/'plan.json',cfg);return cfg

def run(output):
    cfg=json.loads((output/'plan.json').read_bytes())
    assert cfg['producer_sha256']==L.sha(Path(__file__))
    assert cfg['input_packet_sha256']==L.sha(DIRECTORY/'packet.json.gz')
    with (output/'execution.json').open('x',encoding='utf8')as f:json.dump(dict(source=SOURCE,started=time.time()),f)
    began=time.perf_counter();world=cfg['world'];c=L.compile_rule(L.ruleset_from_dict(world['rule']))
    assert c.ruleset_fingerprint=='173bd8ad8bc61414547559bea1bd9196f9d03f8fb5f3e0f35673f14c5108df77'
    root=world['roots'][cfg['root']]
    env=FixedScaleSessionEnv(restore(c,root['record']),unit_type='A')
    assert L.state_sha(env.session.state)==root['state_sha256']
    model=Model(cfg['initial']);before=list(model.weights);events=[];rng=random.Random(cfg['seed'])
    def cancel():
        if role_stop_requested():raise BudgetEnd('USER_STOP')
        if time.perf_counter()-began>=cfg['whole_seconds']:raise BudgetEnd('WHOLE_CAP_UNKNOWN')
    def uniform(e):
        choices=sorted(e.actions(),key=lambda a:json.dumps(L.record_value(a),sort_keys=True))
        index=rng.randrange(len(choices));a=choices[index]
        events.append(dict(kind='Uniform',actor=e.player(),state_sha256=L.state_sha(e.session.state),index=index,legal_count=len(choices),choice=L.record_value(a)))
        return a
    def observed(ply,actor,r):
        events.append(dict(kind='candidate',ply=ply,actor=actor,state_sha256=L.state_sha(env.session.state),receipt=L.record_value(r)))
    result=play_episode(env,model,opponent=Model(cfg['initial']),opponent_policy=uniform,
        learner=TDLeafEpisode(**{k:cfg['learner'][k]for k in('eta','lam')}),learner_color=cfg['role'],
        depth=cfg['search']['depth'],query_nodes=cfg['search']['nodes'],max_nodes=cfg['game_nodes'],
        horizon=cfg['horizon'],seconds=cfg['game_seconds'],cancel=cancel,on_query=observed,search_backend='mainline')
    env.replay()
    row=dict(before=before,after=model.weights,events=events,initial_record=root['record'],final_record=env.record(),
        terminal=L.record_value(env.session.result),result=asdict(result),
        utility=None if result.outcome is None else result.outcome*(1 if cfg['role']==0 else-1),
        seconds=time.perf_counter()-began)
    write(output/'game-000.json',row)
    summary={k:row[k]for k in('before','after','result','utility','seconds')}
    write(output/'result.json',dict(status='CLOSED',**summary));print(json.dumps(summary),flush=True)
    return row

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('plan','run'));ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();globals()[a.mode](a.output)

