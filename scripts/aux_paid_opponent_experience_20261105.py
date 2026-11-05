"""One frozen short-horizon opponent-experience control using play_episode.
DEFAULT values stay outside candidate TD; this is not PRIMARY Q-quality work.
"""
from __future__ import annotations
import argparse,gzip,json,time
from dataclasses import asdict
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,TDLeafEpisode,Receipt,SessionChoice,BudgetEnd,play_episode
from generic_chess.learning.mainline_search import search
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
PIN='549b159a0129e2f96062935ce3786ddf3efb08a1'
def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def write(p,x):p.write_text(json.dumps(L.record_value(x),allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
def prepare(base,out):
    out.mkdir(exist_ok=False);worlds=read(base/'inputs.json.gz')['rows']
    slots=[dict(id=2*f+i,family=f,foe=a) for f in range(6) for i,a in enumerate(('Unit','DEFAULT') if f%2==0 else ('DEFAULT','Unit'))]
    plan=dict(source=PIN,worlds=worlds,slots=slots,
        question='Does a fixed rule-derived DEFAULT opponent expose actual own-model TD transitions differently from Unit on the same six new source initial states?',
        hypothesis='Initial q0D2targets allsix zero freegradient;differentopponentchoices may change ownconsumedfeatures/errors,but do not imply strength or CCsupport.',
        selection='all six published families in source order,first literal initialhistory,no outcomes/features select or replace roots;bothfoes atsame4plyhorizon',
        model=dict(weights=[1,1,1]+[0]*24,fixed=0,scale=10),eta=.05,lam=.95,
        depth=2,horizon=4,query_nodes=2048,query_seconds=1.5,game_nodes=8192,game_seconds=5,whole_seconds=60,
        max_queries=48,max_nodes=98304,foe='Unit uses same q0D2 model;DEFAULT uses existingpublicQ4/hard8,PVS,fullQ default,rule-derived evaluation,freshPlayer/TTperquery,diskOFF;not proven stronger;setup/returnpaid',
        stops='one12slotexecution,earlyterminal/UNKNOWN/NOT_RUNretained,nofittingselect/refill/tuning/default/rules/PRIMARYtimingobserver',
        endpoints='actual consumed candidate-only gradients/error/netupdate,paidqueries/nodes/fullhistory;4plyUNKNOWNnotDRAW,notstrength/heldout/intrinsicprice')
    write(out/'plan.json',plan);print('frozen12slots;0Player')
def run(out):
    p=read(out/'plan.json')
    with (out/'execution.json').open('x',encoding='utf-8') as s:json.dump({'started_utc':time.time()},s)
    began=time.perf_counter();cpu=time.process_time();queries=nodes=0;fatal=None;rows=[]
    compiled={w['family']:L.compile_rule(L.ruleset_from_dict(w['RuleSet'])) for w in p['worlds']}
    def guard():
        if role_stop_requested():raise BudgetEnd('USER_STOP')
        if time.perf_counter()-began>=p['whole_seconds']:raise BudgetEnd('WHOLE_CAP_UNKNOWN')
        if queries>=p['max_queries'] or nodes>=p['max_nodes']:raise BudgetEnd('WHOLE_WORK_CAP_UNKNOWN')
    with (out/'episodes.jsonl').open('x',encoding='utf-8',buffering=1) as stream:
        for slot in p['slots']:
            eb=time.perf_counter();events=[];foe_raw=[];row=dict(slot=slot)
            if fatal or time.perf_counter()-began>=p['whole_seconds']:
                row.update(status='NOT_RUN_UNKNOWN',reason=fatal or 'WHOLE_CAP')
            else:
                world=p['worlds'][slot['family']]
                env=FixedScaleSessionEnv(restore(compiled[slot['family']],world['record']),unit_type='A',feature_mode='count_pairs')
                model=Model(**p['model']);foe=Model(**p['model']);before=list(model.weights)
                def external(state,current,*,depth,nodes,seconds,seed,cancel):
                    if slot['foe']=='Unit':
                        return search(state,current,depth=depth,nodes=nodes,seconds=min(seconds,p['query_seconds']),seed=seed,cancel=cancel)
                    cb=time.perf_counter();allowed=min(seconds,p['query_seconds'])
                    class Stop:
                        reason=None
                        def is_cancelled(self):
                            try:cancel()
                            except BudgetEnd as e:self.reason=str(e)
                            return self.reason is not None
                    stop=Stop();cancel()
                    player=AlphaBetaPlayer(state.session.compiled,use_disk_cache=False,tuning=SearchTuning())
                    d=player.choose_action(state.session,SearchLimits(max_depth=depth,max_nodes=nodes,
                        max_time_seconds=max(1e-9,allowed-(time.perf_counter()-cb)),quiescence_max_depth=4,
                        quiescence_hard_max_depth=8),cancel_token=stop)
                    elapsed=time.perf_counter()-cb
                    foe_raw.append(dict(decision=asdict(d),full_service_seconds=elapsed))
                    ok=d.action is not None and stop.reason is None and elapsed<=allowed
                    choice=SessionChoice('ACTION',action=d.action) if ok else None
                    return Receipt(choice,None,None,False,(),d.nodes+d.qnodes,ok,0,elapsed,
                        stop.reason or ('FOE_TIME_CAP_UNKNOWN' if elapsed>allowed else d.termination_reason))
                def observed(ply,actor,r):
                    nonlocal queries,nodes
                    queries+=1;nodes+=r.nodes
                    events.append(dict(local_ply=ply,actor=actor,record_before=L.record_value(env.session.to_record()),receipt=asdict(r)))
                try:
                    result=play_episode(env,model,opponent=foe,learner=TDLeafEpisode(eta=p['eta'],lam=p['lam']),
                        learner_color=1,horizon=p['horizon'],depth=p['depth'],opponent_depth=p['depth'],
                        query_nodes=p['query_nodes'],max_nodes=p['game_nodes'],seconds=p['game_seconds'],
                        cancel=guard,on_query=observed,opponent_search=external,search_backend='mainline')
                    row.update(status='RETURNED',result=asdict(result))
                except Exception as e:
                    fatal=type(e).__name__+':'+str(e);row.update(status='ERROR',reason=fatal)
                row.update(before=before,after=model.weights,events=events,foe_raw=foe_raw,
                    initial_record=world['record'],final_record=L.record_value(env.session.to_record()),
                    terminal=L.record_value(env.session.result))
            row['wall_seconds']=time.perf_counter()-eb;rows.append(row)
            stream.write(json.dumps(L.record_value(row),allow_nan=False,separators=(',',':'))+'\n')
    summary=dict(source=p['source'],slots=len(rows),queries=queries,nodes=nodes,wall_seconds=time.perf_counter()-began,
        CPU_seconds=time.process_time()-cpu,fatal=fatal,returned=sum(r['status']=='RETURNED' for r in rows),
        new_Q_source_games=0,no_strength_claim=True)
    write(out/'summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':
    a=argparse.ArgumentParser();s=a.add_subparsers(dest='cmd',required=True)
    t=s.add_parser('prepare');t.add_argument('base',type=Path);t.add_argument('out',type=Path)
    t=s.add_parser('run');t.add_argument('out',type=Path);z=a.parse_args()
    prepare(z.base,z.out) if z.cmd=='prepare' else run(z.out)
