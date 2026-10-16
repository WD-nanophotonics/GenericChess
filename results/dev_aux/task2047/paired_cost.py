"""Predeclared bounded paired proof-scheduling microcost on actual exposed records."""
from pathlib import Path
from collections import Counter,defaultdict
import json,time,statistics,datetime
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.generic_inventory_proof_transport import SetupTransportedNoWinFilter
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
OUT=Path('results/dev_aux/task2047')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def lines(p):return[json.loads(x)for x in Path(p).read_text(encoding='utf-8').splitlines()]
def main():
 start=time.perf_counter();plan=dict(status='FROZEN_BEFORE_COST_RUN',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source='Existing exposed2020actual publicrecords; first4eligibleprefixes per exact owner/type pattern, chronologicalslot/ply, <=20cases',order='PNfirst evenordinal,filterfirst oddordinal, same unchanged actual fullhistory/target, no shared bank',PN_nodes=1024,PN_seconds=1.5,depth=64,whole_cap_seconds=60,expected_seconds=6,decision='Can actual PN saving cover filter construction+publicreplay? Descriptive runtime/work, ordinary concurrent Native activity; not equal-clock WDL equivalence/newvalidation. No current2037 policychange/Nativecalls.')
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
 p=read('results/dev_aux/task2020/run-plan.json');c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text(encoding='utf-8')));roots=read(p['roots'])['roots'];steps=defaultdict(list)
 for step in lines(Path('results/dev_aux/task2020/moves.jsonl')):steps[step['slot']].append(step)
 t=time.perf_counter();f=SetupTransportedNoWinFilter('results/dev_aux/task2044','results/dev_aux/task2045/coverage.json',c);construction=time.perf_counter()-t;seen=Counter();samples=[];status='COMPLETE'
 for game in lines(Path('results/dev_aux/task2020/games.jsonl')):
  session=GameSession(c,roots[game['family']]['setup'])
  for step in steps[game['slot']]:
   pattern=tuple(sorted(Counter((x.owner,x.current_type_id)for x in session.state.position.board if x is not None).items()))
   if f.eligible(session)and seen[pattern]<4 and len(samples)<20:
    if time.perf_counter()-start>=60:status='CAP';break
    seen[pattern]+=1;before=session.to_record();measure={};ordinal=len(samples)
    for label in (('PN','FILTER')if ordinal%2==0 else('FILTER','PN')):
     t=time.perf_counter();r=(prove_session_win_batch_pn if label=='PN'else f)(session,max_nodes=1024,seconds=1.5,max_depth=64,cancel=lambda:time.perf_counter()-start>=60);elapsed=time.perf_counter()-t
     assert r.status=='UNKNOWN'and r.certificate is None and session.to_record()==before
     measure[label]=dict(seconds=elapsed,nodes=r.nodes,reason=r.reason)
    assert measure['FILTER']['nodes']==0 and measure['FILTER']['reason']=='certified_inventory_no_win'
    samples.append(dict(ordinal=ordinal,slot=game['slot'],ply=step['ply'],pattern=pattern,record=json.loads(serialize_game_record(before)),measurement=measure))
   encoded=dict(schema_version=1,ruleset_fingerprint=c.ruleset_fingerprint,actions=[step['choice']],resigned_by=None);session.submit(deserialize_game_record(json.dumps(encoded)).actions[0])
  if status!='COMPLETE':break
 assert samples
 pn=sum(x['measurement']['PN']['seconds']for x in samples);filtered=sum(x['measurement']['FILTER']['seconds']for x in samples);gain=pn-filtered
 result=dict(status=status,cases=len(samples),patterns=len(seen),samples=samples,construction_seconds=construction,PN_seconds=pn,filtered_seconds=filtered,net_seconds_after_construction=gain-construction,PN_nodes=sum(x['measurement']['PN']['nodes']for x in samples),filter_nodes=0,estimated_calls_to_amortize=construction/(gain/len(samples))if gain>0 else None,seconds=time.perf_counter()-start,scope=plan['decision'])
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k!='samples'}))
if __name__=='__main__':main()
