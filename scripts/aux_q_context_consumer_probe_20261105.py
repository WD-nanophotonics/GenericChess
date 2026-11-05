"""Prospective bounded actual q0 learner consumption on new committed Q-game histories.
No fitting, rollout, Q-policy rerun or teacher-score import.
"""
from __future__ import annotations
import argparse,gzip,json,time
from pathlib import Path
from dataclasses import asdict
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,TDLeafEpisode,BudgetEnd
from generic_chess.learning.mainline_search import search
PIN='549b159a0129e2f96062935ce3786ddf3efb08a1'
def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def write(p,x):p.write_text(json.dumps(L.record_value(x),allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
def prepare(base,out):
    out.mkdir(exist_ok=False)
    inputs=read(base/'inputs.json.gz')['rows'];roots=[]
    for family in range(6):
        # Source order/clock positions fixed without examining score or outcome.
        game=read(base/('game-%02d.json.gz'%(2*family)))
        for ply in (0,16,32):
            r=read(base/(game['returns'][ply]+'.gz'))
            roots.append(dict(id=len(roots),family=family,game=2*family,ply=ply,
                source_return=game['returns'][ply],record=r['record_before'],
                source_action=r['decision']['action'],source_score=r['decision']['score'],source_actor=r['actor']))
    plan=dict(source=PIN,input_source='committedQpolicyDATA',roots=roots,worlds=inputs,
        question='Does actual existing Unit27/q0D2 TDLeaf consumer obtain valid feature targets on18 fixed new-family/full-history contexts, without using external Q4scores?',
        endpoint='actualreceipt completion/depth/PV/value/gradient,observe acceptedrows,sourceactiondifference/cost descriptiveonly',
        selection='sixsourcefamiliesfirstrolegameatabsoluteplies0/16/32;notfeature/score/outcomeselected;nooracletrainingstarts',
        cap=dict(queries=18,query_nodes=2048,query_seconds=1.5,whole_seconds=45),
        stops='no fitting/TDfinish/apply/rollout/retry/replacement/newQ4/default/worker;incompleteorbudgetexceptionsstayUNKNOWN;all18slotsretained',
        model=dict(weights=[1,1,1]+[0]*24,fixed=0,scale=10,feature_mode='count_pairs'),depth=2)
    write(out/'plan.json',plan);print('frozen18contexts;0search')
def run(out):
    p=read(out/'plan.json');marker=out/'execution.json'
    with marker.open('x',encoding='utf-8') as f:json.dump(dict(started_utc=time.time()),f)
    start=time.perf_counter();cpu=time.process_time();rows=[];queries=nodes=0;compiled={}
    for world in p['worlds']:compiled[world['family']]=L.compile_rule(L.ruleset_from_dict(world['RuleSet']))
    for root in p['roots']:
        if time.perf_counter()-start>=p['cap']['whole_seconds']:
            rows.append(dict(root_id=root['id'],status='NOT_RUN_WHOLE_CAP_UNKNOWN'));continue
        env=FixedScaleSessionEnv(restore(compiled[root['family']],root['record']),unit_type='A',feature_mode='count_pairs')
        model=Model(**{k:v for k,v in p['model'].items() if k!='feature_mode'})
        frozen=list(model.weights);before=L.record_value(env.session.to_record());began=time.perf_counter()
        def guard():
            from scripts.leaper_microgames import role_stop_requested
            if role_stop_requested():raise BudgetEnd('USER_STOP')
            if time.perf_counter()-start>=p['cap']['whole_seconds']:raise BudgetEnd('WHOLE_CAP_UNKNOWN')
        r=search(env,model,depth=p['depth'],nodes=p['cap']['query_nodes'],
            seconds=min(p['cap']['query_seconds'],p['cap']['whole_seconds']-(time.perf_counter()-start)),cancel=guard)
        queries+=1;nodes+=r.nodes
        learner=TDLeafEpisode();learner.observe(model,r)
        # Observe only, never finish/apply or borrow a literal final draw.
        assert frozen==model.weights and before==L.record_value(env.session.to_record())
        phi=r.pv_phi;grad=None if not r.complete or r.pv_terminal else model.gradient(phi)
        source_action_equal=r.action is not None and r.action.kind=='ACTION' and L.record_value(r.action.action)==root['source_action']
        row=dict(root_id=root['id'],family=root['family'],game=root['game'],ply=root['ply'],
            status='COMPLETE' if r.complete else 'UNKNOWN',receipt=asdict(r),observed_rows=len(learner.rows),
            gradient=grad,CC_gradient=None if grad is None else grad[17],root_phi=env.features(),source_action_equal=source_action_equal,
            source_score_NOT_CONSUMED=root['source_score'],root_unchanged=True,weights_unchanged=True,
            wall_seconds=time.perf_counter()-began)
        rows.append(row)
        with (out/'returned.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(L.record_value(row),allow_nan=False,separators=(',',':'))+'\n')
    result=dict(source=p['source'],rows=rows,queries=queries,nodes=nodes,wall_seconds=time.perf_counter()-start,CPU_seconds=time.process_time()-cpu,
        new_games=0,new_training=0,source_Q_returns_rerun=0,default_change=False)
    write(out/'results.json',result);print(json.dumps(dict(queries=queries,nodes=nodes,wall_seconds=result['wall_seconds'],
        complete=sum(x['status']=='COMPLETE' for x in rows),observed_rows=sum(x.get('observed_rows',0) for x in rows),
        nonzero_free_gradient_rows=sum(any(x.get('gradient') or []) for x in rows),
        changed_actions=sum(not x.get('source_action_equal',False) for x in rows if x['status']=='COMPLETE')),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
    a=s.add_parser('prepare');a.add_argument('base',type=Path);a.add_argument('out',type=Path)
    a=s.add_parser('run');a.add_argument('out',type=Path);a=p.parse_args()
    prepare(a.base,a.out) if a.cmd=='prepare' else run(a.out)
