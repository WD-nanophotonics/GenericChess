"""Fixed complete-input search-performance study; reuses production benchmark APIs."""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import asdict,replace
from unittest.mock import patch
import argparse,json,time,hashlib,platform,sys,subprocess,cProfile,pstats
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.verify_leaper_delayed_capture import load
from scripts.research_record import record_value
from generic_chess.ai.benchmark import audit_suite
from generic_chess.ai.benchmark.core_profiling import core_function_timings
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.audit_instrumentation import TimingAuditRecorder
from tools.local_agent.common import write_json

def stamp():return datetime.now(timezone.utc).isoformat()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def gate(p):
    if datetime.now(timezone.utc)>=datetime.fromisoformat(p['deadline']):raise RuntimeError('original total deadline; no refill')
def prepare(d):
    plan=load(d/'plan.json');gate(plan)
    old=Path('docs/research/data/leaper_support_and_delayed_win_20261024')
    reg=load(old/'existence-registration.json.gz');m=load(old/'existence-completed.json.gz')
    rr=L.ruleset_from_dict(reg['complete_rules']['6']);c=L.compile_rule(rr)
    # Fixed complete root and first forcing capture, never a synthetic state.
    z=replay(c,next(row for row in m['rows']if row['H']==6)['root']['record']);solved=[record_value(z.to_record())]
    from generic_chess.core.actions import action_source_square,action_target_square
    a=next(a for a in z.legal_actions()if (action_source_square(a).file,action_source_square(a).rank,action_target_square(a).file,action_target_square(a).rank)==(0,0,0,1))
    z.submit(a);solved.append(record_value(z.to_record()))
    cases=[]
    def add(name,rule,records,labels):
        for i,record in enumerate(records):
            cc=L.compile_rule(rule);ss=replay(cc,record)
            cases.append(dict(key=name+'_'+str(i),rule=L.ruleset_to_dict(rule,include_metadata=True),record=record,source=labels[i],expected_WDL=([1,-1][i] if name=='solved3' else None),side=ss.state.position.side_to_move,ply=ss.state.ply_count,result=record_value(ss.result),input_sha256=digest([L.ruleset_to_dict(rule,include_metadata=True),record])))
    add('solved3',rr,solved,['published all-defense ply3WIN root','published only-defense child; role1 LOSS'])
    rr=L.definition(3,8);cc=L.compile_rule(rr);ss=L.GameSession(cc);records=[record_value(ss.to_record())]
    for _ in range(3):
        if ss.result.status.value!='ongoing':break
        ss.submit(sorted(ss.legal_actions(),key=str)[0])
    records.append(record_value(ss.to_record()));add('six4',rr,records,['existing leaper_design.definition(3,8)6actors','lexical3ply fixed opening, not chosen by search outcome'])
    with patch.object(audit_suite,'compile_ruleset',side_effect=lambda r:r):rr=audit_suite._hb_multi_promo()
    cc=L.compile_rule(rr);ss=L.GameSession(cc);records=[record_value(ss.to_record())]
    for _ in range(6):
        if ss.result.status.value!='ongoing':break
        aa=list(ss.legal_actions())
        # Freeze exogenous opening favoring semantic promotions, then lexical.
        ss.submit(sorted(aa,key=lambda a:(getattr(a,'promotion_target_id',None)is None,str(a)))[0])
    records.append(record_value(ss.to_record()));add('promo6',rr,records,['existing audit_suite.hb_multi_promo full rule','promotion-first lexical6ply opening; drops/captures not removed'])
    write_json(d/'inputs.json',dict(cases=cases,started_at=stamp(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),base_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),python=platform.python_version(),platform=platform.system()+' '+platform.release()))
    print('prepared',[(x['key'],x['side'],x['ply'],x['result']['status'])for x in cases],flush=True)

def limits(mode,value):
    if mode=='depth':return SearchLimits(max_depth=int(value),max_nodes=20000,max_time_seconds=30,quiescence_max_depth=0)
    if mode=='nodes':return SearchLimits(max_depth=64,max_nodes=int(value),max_time_seconds=None,quiescence_max_depth=0)
    if mode=='wall':return SearchLimits(max_depth=64,max_nodes=None,max_time_seconds=float(value),quiescence_max_depth=0)
    raise ValueError(mode)

