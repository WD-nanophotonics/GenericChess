"""Actual-history noWIN-filter qualification, no changed training or Native calls."""
from pathlib import Path
from collections import Counter,defaultdict
from copy import copy
from dataclasses import replace
import json,hashlib,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.generic_inventory_proof_transport import SetupTransportedNoWinFilter
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.generic_win_proof import _same_state
OUT=Path('results/dev_aux/task2046')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def lines(p):return[json.loads(x)for x in Path(p).read_text(encoding='utf-8').splitlines()]
def main():
 start=time.perf_counter();p=read('results/dev_aux/task2020/run-plan.json');c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text(encoding='utf-8')));roots=read(p['roots'])['roots'];steps=defaultdict(list)
 for step in lines(Path('results/dev_aux/task2020/moves.jsonl')):steps[step['slot']].append(step)
 f=SetupTransportedNoWinFilter('results/dev_aux/task2044','results/dev_aux/task2045/coverage.json',c);samples=[];seen=set();positive=None
 for game in lines(Path('results/dev_aux/task2020/games.jsonl')):
  session=GameSession(c,roots[game['family']]['setup'])
  for step in steps[game['slot']]:
   pattern=tuple(sorted(Counter((x.owner,x.current_type_id)for x in session.state.position.board if x is not None).items()))
   if f.eligible(session) and pattern not in seen:
    seen.add(pattern);before=session.to_record();state=session.state;result=session.result;r=f(session,max_nodes=1024,seconds=1.5,max_depth=64)
    assert r.status=='UNKNOWN' and r.reason=='certified_inventory_no_win' and r.nodes==0 and r.certificate is None
    assert session.to_record()==before and _same_state(session.state,state) and session.result==result
    clone=GameSession.replay(replace(c),before);assert not f.eligible(clone)
    samples.append(dict(slot=game['slot'],ply=step['ply'],pattern=pattern,record=json.loads(serialize_game_record(before)),status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,state_unchanged=True,foreign_compiled_identity_rejected=True))
   piece_counts=Counter(x.current_type_id for x in session.state.position.board if x is not None)
   if positive is None and step['source']=='PROOF'and piece_counts==Counter(K=2,R=1):
    before=session.to_record();assert not f.eligible(session);r=f(session,max_nodes=1024,seconds=1.5,max_depth=64);verification=verify_session_certificate(session,r.certificate,max_nodes=16384,seconds=.5)if r.certificate else None
    assert session.to_record()==before and r.status=='PROVEN_WIN' and verification['verified']
    positive=dict(slot=game['slot'],ply=step['ply'],status=r.status,nodes=r.nodes,rank=r.certificate.tree.rank,verification=verification,record=json.loads(serialize_game_record(before)),certificate_sha=hashlib.sha256(repr(r.certificate).encode()).hexdigest())
   encoded=dict(schema_version=1,ruleset_fingerprint=c.ruleset_fingerprint,actions=[step['choice']],resigned_by=None);session.submit(deserialize_game_record(json.dumps(encoded)).actions[0])
 assert samples and positive is not None
 six=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2024/rules.json').read_text(encoding='utf-8')))
 try:SetupTransportedNoWinFilter('results/dev_aux/task2044','results/dev_aux/task2045/coverage.json',six)
 except ValueError as exc:rejected=str(exc)
 else:raise AssertionError('unsafe6board transfer accepted')
 result=dict(status='PASS_ACTUAL_HISTORY_UNKNOWN_ONLY_AND_ROOK_PROOF_FALLBACK',samples=samples,positive_control=positive,sixboard_rejection=rejected,seconds=time.perf_counter()-start,new_Native_calls=0,new_PN_calls=1,current2037_policy_changed=False,scope='Existing production generic data-driven filter, fresh census under actual extra-B law, setup-only exact field transport to old actual records. UNKNOWN only/no syntheticdraw/action/reward. Positive fallback is actual full-history provenWIN, not universal alwaysprogress or6board support. No speedup/equivalence claim until a separate prospective study.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(status=result['status'],patterns=len(samples),positive=positive,rejected=rejected,seconds=result['seconds'])))
if __name__=='__main__':main()
