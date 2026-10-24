"""Scoped full-history ordering diagnosis; published capsules remain data only."""
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import argparse, gzip, hashlib, json, time
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from tools.local_agent.common import write_json


def stamp(): return datetime.now(timezone.utc).isoformat()
def sha(b): return hashlib.sha256(b).hexdigest()
def read(p): return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())


def prepare(d):
    started=stamp(); tick=time.perf_counter()
    raw=(d/'evidence.json.gz').read_bytes(); packet=read(d/'evidence.json.gz'); manifest=read(d/'manifest.json')
    assert sha(raw)==manifest['packet_sha256']
    docs=packet['documents_utf8']
    for key,value in docs.items():
        assert sha(value.encode())==manifest['documents_utf8'][key]['sha256']
    cfg=json.loads(docs['cost/plan.json']); game=json.loads(docs['cost/game-000.json']); truth=json.loads(docs['graph/trace-truth.json'])
    c=L.compile_rule(L.ruleset_from_dict(cfg['world']['rule']))
    cases=[]
    for ply in (48,50,52):
        q=next(x for x in truth['queries'] if x['ply']==ply)
        record=dict(game['final_record']);record['actions']=record['actions'][:ply]
        s=replay(c,record)
        assert L.state_sha(s.state)==q['state_sha256']
        assert s.state.ply_count==ply and s.result.status.value=='ongoing'
        legal=[L.record_value(a) for a in s.legal_actions()]
        assert len(legal)==len(q['arms']) and all(a in legal for a in [x['action'] for x in q['arms']])
        children=[]
        for arm in q['arms']:
            child=replay(c,record);child.submit(L.match_action(child,arm['action']))
            children.append(dict(action=arm['action'],truth=arm['truth'],state_sha256=L.state_sha(child.state),record=L.record_value(child.to_record()),result=L.record_value(child.result)))
        original=next(x for x in game['events'] if x.get('ply')==ply and x['kind']=='candidate')
        cases.append(dict(ply=ply,rule=cfg['world']['rule'],record=record,state=L.record_value(s.state),state_sha256=L.state_sha(s.state),root_truth=q['root'],children=children,original_receipt=original['receipt']))
    write_json(d/'prepared.json',dict(started_at=started,ended_at=stamp(),seconds=time.perf_counter()-tick,cases=cases,
        qualification='Original published graph/barrier theorem labels, not independently re-solved here. Current Core strict full-history replay and complete root action binding only. No all-node oracle.',new_Player_queries=0,new_graph_or_solver_calls=0))
    old=Path('docs/research/data/pure_leaper_search_20261024'); grouped=defaultdict(list)
    for name in ('bench','pvs'):
        for line in gzip.decompress((old/(name+'.jsonl.gz')).read_bytes()).splitlines():
            r=json.loads(line);v=r['decision']
            grouped[(name,r['case'],r.get('mode','fixed-depth'),r.get('pvs_enabled',r.get('availability_enabled')))].append(r)
    rows=[]
    for key,rs in grouped.items():
        totals={k:sum(r['decision'][k] for r in rs) for k in ('nodes','qnodes','beta_cutoffs','pvs_null_window_searches','pvs_researches','ordering_seconds','legal_generation_seconds','evaluation_seconds','capture_qactions','checking_move_qactions','in_check_qnodes','stand_pat_cutoffs')}
        totals.update(phase=key[0],case=key[1],mode=key[2],enabled=key[3],physical_calls=len(rs),completed_depths=[r['decision']['completed_depth']for r in rs],complete=[r.get('complete',True)for r in rs],outer_seconds=sum(r['wall_seconds']for r in rs))
        totals['q_event_fraction']=totals['qnodes']/(totals['nodes']+totals['qnodes']);rows.append(totals)
    write_json(d/'retained-work-distribution.json',dict(new_Player_queries=0,rows=rows,interpretation='budget events not distinct positions; main beta cutoff count excludes q stand-pat; timing components may nest; PVS censored rows stay separate'))
    own=Path('docs/research/data/leaper_support_and_delayed_win_20261024')
    cert=read(own/'existence-completed.json.gz'); summary=[]
    for r in cert['rows']:
        root=r['root'];summary.append(dict(origin=r['origin'],H=r['H'],record=root['record'],state_sha256=root['state_sha256'],legal_first=len(root['legal_actions']),listed_first=len(r['all_white_first']),defenses=len(r['all_black_defenses']),covered_finish_results=[(x.get('finish') or {}).get('result')for x in r['all_black_defenses']]))
    write_json(d/'truth-coverage.json',dict(own_shallow_controls=summary,four_actor_source='26d414cce26d44e7d2cfae84a20195fa715f2906',four_actor_cases=[dict(ply=x['ply'],root=x['root_truth'],actions=len(x['children']),child_values=[z['truth']['value']for z in x['children']])for x in cases],unknown='No complete internal-node labels and no ideal fixed-depth heuristic ordering. Seven winning actions at ply50 are published WDL evidence, not new proof or unexposed holdout.'))
    print(json.dumps(dict(prepared=[(x['ply'],x['root_truth'],len(x['children']))for x in cases],work_rows=len(rows),ended_at=stamp())))


