"""Prospectively frozen pure-Leaper q-order generalization; no oracle labels."""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import argparse,hashlib,json,random,time,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from generic_chess.session.serialization import serialize_game_record
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
PAIRS=((5,7),(6,9),(7,12),(9,17),(10,19),(11,20),(12,23),(13,24))

def prepare(d):
    assert not d.exists(), 'new registration only'
    d.mkdir(parents=True);rules={};cases=[];rng=random.Random(20261025)
    for ri,(a,b) in enumerate(PAIRS):
        r=replace(L.definition(a,b),max_ply=64);raw=L.ruleset_to_dict(r)
        rh=hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':')).encode()).hexdigest();rules[rh]=raw
        c=L.compile_rule(r);initial=L.GameSession(c)
        for ply in (0,5):
            s=initial
            if ply:
                for attempt in range(100):
                    s=L.GameSession(c)
                    for _ in range(ply):
                        legal=sorted(s.legal_actions(),key=str)
                        if not legal:break
                        s.submit(legal[rng.randrange(len(legal))])
                        if s.state.terminal_status.is_terminal:break
                    if s.state.ply_count==ply and not s.state.terminal_status.is_terminal:break
                else:raise RuntimeError('predeclared walk generation failed; no query')
            rec=json.loads(serialize_game_record(s.to_record()))
            assert L.state_sha(replay(c,rec).state)==L.state_sha(s.state)
            cases.append(dict(key=f'r{ri}-p{ply}',rule_sha256=rh,masks=[a,b],actor=s.state.position.side_to_move,record=rec,state_sha256=L.state_sha(s.state),legal_frontier=[L.record_value(x) for x in s.legal_actions()]))
    write_json(d/'inputs.json',dict(prepared_at=stamp(),rules=rules,cases=cases,seed=20261025,exposure='Prospective fixed mask pairs chosen after prior exposed q-order results; not independent WDL holdout.',selection='All8 fixed pairs at initial/p5 nonterminal full history; deterministic random legal walks, up to100 attempts. No Player outcomes used. No graph/solver calls.',truth='UNKNOWN; common-depth value parity and total cost only.'))
    slots=[]
    for i,case in enumerate(cases):
        for ordered in ((False,True) if i%2==0 else (True,False)):
            slots.append(dict(key=case['key'],ordered=ordered))
    write_json(d/'plan.json',dict(prepared_at=stamp(),source_sha256=sha(Path(__file__)),inputs_sha256=sha(d/'inputs.json'),slots=slots,limits=dict(max_depth=64,max_nodes=10000000,max_time_seconds=120.0),batch_seconds=5100.0,hypothesis='Does existing q-order reduce work/time across prospectively fixed pureLeaper rules while preserving common completed-depth root scores?',decision='Retain/reject current q-order cost rationale across these rules; do not activate default or infer strength from parity/depth.',estimate='32 serial calls at120s, <=64min query cap plus replay/records <10min. Entire expected run <120min. No source query refills.',fairness='Fresh Player/TT, diskfalse, default dynamic evaluator,Q4/hard8; sole difference existing use_ordered_qsearch. Root observer common both. Alternate arm order percase. Full history/maxply64/repetition4 retained.',missing='Incomplete depth UNKNOWN; no parity when no common completed depth. Actual final action/terminal source differs from value parity; no WDL truth labels.',stops='Cooperative own stop cached250ms; batch5100s; no retry/refill/worker.',source_scope='8 prospective exact rules/16 histories/two actor seats; sampled costs, not rule-class-wide success.'))
    print('FROZEN',len(cases),'histories',len(slots),'queries',flush=True)

def run(d):
    from generic_chess.ai.alphabeta import search as S
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    p=L.load(d/'plan.json');data=L.load(d/'inputs.json')
    assert sha(Path(__file__))==p['source_sha256'] and sha(d/'inputs.json')==p['inputs_sha256']
    assert not(d/'queries.jsonl').exists() and not(d/'receipt.json').exists(),'no refill'
    tick=time.perf_counter();cpu=time.process_time();began=stamp();original=S.negamax;attempted=0;calls=0;status='FAILED'
    class Stop:
        last=0.;flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25:self.last=now;self.flag=stopped()or now-tick>=p['batch_seconds']
            return self.flag
    try:
        for index,slot in enumerate(p['slots']):
            if Stop().is_cancelled():raise RuntimeError('stop/batch limit; missing slots UNKNOWN')
            case=next(c for c in data['cases'] if c['key']==slot['key'])
            c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]))
            s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']
            player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_ordered_qsearch=slot['ordered']))
            root=[];its=[]
            def observe(*args,**kw):
                r=original(*args,**kw)
                if args[4]==0:root[:]=[r]
                return r
            S.negamax=observe;start=stamp();qt=time.perf_counter();qc=time.process_time()
            def progress(depth,nodes,qnodes):
                r=root[0];it=dict(depth=depth,nodes=nodes,qnodes=qnodes,elapsed=time.perf_counter()-qt,score=r.score,action=L.record_value(r.best_action))
                its.append(it);append(d/'iterations.jsonl',dict(slot=slot,**it))
            attempted+=1
            dec=player.choose_action(s,SearchLimits(**p['limits']),cancel_token=Stop(),progress_callback=progress)
            ended=stamp();seconds=time.perf_counter()-qt
            row=dict(index=index,slot=slot,actor=case['actor'],rule_sha256=case['rule_sha256'],state_sha256=case['state_sha256'],started_at=start,query_ended_at=ended,seconds=seconds,cpu_seconds=time.process_time()-qc,decision=L.record_value(dec),iterations=its,evaluation_profile=L.record_value(player.evaluation_profile),native_availability=player.native_legality_provider.availability_metrics)
            append(d/'queries.jsonl',row);calls+=1
            assert L.state_sha(s.state)==case['state_sha256']
            pv=replay(c,case['record'])
            for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a)
            print('PROSPECTIVE',index+1,'/',len(p['slots']),slot,'D',dec.completed_depth,dec.score,dec.termination_reason,round(seconds,3),flush=True)
        status='CLOSED'
    except Exception:
        write_json(d/'failure.json',dict(at=stamp(),traceback=traceback.format_exc(),attempted=attempted,returns=calls));raise
    finally:
        S.negamax=original
        write_json(d/'receipt.json',dict(status=status,started_at=began,ended_at=stamp(),seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-cpu,attempted=attempted,queries=calls,planned=len(p['slots']),source_sha256=p['source_sha256']))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('mode',choices=['prepare','run']);a.add_argument('--directory',required=True,type=Path);x=a.parse_args();(prepare if x.mode=='prepare' else run)(x.directory)
