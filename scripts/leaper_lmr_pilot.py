"""Frozen LMR-over-PVS development pilot; no desktop/backend activation."""
import argparse,gzip,json,sys,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime,_plain_leaper_hash_patterns
from scripts.leaper_lmr_research_policy import LateQuietReduction
from scripts.leaper_pvs_quality_pilot import make_session,digest,CallerDeadline,provider_metrics,metric_delta
from scripts.leaper_postexchange_source import load,sha,stamp,stopped
from scripts.leaper_check_extension_quality import record_interval
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.research_record import record_value,write_record
from tools.local_agent.common import read_json,write_json


def player(c):
    assert _plain_leaper_hash_patterns(c) is not None
    return AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True),use_native_semantic_legality=True,use_native_semantic_check=True,use_native_semantic_availability=True)


def qualify(row,plan,out):
    begin=stamp();c,s=make_session(row);p=player(c);provider=p.native_legality_provider
    rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses,legal_binding_provider=provider,availability_provider=provider.has_legal_action,check_provider=provider.in_check)
    ctx=S._Context(c,p._evaluator,TranspositionTable(),SearchStatistics(),S._Budget(SearchLimits(max_nodes=2000000,max_time_seconds=20,quiescence_max_depth=4,quiescence_hard_max_depth=8),None),SearchTuning(use_pvs=True),True,True,4,8,None,runtime=rt,first_main_iteration_complete=True)
    original=S.negamax;policy=LateQuietReduction(original);t=time.perf_counter();cpu=time.process_time()
    q=dict(family=row['family'],case_id=row['id'],record_sha256=digest(s.to_record()),actual_tuning=record_value(p._tuning),requested_depth=4,first_main_iteration_complete=True)
    try:
        S.negamax=policy;r=S.negamax(rt.state,4,-S.INF,S.INF,0,ctx);q.update(status='RETURNED',result=record_value(r))
    except S.SearchAborted as e:q.update(status='ABORTED_UNKNOWN',reason=str(e))
    finally:S.negamax=original
    q.update(search_seconds=time.perf_counter()-t,search_cpu_seconds=time.process_time()-cpu,lmr=dict(policy.counts),lmr_classification_seconds=policy.classification_seconds,stats=record_value(ctx.stats))
    write_record(out/f"qualification-{row['family']}.json",q)
    rt.assert_balanced();assert not policy.stack
    if q['status']=='RETURNED':
        pv=make_session(row)[1]
        for a in r.pv:pv.submit(a)
        assert r.best_action in s.legal_actions()
    q['runtime_balanced']=True;q['PV_legal']=q['status']=='RETURNED'
    refs=[load(Path(x)) for x in plan['qualification_references'][str(row['family'])]]
    assert all(x['status']=='RETURNED' and x['record_sha256']==q['record_sha256'] and x['requested_depth']==4 for x in refs)
    q['reused_reference_search_seconds']=sum(x['search_seconds'] for x in refs)/len(refs)
    q['reference_paths']=plan['qualification_references'][str(row['family'])]
    write_record(out/f"qualification-{row['family']}.json",q);record_interval(begin,stamp(),'validation',str(out/f"qualification-{row['family']}.json"),out)
    return q


class GameDeadline(CallerDeadline):
    def __init__(self,deadline):super().__init__(deadline);self.next_stop_read=0;self.stop_reads=0
    def is_cancelled(self):
        now=time.perf_counter()
        if now>=self.next_stop_read:
            self.next_stop_read=now+.1;self.stop_reads+=1
            if stopped():self.observed=True
        return super().is_cancelled()


