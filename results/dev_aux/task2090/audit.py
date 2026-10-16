"""Independent public Session consumer of the frozen2088 journal/certificates."""
from pathlib import Path
from collections import Counter
from copy import copy
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionWinCertificate,SessionStrategyCursor,verify_session_certificate
from scripts.generic_proof_rnb_bridge import actor_state
from results.dev_aux.task2048.portable_certificate import decode
from results.dev_aux.task2068.teacher import CanonicalTeacher
OUT=Path('results/dev_aux/task2090')
def main():
    start=time.perf_counter();rows=[json.loads(x)for x in Path('results/dev_aux/task2088/queries.jsonl').read_text(encoding='utf-8').splitlines()];certs=json.loads(Path('results/dev_aux/task2088/certificates.json').read_text(encoding='utf-8'));teacher=CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2073','results/dev_aux/task2074');roots=json.loads(Path('results/dev_aux/task2087/inputs.json').read_text(encoding='utf-8'))['roots']
    assert len(rows)==192 and len({(r['family'],r['snapshot'],r['target'],r['provider']) for r in rows})==192
    sessions={}
    for root in roots:
        c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text(encoding='utf-8')));s=GameSession(c);snapshots=[copy(s)]
        for _ in range(2):
            if s.result.status is SessionStatus.ONGOING:s.submit(s.legal_actions()[0])
        snapshots.append(s)
        for k,v in enumerate(snapshots):sessions[root['family'],k]=v
    misses=0;negative=0
    for r in rows:
        s=sessions[r['family'],r['snapshot']];assert s.to_record()==deserialize_game_record(json.dumps(r['root_record']))
        assert r['nodes']<=1024 and r['seconds']<1.6
        if r['status']=='PROVEN_WIN':assert r['verified']['verified']
        if r['reason']=='certified_complete_graph_no_win':
            v={'WIN':1,'DRAW':0,'LOSS':-1}[teacher.rows[teacher.key(actor_state(s.state))]['label']];v=v if r['target']==s.state.position.side_to_move else-v
            assert v<=0 and r['status']=='UNKNOWN' and r['nodes']==0;negative+=1
    moves=0;rejections=0;compositions=Counter();wins=Counter()
    for entry in certs:
        r=rows[entry['query']];s=copy(sessions[r['family'],r['snapshot']]);cert=SessionWinCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,entry['target'],decode(entry['tree'],s.compiled.ruleset_fingerprint));cursor=SessionStrategyCursor(s,cert,max_nodes=16384,seconds=.5);compositions[r['composition']]+=1
        initial=cursor.node.rank
        while s.result.status is SessionStatus.ONGOING:
            choice=cursor.choose(s)if s.state.position.side_to_move==entry['target']else max(cursor.node.edges,key=lambda e:e[1].rank)[0]
            rank=cursor.node.rank;cursor.commit(s,choice);assert cursor.node.rank<rank
            replay=GameSession.replay(s.compiled,s.to_record());assert replay.state==s.state and replay.result==s.result;moves+=1
        assert s.result.winner==entry['target'];wins[s.result.status.value]+=1
    paired=[]
    for family in range(24):
        for snap in range(2):
            for target in(0,1):
                pair={r['provider']:r for r in rows if(r['family'],r['snapshot'],r['target'])==(family,snap,target)}
                a,b=pair['reference'],pair['composite'];paired.append((a['status'],b['status']))
    output=dict(status='PASS_FIXED_QUERY_REPLAY_AND_PHYSICAL_STRATEGY',queries=len(rows),negative_UNKNOWN_checked=negative,positive_certificates=len(certs),actual_checkmates=dict(wins),actual_cursor_moves=moves,certificates_by_composition=dict(compositions),paired_status={a+' -> '+b:n for(a,b),n in Counter(paired).items()},seconds=time.perf_counter()-start,scope='IndependentexistingSessionverifier/cursor, longest-rankdefenses, all-defensecertificateverification. Qualification notactualmodelbenefit; graphlabels onlycheckednegative-scheduling sign. Existingprecomputedteachersnotnewscientificindependence.')
    (OUT/'result.json').write_text(json.dumps(output,indent=2),encoding='utf-8');print(json.dumps(output))
if __name__=='__main__':main()
