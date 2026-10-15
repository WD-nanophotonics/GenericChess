"""New diagnostic of FOUR saved censored DEV endpoints; not policy continuation.

Old H16 outcomes/selection remain immutable. Proving off-policy wins here does
not award those wins to either old policy. No engine, training or new roots.
"""
from pathlib import Path
import hashlib,json,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof_pn import prove_session_win_pn
from scripts.generic_session_win_proof import SessionStrategyCursor
from scripts.generic_session_certificate_json import export_session_certificate
OUT=Path('results/dev_aux/task1827')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,obj):
    with (OUT/name).open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2)
def freeze():
    p=Path('results/dev_aux/task1825/games.jsonl');rows=[json.loads(x) for x in p.read_text().splitlines()]
    ix={(x['family'],x['candidate_side'],x['R']):x for x in rows if x['phase']=='DEV' and x['candidate_proof']};cases=[]
    for key,row in ix.items():
        if row['R'] not in (720,1440) or row['outcome']!='UNKNOWN':continue
        other=ix[(row['family'],row['candidate_side'],1440 if row['R']==720 else 720)]
        if other['outcome']==row['outcome']:continue
        cases.append(dict(slot=row['slot'],family=row['family'],candidate_side=row['candidate_side'],R=row['R'],old_outcome=row['outcome'],paired_outcome=other['outcome'],record=row['record'],final_state_sha=row['final_state_sha']))
    assert len(cases)==4
    sources=[__file__,'scripts/generic_session_win_proof.py','scripts/generic_session_win_proof_pn.py','scripts/generic_session_certificate_json.py']
    write('plan.json',dict(question='Are the four actual censored endpoints responsible for nonidentical Native price-pair outcomes provably winning at a larger fixed diagnostic budget? This cannot relabel oldpolicy WDL or select newprices.',cases=cases,parent=str(p),parent_sha=sha(p),
        budgets=[dict(nodes=1024,seconds=.0625),dict(nodes=65536,seconds=1.),dict(nodes=65536,seconds=5.)],targets=[0,1],max_depth=64,verification_nodes=262144,verification_seconds=3.,seconds_cap=180,
        source_sha={str(p):sha(p) for p in sources},rules='results/dev_aux/task1822/rules.json',rules_sha=sha('results/dev_aux/task1822/rules.json'),
        nodes='SessionPN newly inspected nodes, not equivalent primitive work',scope='Exposed outcome-selected failure diagnosis only; no new Nativego or oldcap/H extension, no arbitrary fresh root/history reset.'))
    print('FROZEN_FOUR_CENSORED_ENDPOINT_DIAGNOSTIC')
def run():
    p=json.loads((OUT/'plan.json').read_text());assert all(sha(f)==h for f,h in p['source_sha'].items());c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text()));rows=[];start=time.perf_counter()
    with (OUT/'calls.jsonl').open('x',encoding='utf-8') as log:
        for case in p['cases']:
            for budget in p['budgets']:
                for target in p['targets']:
                    if time.perf_counter()-start>=p['seconds_cap']:break
                    s=GameSession.replay(c,deserialize_game_record(json.dumps(case['record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==case['final_state_sha']
                    result=prove_session_win_pn(s,target=target,max_nodes=budget['nodes'],seconds=budget['seconds'],max_depth=p['max_depth'],cancel=lambda:time.perf_counter()-start>=p['seconds_cap'])
                    row=dict(slot=case['slot'],target=target,budget=budget,status=result.status,reason=result.reason,nodes=result.nodes,seconds=result.seconds,rank=None,verification=None,physical=None)
                    if result.certificate is not None:
                        cursor=SessionStrategyCursor(s,result.certificate,max_nodes=p['verification_nodes'],seconds=p['verification_seconds']);row['verification']=cursor.receipt;row['rank']=cursor.node.rank
                        data=export_session_certificate(s,result.certificate);name=f"witness-{case['slot']}-{target}-{budget['nodes']}-{budget['seconds']}.json";write(name,data);row['witness']=name
                        steps=0
                        while s.result.status is SessionStatus.ONGOING:
                            choice=cursor.choose(s) if s.state.position.side_to_move==target else cursor.node.edges[0][0]
                            cursor.commit(s,choice);steps+=1
                        assert s.result.winner==target and steps<=row['rank'];row['physical']=dict(steps=steps,status=s.result.status.value,winner=s.result.winner)
                    rows.append(row);log.write(json.dumps(row)+'\n');log.flush();print(json.dumps(row),flush=True)
    write('result.json',dict(status='COMPLETE' if len(rows)==24 else 'PARTIAL_CAP_PRESERVED',calls=len(rows),seconds=time.perf_counter()-start,proven=sum(x['status']=='PROVEN_WIN' for x in rows),actual_native_go=0,old_rewards_unchanged=True))
if __name__=='__main__':
    import sys
    {'freeze':freeze,'run':run}[sys.argv[1]]()