def choose(c,s,players,owners,seat,on,qid,out):
    begin=stamp();t=time.perf_counter();cpu=time.process_time();token=GameDeadline(t+1.5)
    if seat not in players:players[seat]=player(c);owners[seat]=on
    assert owners[seat] is on
    p=players[seat];assert p._tuning.use_pvs and not p._tuning.use_one_check_extension
    before=s.to_record();before_hash=digest(before);metrics=provider_metrics(p);packing=time.perf_counter()-t;remaining=1.5-packing
    assert remaining>0,'construction exhausted service'
    limits=SearchLimits(max_depth=64,max_nodes=500000,max_time_seconds=remaining,quiescence_max_depth=4,quiescence_hard_max_depth=8)
    original=S.negamax;policy=LateQuietReduction(original)
    try:
        if on:S.negamax=policy
        d=p.choose_action(s,limits,cancel_token=token)
    except BaseException as e:
        fail=dict(query_id=qid,on=on,at=stamp(),error_type=type(e).__name__,error=str(e),elapsed_seconds=time.perf_counter()-t,lmr=dict(policy.counts),decision='NOT_RETURNED')
        write_record(out/f'failure-{qid}.json',fail);record_interval(begin,fail['at'],'research',str(out/f'failure-{qid}.json'),out)
        raise
    finally:S.negamax=original
    end=stamp();wall=time.perf_counter()-t
    q=dict(query_id=qid,status='RETURNED',on=on,policy_id='late-quiet-nonPV-oneply/v1' if on else 'existing-PVS/v1',seat=seat,started_at=begin,ended_at=end,requested_service_seconds=1.5,construction_packing_seconds=packing,limits=record_value(limits),actual_tuning=record_value(p._tuning),decision=record_value(d),record_before_sha256=before_hash,service_wall_seconds=wall,cpu_seconds=time.process_time()-cpu,timing_eligible=wall<=1.65,lmr=dict(policy.counts),lmr_classification_seconds=policy.classification_seconds,policy_owned_TT=True,stop_reads=token.stop_reads,provider_present=metrics['present'],provider_delta=metric_delta(metrics,provider_metrics(p)))
    write_record(out/'returns'/f'{qid}.json',q);record_interval(begin,end,'research',str(out/'returns'/f'{qid}.json'),out)
    v=stamp();assert not policy.stack and s.to_record()==before and d.runtime_depth_balanced
    assert d.action is not None and d.action in s.legal_actions()
    assert metrics['present'] and d.native_legality_fallbacks==d.native_legality_operational_failures==0
    assert q['provider_delta']['availability'].get('declines',0)==0
    from generic_chess.session.session import GameSession
    pv=GameSession.replay(c,before)
    for a in d.principal_variation:pv.submit(a)
    assert s.to_record()==before
    s.submit(d.action);q.update(record_after_sha256=digest(s.to_record()),root_unchanged=True,pv_legal=True)
    record_interval(v,stamp(),'validation',qid+':actualCore/PV/submit',out)
    return q


def endpoints(games):
    scores=[];families={str(f):[] for f in range(8)};outcomes=Counter()
    for g in games:
        score=None
        if g['status']=='TERMINAL' and g['timing_eligible']:
            winner=g['Core_terminal']['winner'];score=.5 if winner is None else float(winner==g['on_seat']);scores.append(score)
            outcomes['DRAW' if winner is None else 'ON_WIN' if score else 'OFF_WIN']+=1
        families[str(g['family'])].append(score)
    positive=sum(len(x)==2 and all(v is not None for v in x) and sum(x)>1 for x in families.values())
    return dict(eligible_terminals=len(scores),planned_games=16,missing=16-len(scores),outcomes=dict(outcomes),ON_points=sum(scores),positive_families=positive,families=families,
                exploratory_gate_passed=len(scores)==16 and positive>=4 and sum(scores)>=.55*16,
                scope='Exposed development LMR increment over PVS reference only;not desktop-default/unseen-family strength or activation')