def run(d):
    from generic_chess.ai.alphabeta import search as S
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    from generic_chess.ai.evaluation.config import MATE_THRESHOLD
    from tools.local_agent.session import stopped
    from scripts.pure_leaper_search_study import append
    reg=read(d/'ordering-plan.json'); cases=read(d/'prepared.json')['cases']
    assert sha(Path(__file__).read_bytes())==reg['source_sha256']
    out=d/'ordering-queries.jsonl'
    if out.exists(): raise ValueError('No restart/refill of this diagnostic')
    original=S.MoveOrderer; original_negamax=S.negamax; began=stamp(); tick=time.perf_counter();cpu=time.process_time();calls=0

    class Material:
        def evaluate(self,state):
            value=sum((1 if p.owner==0 else -1) for p in state.position.board if p is not None and p.current_type_id in ('A','B'))
            return value if state.position.side_to_move==0 else -value
        def capture_order_value(self,mover,victim): return 0

    class Stop:
        last=0.; flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25:
                self.last=now;self.flag=stopped() or datetime.now(timezone.utc)>=datetime.fromisoformat(reg['deadline'])
            return self.flag

    try:
        for slot in reg['slots']:
            if Stop().is_cancelled(): raise RuntimeError('stop/deadline; missing slots UNKNOWN')
            case=next(x for x in cases if x['ply']==slot['ply']);c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record'])
            labels={L.match_action(s,x['action']):(x['truth']['value'],x['truth']['rank']) for x in case['children']}
            latest={};hist=defaultdict(int);order_seconds=[0.];root_orders=[]

            class Ranked(list):
                def __init__(self,values,depth):super().__init__(values);self.depth=depth
                def __iter__(self):
                    for index,a in enumerate(super().__iter__()):
                        latest[self.depth]=(index,len(self));yield a

            class DiagnosticOrderer(original):
                def order(self,state,actions,evaluator,depth,tt_move,prev_action,tuning):
                    ordered=super().order(state,actions,evaluator,depth,tt_move,prev_action,tuning)
                    if state.ply_count==case['ply']:
                        t=time.perf_counter()
                        if slot['arm']=='root_truth':
                            ordered=sorted(ordered,key=lambda a:(-labels[a][0],labels[a][1] if labels[a][1] is not None else 10**9))
                        order_seconds[0]+=time.perf_counter()-t
                        root_orders.append(dict(depth=depth,actions=[L.record_value(a)for a in ordered]))
                    return Ranked(ordered,depth)
                def record_killer(self,depth,action):
                    index,n=latest[depth];hist[(depth,index,n)]+=1
                    super().record_killer(depth,action)

            S.MoveOrderer=DiagnosticOrderer
            qstart=stamp();qt=time.perf_counter();qc=time.process_time();iterations=[]
            p=AlphaBetaPlayer(c,evaluator_override=Material(),use_disk_cache=False,use_native_semantic_availability=False,tuning=SearchTuning(use_root_tactical=False,require_full_pv=True))
            root_result=[]
            def capture_root(*args,**kwargs):
                result=original_negamax(*args,**kwargs)
                if args[4]==0:root_result[:]=[(args[1],result)]
                return result
            S.negamax=capture_root
            def progress(depth,nodes,qnodes):
                assert root_result and root_result[0][0]==depth
                result=root_result[0][1];assert result.best_action in labels
                r=dict(depth=depth,nodes=nodes,qnodes=qnodes,elapsed=time.perf_counter()-qt,score=result.score,action=L.record_value(result.best_action),published_child_WDL=labels[result.best_action][0],score_proves_win=result.score>=MATE_THRESHOLD)
                iterations.append(r);append(d/'ordering-iterations.jsonl',dict(slot=slot,**r));print('ITER',slot,depth,round(r['elapsed'],3),r['score'],r['published_child_WDL'],flush=True)
            dec=p.choose_action(s,SearchLimits(max_depth=64-case['ply'],max_nodes=10000000,max_time_seconds=reg['seconds_per_query'],quiescence_max_depth=0,quiescence_hard_max_depth=0),cancel_token=Stop(),progress_callback=progress)
            qend=stamp();assert L.state_sha(s.state)==case['state_sha256'];assert dec.action in labels
            leaf=replay(c,case['record'])
            for action in dec.principal_variation: assert action in leaf.legal_actions();leaf.submit(action)
            row=dict(slot=slot,started_at=qstart,query_ended_at=qend,ended_at=stamp(),cpu_seconds=time.process_time()-qc,outer_seconds=time.perf_counter()-qt,decision=L.record_value(dec),published_child_WDL=labels[dec.action][0],iterations=iterations,root_orders=root_orders,root_order_added_seconds=order_seconds[0],cutoff_positions=[dict(depth=k[0],index=k[1],frontier=k[2],count=v)for k,v in sorted(hist.items())],PV_final_result=L.record_value(leaf.result),PV_plies=len(dec.principal_variation))
            assert sum(hist.values())==dec.beta_cutoffs
            append(out,row);calls+=1;print('DONE',slot,dec.completed_depth,dec.termination_reason,round(row['outer_seconds'],3),flush=True)
        status='CLOSED'
    except Exception:
        status='FAILED';raise
    finally:
        S.MoveOrderer=original
        S.negamax=original_negamax
        write_json(d/'ordering-receipt.json',dict(status=locals().get('status','FAILED'),started_at=began,ended_at=stamp(),seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-cpu,queries=calls,source_sha256=reg['source_sha256']))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run']);p.add_argument('--directory',type=Path,required=True);a=p.parse_args();globals()[a.mode](a.directory)
