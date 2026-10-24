"""Pure-Leaper-only availability study: full inputs, frozen caps and actual work."""
from pathlib import Path
from dataclasses import replace
from datetime import datetime, timezone
import argparse, hashlib, json, time, subprocess, traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.search_performance_study import stamp, digest, gate
from generic_chess.core.pieces import Piece
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.benchmark.runner import play_game, RunConfig
from generic_chess.ai.benchmark.profiles import PROFILES
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped


def guard(d):
    gate(L.load(d/'plan.json'))
    if stopped():
        raise RuntimeError('PRIMARY stop persists')


def append(p, row):
    with p.open('a',encoding='utf-8') as f:
        f.write(json.dumps(row,ensure_ascii=True)+'\n'); f.flush()


def rule(n, a, b):
    template=L.definition(a,b)
    board=[[None]*n for _ in range(n)]
    for x,y,owner,tid in [(0,0,0,'K'),(1,0,0,'A'),(0,1,0,'B'),(n-1,n-1,1,'K'),(n-2,n-1,1,'A'),(n-1,n-2,1,'B')]:
        board[y][x]=Piece(owner,tid,tid)
    return replace(template,board_size=n,initial_position=tuple(tuple(r)for r in board),drop_allowed={t:((False,)*(n*n),)*2 for t in ('A','B')},max_ply=96)