def run(plan_path,out):
    plan=read_json(plan_path)
    for p,h in plan['files'].items():assert sha(p)==h,p
    assert not out.exists();out.mkdir();(out/'returns').mkdir()
    write_record(out/'frozen.json',plan);rows=json.loads(gzip.decompress(Path(plan['input_packet']).read_bytes()))['rows'];assert len(rows)==8 and {r['family'] for r in rows}==set(range(8))
    import generic_chess.native as native
    module=native._module();bp=Path(module.__file__);binary=dict(module=bp.name,sha256=sha(bp),bytes=bp.stat().st_size,python=sys.version)
    assert binary['sha256']==plan['reference_binary_sha256'],'reference binary changed;do not reuse controls'
    write_record(out/'loaded-binary.json',binary)
    quals=[];halt=None
    for row in rows:
        if stopped():halt='scoped_stop';break
        q=qualify(row,plan,out);quals.append(q);print(dict(qual_family=row['family'],status=q['status'],lmr=q['lmr'],seconds=q['search_seconds']),flush=True)
    complete=len(quals)==8 and all(q['status']=='RETURNED' for q in quals)
    active={q['family'] for q in quals if q['lmr'].get('reductions',0)>0}
    ratio=sum(q['search_seconds'] for q in quals)/sum(q['reused_reference_search_seconds'] for q in quals) if complete else None
    qualified=complete and len(active)>=4 and ratio<=1.10
    write_record(out/'qualification.json',dict(queries=quals,new_candidate_queries=len(quals),reused_reference_slots=16,complete=complete,active_families=sorted(active),candidate_reference_wall_ratio=ratio,gate=qualified,caveat='Historical same-build brackets;not interleaved newcandidate control. Feasibility only,not a speedup/strength claim.'))
    if not qualified:halt=halt or 'qualification_NO_GO'
    games=[];gtick=time.perf_counter();qid=0
    for row in rows:
        for on_seat in ((0,1) if row['family']%2==0 else (1,0)):
            g=dict(game_id=len(games),case_id=row['id'],family=row['family'],fingerprint=row['fingerprint'],on_seat=on_seat,initial_record=row['record'],status='NOT_STARTED',queries=[])
            remaining=(datetime.fromisoformat(plan['whole_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()
            if remaining<180+480 or time.perf_counter()-gtick+180>2700 or stopped():halt=halt or 'whole_or_batch_dispatch_reserve_or_stop'
            if not halt:
                begin=stamp();t=time.perf_counter()
                try:
                    c,s=make_session(row);players={};owners={};g.update(status='RUNNING',started_at=begin)
                    while not s.state.terminal_status.is_terminal:
                        if stopped() or time.perf_counter()-t>=180 or time.perf_counter()-gtick>=2700:
                            halt='scoped_stop_or_game_batch_cap';break
                        if (datetime.fromisoformat(plan['whole_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()<482:
                            halt='whole_delivery_reserve';break
                        seat=s.state.position.side_to_move;query=choose(c,s,players,owners,seat,seat==on_seat,f'g{qid:04d}',out);qid+=1;g['queries'].append(query)
                        write_record(out/f"game-{g['game_id']:02d}-queries.json",g['queries']);write_json(out/'progress.json',dict(at=stamp(),completed_games=len(games),active_game=g['game_id'],family=row['family'],turns=len(g['queries']),returns=qid))
                    g.update(status='TERMINAL' if s.state.terminal_status.is_terminal else 'UNFINISHED',final_record=record_value(s.to_record()),Core_terminal=record_value(s.state.terminal_status),Session_result=record_value(s.result),ended_at=stamp(),outer_seconds=time.perf_counter()-t,timing_eligible=all(q['timing_eligible'] for q in g['queries']))
                except Exception as e:g.update(status='FAILED',error_type=type(e).__name__,error=str(e));halt='game_or_validation_failure'
            g['reason']=halt;games.append(g);write_record(out/f"game-{g['game_id']:02d}.json",g);write_record(out/'games.json',games);print({k:g[k] for k in ('game_id','family','status','reason')},flush=True)
    summary=dict(ended_at=stamp(),game_statuses=dict(Counter(g['status'] for g in games)),qualification=qualified,halt=halt,new_candidate_qualifiers=len(quals),new_game_Player_returns=qid,outcome=endpoints(games),product_default_changed=False,builds=0)
    write_record(out/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.plan,a.output)
