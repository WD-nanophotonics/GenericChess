"""Paid-path cost probe of exact-history partial proof retention, not WDL."""
import json,random,time
from pathlib import Path
from dataclasses import asdict
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor,uci,actor_state
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from scripts.generic_win_proof_pn import prove_win_pn
from scripts.generic_win_proof_retained import PartialProofStore,prove_win_retained
from scripts.generic_win_proof import verify_certificate,PROVEN_WIN
from scripts.generic_proof_native_study import sha,mod


def freeze(folder):
    out=Path(folder);out.mkdir(exist_ok=False)
    p=Path('results/dev_aux/task1773');rows=[json.loads(x) for x in (p/'run/games.jsonl').read_text().splitlines()]
    c=compile_rnb();fs={f['family']:f for f in json.loads((p/'plan.json').read_text())['families']};cases=[];seen=set()
    for i,row in enumerate(rows):
        if row['proof']:continue
        s=from_actor(c,fs[row['family']]['roots'][row['color']])
        for ply,z in enumerate(row['trajectory']):
            if ply+2<=len(row['trajectory']) and repr(s) not in seen:
                cases.append(dict(row=i,ply=ply));seen.add(repr(s))
            action=next(a for a in legal_actions(s,c) if uci(a)==z['decision']['action']);s=apply_action(s,action,c)
    rng=random.Random(20261015554);rng.shuffle(cases);cases=cases[:64];assert len(cases)==64
    plan=dict(status='FROZEN_BEFORE_RETENTION_TIMINGS',source='results/dev_aux/task1773',games_sha256=sha(p/'run/games.jsonl'),cases=cases,seed=20261015554,nodes=1024,seconds=.25,max_depth=32,total_seconds=180,max_entries=16,purpose='Price/WDL-blind unique paid plain-player states and their ACTUAL next two moves. Never choose a future state because cache contains it. No new Nativego or closed-loop WDL claim.',accounting='Counterbalance cold/retained parent search, measure all collection preparation. Reuse requires root UNKNOWN, exact full-history child hit and independent verification in next call budget. Also cold-probe ALL actual child states for comparison.',retained_sha256=sha('scripts/generic_win_proof_retained.py'),pn_sha256=sha('scripts/generic_win_proof_pn.py'))
    (out/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print('FROZEN64')


def run(folder):
    out=Path(folder);plan=json.loads((out/'plan.json').read_text());assert sha('scripts/generic_win_proof_retained.py')==plan['retained_sha256'] and sha('scripts/generic_win_proof_pn.py')==plan['pn_sha256']
    p=Path(plan['source']);assert sha(p/'run/games.jsonl')==plan['games_sha256']
    rows=[json.loads(x) for x in (p/'run/games.jsonl').read_text().splitlines()];fs={f['family']:f for f in json.loads((p/'plan.json').read_text())['families']};c=compile_rnb();start=time.perf_counter();deadline=start+plan['total_seconds'];records=[];error=None;flags=mod('RETENTION_STOP55','results/dev_aux/task166/run.py')
    def stop():return time.perf_counter()>=deadline
    try:
        with (out/'calls.jsonl').open('x',encoding='utf-8') as log:
            for i,case in enumerate(plan['cases']):
                flags.stop()
                if stop():raise RuntimeError('wallcap')
                row=rows[case['row']];s=from_actor(c,fs[row['family']]['roots'][row['color']]);states=[]
                for ply,z in enumerate(row['trajectory']):
                    if ply==case['ply']:parent=s
                    a=next(a for a in legal_actions(s,c) if uci(a)==z['decision']['action']);s=apply_action(s,a,c)
                    if ply+1==case['ply']+2:child=s;break
                target=parent.position.side_to_move;store=PartialProofStore(plan['max_entries']);answers={}
                for kind in (['COLD','RETAIN'] if i%2==0 else ['RETAIN','COLD']):
                    args=dict(target=target,max_nodes=plan['nodes'],seconds=plan['seconds'],max_depth=plan['max_depth'],cancel=stop)
                    result=prove_win_pn(c,parent,**args) if kind=='COLD' else prove_win_retained(c,parent,store=store,**args)
                    assert result.pushes==result.pops and result.nodes<=plan['nodes']
                    if result.certificate:assert verify_certificate(c,parent,result.certificate,seconds=.25)['verified']
                    answers[kind]=dict(status=result.status,nodes=result.nodes,seconds=result.seconds,reason=result.reason)
                entries=len(store.certificates);cert=store.take(c,child,target) if answers['RETAIN']['status']!='PROVEN_WIN' else None
                verification=verify_certificate(c,child,cert,max_nodes=plan['nodes'],seconds=plan['seconds'],cancel=stop) if cert else None
                if verification:assert verification['verified']
                result=prove_win_pn(c,child,target=target,max_nodes=plan['nodes'],seconds=plan['seconds'],max_depth=plan['max_depth'],cancel=stop)
                if result.certificate:assert verify_certificate(c,child,result.certificate,seconds=.25)['verified']
                record=dict(**case,parent=answers,stored_entries=entries,eligible_actual_path_hit=cert is not None,reuse_verification=verification,cold_child=dict(status=result.status,nodes=result.nodes,seconds=result.seconds),no_new_native_go=True)
                records.append(record);log.write(json.dumps(record)+'\n');log.flush()
    except BaseException as e:error=type(e).__name__+':'+str(e)
    result=dict(status='COMPLETE' if error is None else 'PARTIAL',error=error,cases=len(records),actual_new_native_go=0,seconds=time.perf_counter()-start,
                parent_seconds={k:sum(r['parent'][k]['seconds'] for r in records) for k in ('COLD','RETAIN')},parent_proofs={k:sum(r['parent'][k]['status']==PROVEN_WIN for r in records) for k in ('COLD','RETAIN')},
                stored_entries=sum(r['stored_entries'] for r in records),actual_path_hits=sum(r['eligible_actual_path_hit'] for r in records),
                hit_cold_child_seconds=sum(r['cold_child']['seconds'] for r in records if r['eligible_actual_path_hit']),hit_verify_seconds=sum(r['reuse_verification']['seconds'] for r in records if r['reuse_verification']),
                scope='Observed paid paths only; preparation included. No live policy or end-to-end strength claim.')
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result)


if __name__=='__main__':
    import sys;(freeze if sys.argv[1]=='freeze' else run)(sys.argv[2])