def prepare(d):
    guard(d)
    if (d/'inputs.json').exists():raise ValueError('fresh preparation only')
    cases=[];began=stamp();tick=time.perf_counter()
    # Geometric design fixed before queries; no search-dependent root selection.
    for n,a,b in [(4,1,8),(4,3,16),(5,2,8),(5,1,16),(6,3,8),(6,2,16)]:
        rr=rule(n,a,b);c=L.compile_rule(rr);s=L.GameSession(c)
        for prefix in (0,5):
            if prefix:
                for _ in range(5):
                    if s.result.status.value!='ongoing':break
                    s.submit(sorted(s.legal_actions(),key=str)[0])
            raw=L.record_value(s.to_record());rd=L.ruleset_to_dict(rr,include_metadata=True)
            cases.append(dict(key=f'n{n}-a{a}-b{b}-p{prefix}',n=n,masks=[a,b],nominal_prefix=prefix,actual_ply=s.state.ply_count,rule=rd,record=raw,input_sha256=digest([rd,raw]),result=L.record_value(s.result),semantic_fingerprint=s.state.position.ruleset_fingerprint,scope='6actors;fullrules;LeapAtom only;no promotion/drop/hand;maxply96;repetition4'))
    write_json(d/'inputs.json',dict(cases=cases,started_at=began,ended_at=stamp(),wall_seconds=time.perf_counter()-tick,base_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    print('prepared',[(x['key'],x['result']['status'])for x in cases],flush=True)


def player(c, enabled):
    return AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_availability=enabled)


def decision_row(d, case, s, p, enabled, limits, extra):
    guard(d);before=L.record_value(s.to_record());provider=p.native_legality_provider
    assert provider is not None, 'actual Native legal provider required; decline not silently accepted'
    m=provider.availability_metrics;start=stamp();t=time.perf_counter();cp=time.process_time()
    dec=p.choose_action(s,limits);p._study_last_decision=dec;ended=stamp();wall=time.perf_counter()-t;cpu=time.process_time()-cp
    after=provider.availability_metrics;delta={k:v-m.get(k,0)for k,v in after.items()}
    row=dict(case=case['key'],input_sha256=case['input_sha256'],availability_enabled=enabled,limits=L.record_value(limits),started_at=start,ended_at=ended,wall_seconds=wall,cpu_seconds=cpu,availability_delta=delta,decision=L.record_value(dec),**extra)
    assert before==L.record_value(s.to_record()),'query mutated session'
    assert dec.action in s.legal_actions() if dec.action is not None else s.result.status.value!='ongoing'
    assert delta.get('queries',0)>0 if enabled else delta=={}
    return row


def compare(pair):
    a,b=[r['decision']for r in pair]
    fs=('score','completed_depth','nodes','qnodes','principal_variation','tt_hits','tt_cutoffs','runtime_pushes','runtime_pops')
    return all(a[f]==b[f]for f in fs)


def bench(d, pilot=False):
    guard(d);name='pilot' if pilot else 'bench';out=d/(name+'.jsonl')
    if out.exists():raise ValueError('no automatic rerun/refill')
    reg=L.load(d/('pilot-plan.json' if pilot else 'execution-plan.json'));inputs=L.load(d/'inputs.json')['cases'];started=stamp();t=time.perf_counter();cp=time.process_time();count=0
    try:
        for key in reg['cases']:
            case=next(x for x in inputs if x['key']==key);cc=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(cc,case['record'])
            if s.result.status.value!='ongoing':
                append(d/(name+'-skipped.jsonl'),dict(case=key,reason='terminal full root',result=L.record_value(s.result)));continue
            # Fresh Player per call controls both TT and native action cache.
            for rep in range(reg['repetitions']):
                for mode in reg['modes']:
                    pair=[];order=(False,True) if rep in (0,3) else (True,False)
                    limits=SearchLimits(max_depth=reg['depth'],max_nodes=reg['nodes'] if mode=='nodes' else None,max_time_seconds=reg['safety_seconds'] if mode=='nodes' else reg['seconds'],quiescence_max_depth=4,quiescence_hard_max_depth=8)
                    for enabled in order:
                        guard(d);setup=time.perf_counter();p=player(cc,enabled);setup_s=time.perf_counter()-setup
                        row=decision_row(d,case,s,p,enabled,limits,dict(rep=rep,mode=mode,order=list(order),TT='cold',native_action_cache='fresh_player',player_setup_seconds=setup_s));append(out,row);pair.append(row);count+=1
                        print(name,key,rep,mode,enabled,row['decision']['completed_depth'],row['decision']['nodes']+row['decision']['qnodes'],round(row['wall_seconds'],3),flush=True)
                    if mode=='nodes' and all(r['decision']['termination_reason']!='time_limit'for r in pair):
                        assert compare(pair),'fixed-work/value/PV changed'
        status='CLOSED'
    except Exception:
        status='FAILED';raise
    finally:
        write_json(d/(name+'-receipt.json'),dict(status=locals().get('status','FAILED'),started_at=started,ended_at=stamp(),wall_seconds=time.perf_counter()-t,cpu_seconds=time.process_time()-cp,queries=count,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))


class Arm:
    def __init__(self,d,case,p,enabled,path):self.d=d;self.case=case;self.player=p;self.enabled=enabled;self.path=path
    def choose_action(self,s,limits):
        self.last_session=s
        row=decision_row(self.d,self.case,s,self.player,self.enabled,limits,dict(before_record=L.record_value(s.to_record())))
        append(self.path,row)
        # Return the original typed decision, not a serialized reconstruction.
        return self.player._study_last_decision


def games(d):
    guard(d);reg=L.load(d/'execution-plan.json');cases=L.load(d/'inputs.json')['cases'];out=d/'games.jsonl'
    if out.exists():raise ValueError('new producer only; partial output needs explicit diagnosis')
    start=stamp();t=time.perf_counter();cpu=time.process_time();count=0
    try:
        for key in reg['game_cases']:
            case=next(x for x in cases if x['key']==key);c=L.compile_rule(L.ruleset_from_dict(case['rule']));initial=replay(c,case['record']);opening=initial.to_record().actions
            if initial.result.status.value!='ongoing':
                append(d/'games-skipped.jsonl',dict(case=key,reason='terminal complete initial record'));continue
            for color in (0,1):
                guard(d);name=key+'-candidate'+str(color);path=d/(name+'-turns.jsonl');assert not path.exists()
                cand=Arm(d,case,player(c,True),True,path);control=Arm(d,case,player(c,False),False,path)
                result,events=play_game(c,opening,key,name,color,cand,control,RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),seconds=reg['game_seconds'],nodes=None,max_plies=reg['caller_max_plies']))
                final=getattr(cand,'last_session',getattr(control,'last_session',initial));row=dict(game=name,case=key,input_sha256=case['input_sha256'],candidate_color=color,outcome=L.record_value(result),eligible=result.eligible,events=L.record_value(events),final_record=L.record_value(final.to_record()),final_result=L.record_value(final.result));append(out,row);count+=1
                print('game',name,result.result,result.plies,'eligible',result.eligible,flush=True)
        status='CLOSED'
    except Exception:
        status='FAILED';raise
    finally:
        write_json(d/'games-receipt.json',dict(status=locals().get('status','FAILED'),started_at=start,ended_at=stamp(),wall_seconds=time.perf_counter()-t,cpu_seconds=time.process_time()-cpu,games=count,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('phase',choices=['prepare','pilot','bench','games']);a.add_argument('--directory',type=Path,required=True);args=a.parse_args()
    {'prepare':prepare,'pilot':lambda d:bench(d,True),'bench':bench,'games':games}[args.phase](args.directory)
