"""Independent fixed-opponent candidate-only full-player scheduling audit."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,statistics,random
from results.dev_aux.task2051.physical_audit import audit,read,lines
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_inventory_proof_transport import SetupTransportedNoWinFilter
from scripts.generic_proof_rnb_bridge import orbit
P=Path('results/dev_aux/task2050');OUT=Path('results/dev_aux/task2051')
def main():
 plan=read(P/'run-plan.json');done=read(P/'completion.json');games=lines(P/'games.jsonl');moves=lines(P/'moves.jsonl');physical=audit(P)
 assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in plan['source_sha'].items())
 assert len(plan['slots'])==32 and len(read(P/'qualification.json')['perfts'])==8
 assert all(g['opponent_R']==1260 and g['opponent_B']==g['B']==g['N']==720 for g in games)
 assert all(all(g[k]==v for k,v in slot.items()) for slot,g in zip(plan['slots'],games))
 by=defaultdict(list)
 for step in moves:by[step['slot']].append(step)
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text(encoding='utf-8')));roots=read(plan['roots'])['roots'];filtered=SetupTransportedNoWinFilter('results/dev_aux/task2044','results/dev_aux/task2045/coverage.json',c);hits=0
 old=set()
 for r in read('results/dev_aux/task2036/feasibility.json')['roots']:old.update(orbit(tuple(r['root'])))
 assert all(tuple(r['root'])not in old for r in roots)
 for g in games:
  session=GameSession(c,roots[g['family']]['setup'])
  for step in by[g['slot']]:
   skipped=step['logical_reason']=='certified_inventory_no_win'
   if skipped:
    assert g['candidate_filter']and step['side']==g['candidate_side']and filtered.eligible(session)and step['proof_nodes']==0;hits+=1
   elif not g['candidate_filter']or step['side']!=g['candidate_side']:assert step['proof_reason']!='certified_inventory_no_win'
   encoded=dict(schema_version=1,ruleset_fingerprint=c.ruleset_fingerprint,actions=[step['choice']],resigned_by=None);session.submit(deserialize_game_record(json.dumps(encoded)).actions[0])
 result=dict(status='PASS_COMPLETE_FIXED_OPPONENT_COST_CONTROL'if done['status']=='COMPLETE'else'PARTIAL_CONTROL_RETAINED',physical=physical,filter_hits=hits,original_planned=32,observed=len(games),unrun=[g['slot']for g in plan['slots'][len(games):]],scope='Candidate-only intervention, originalopponent fixed. Descriptive cost/work and observed behavior only; no equivalence margin/universalWDLpreservation/strength claim. Actual max96 rule draw, UNKNOWN unscored. No newNative/PN duringaudit; no current2037policychange.')
 if done['status']=='COMPLETE':
  assert len(games)==32 and all(g['outcome']!='UNKNOWN'for g in games)
  cells={(g['family'],g['candidate_side'],g['candidate_filter']):g for g in games};families=[];changes=[]
  for f in range(8):
   delta=[]
   for side in (0,1):
    a,b=cells[f,side,False],cells[f,side,True];same=a['record']['actions']==b['record']['actions'];prefix=0
    for aa,bb in zip(by[a['slot']],by[b['slot']]):
     if aa['choice']!=bb['choice']:break
     prefix+=1
    first_actor=None
    if prefix<min(a['moves'],b['moves']):
     assert by[a['slot']][prefix]['before_state_sha']==by[b['slot']][prefix]['before_state_sha'];first_actor='CANDIDATE'if by[a['slot']][prefix]['side']==side else'OPPONENT'
    changes.append(dict(family=f,side=side,identical_actions=same,outcomes=[a['outcome'],b['outcome']],common_prefix=prefix,first_fork_actor=first_actor))
    delta.append(b['seconds']-a['seconds'])
   families.append(dict(family=f,seconds_delta=statistics.mean(delta)))
  rng=random.Random(20261016692051);bs=sorted(statistics.mean(rng.choices([x['seconds_delta']for x in families],k=8))for _ in range(10000))
  arms={}
  for flag in (False,True):
   gs=[g for g in games if g['candidate_filter']==flag];ms=[m for g in gs for m in by[g['slot']]];own=[m for g in gs for m in by[g['slot']]if m['side']==g['candidate_side']]
   arms[str(flag)]=dict(games=len(gs),outcomes=dict(Counter(g['outcome']for g in gs)),game_seconds=sum(g['seconds']for g in gs),moves=len(ms),candidate_PN_seconds=sum(m['proof_seconds']for m in own),candidate_PN_nodes=sum(m['proof_nodes']for m in own),total_PN_seconds=sum(m['proof_seconds']for m in ms),normal_nodes=sum(m['search_nodes']for m in ms))
  result.update(arms=arms,paired_trajectories=changes,family_runtime_deltas=families,mean_seconds_delta=statistics.mean(x['seconds_delta']for x in families),exploratory8family_interval=[bs[249],bs[9749]],same_trajectory_pairs=sum(x['identical_actions']for x in changes),same_outcome_pairs=sum(x['outcomes'][0]==x['outcomes'][1]for x in changes),campaign_non_game_overhead_seconds=done['seconds']-sum(g['seconds']for g in games))
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k not in ('physical','paired_trajectories','family_runtime_deltas')}))
if __name__=='__main__':main()