def run(d,phase,candidate=None):
    p=load(d/'plan.json');inp=load(d/'inputs.json');out=d/(phase+'.jsonl')
    if out.exists():raise ValueError('new phase required, no automatic retry')
    tuning=SearchTuning() if candidate is None else replace(SearchTuning(),**{candidate:True})
    started=stamp();proc=time.process_time();tick=time.perf_counter()
    specs=[('depth',2),('depth',3),('nodes',512),('nodes',4096),('wall',.5),('wall',2.)]
    for ci,case in enumerate(inp['cases']):
        gate(p);setup=time.perf_counter();c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=tuning);setup_s=time.perf_counter()-setup
        for mode,value in specs:
            gate(p);player.reset();before=record_value(s.to_record());query_started=stamp();t=time.perf_counter();cpu=time.process_time()
            try:
                dec=player.choose_action(s,limits(mode,value));row=dict(case=case['key'],input_sha256=case['input_sha256'],mode=mode,budget=value,tuning=asdict(tuning),TT='cold',started_at=query_started,ended_at=stamp(),wall_seconds=time.perf_counter()-t,cpu_seconds=time.process_time()-cpu,setup_seconds=setup_s,decision=record_value(dec),legal=dec.action in s.legal_actions()if dec.action is not None else s.result.status.value!='ongoing',state_unchanged=before==record_value(s.to_record()),native_provider_available=player.native_legality_provider is not None)
                assert row['legal']and row['state_unchanged']
            except Exception as exc:row=dict(case=case['key'],mode=mode,budget=value,failure=type(exc).__name__+':'+str(exc),wall_seconds=time.perf_counter()-t,cpu_seconds=time.process_time()-cpu)
            with out.open('a',encoding='utf-8')as f:f.write(json.dumps(row)+'\n')
            print(phase,case['key'],mode,value,'D',row.get('decision',{}).get('completed_depth'),'n',row.get('decision',{}).get('nodes'),'q',row.get('decision',{}).get('qnodes'),'t',round(row['wall_seconds'],3),row.get('failure',''),flush=True)
        # Actual same-player warm probe, separate from all cold controls.
        if phase=='baseline':
            player.reset();lim=limits('depth',2);cold=player.choose_action(s,lim);warm=player.choose_action(s,lim)
            with out.open('a',encoding='utf-8')as f:f.write(json.dumps(dict(case=case['key'],mode='warm_depth',budget=2,TT='same player, one exactroot depth2 prime',prime=record_value(cold),decision=record_value(warm)))+'\n')
    write_json(d/(phase+'-receipt.json'),dict(started_at=started,ended_at=stamp(),wall_seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-proc,queries=6*len(inp['cases'])+(2*len(inp['cases'])if phase=='baseline'else 0),producer_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))

def profile(d):
    p=load(d/'plan.json');inp=load(d/'inputs.json');rows=[]
    for case in inp['cases'][::2]:
        gate(p);c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);player=AlphaBetaPlayer(c,use_disk_cache=False);rec=TimingAuditRecorder();pr=cProfile.Profile();pr.enable();dec=player.choose_action(s,limits('nodes',512),recorder=rec);pr.disable()
        stats=pstats.Stats(pr);top=sorted([(f[0].replace('\\','/').split('GenericChess 2/')[-1],f[1],f[2],v[0],v[2],v[3])for f,v in stats.stats.items()],key=lambda x:x[-1],reverse=True)[:35]
        rows.append(dict(case=case['key'],decision=record_value(dec),instrumented=rec.snapshot(),cprofile_top_cumulative=top,core_micro=core_function_timings(c,s.state,repeats=3,warmup=1)))
    write_json(d/'profiles.json',dict(rows=rows,note='Instrumented/cProfile run is separate from timing controls; nested durations not additive. Root Core microbench is not whole-search share.'))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('phase',choices=['prepare','baseline','candidate','profile']);a.add_argument('--directory',type=Path,required=True);a.add_argument('--candidate');v=a.parse_args()
    if v.phase=='prepare':prepare(v.directory)
    elif v.phase=='profile':profile(v.directory)
    else:run(v.directory,v.phase,v.candidate)
