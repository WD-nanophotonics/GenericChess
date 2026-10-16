"""Independent actual-record, role/dedup, budget and causal-condition audit."""
from pathlib import Path
from collections import Counter,defaultdict
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_win_proof import _same_state
from scripts.generic_session_win_proof import SessionWinCertificate,verify_session_certificate
from results.dev_aux.task2048.portable_certificate import decode
OUT=Path('results/dev_aux/task2135')
def audit(task):
 start=time.perf_counter();root=Path(f'results/dev_aux/task{task}');p=json.loads((root/'plan.json').read_text());completion=json.loads((root/'completion.json').read_text());started=json.loads((root/'started.json').read_text());assert hashlib.sha256((root/'learn.py').read_bytes()).hexdigest()==started['source_sha'];inputs=json.loads((root/'inputs.json').read_text())['roots'];families=range(48);policies=['TRIGGER'];opponent='TRIGGER';cap=p['one_game_cap_seconds'];actor=RoyalActor(3)
 games=[json.loads(x)for x in(root/'games.jsonl').read_text().splitlines()];by=defaultdict(list)
 for line in(root/'moves.jsonl').read_text().splitlines():
  r=json.loads(line);by[r['physical_id']].append(r)
 lockpath=root/'selector-lock.json';lock=json.loads(lockpath.read_text())if lockpath.exists()else None;expected=[]
 for family in range(32):
  for role in(0,1):
   off=(family+role)%7;prices=p['ratios'][off:]+p['ratios'][:off];expected.extend((family,role,r,'TRIGGER')for r in prices)
 if lock is not None:
  for family in range(32,48):
   for role in(0,1):
    off=(family+role)%len(lock['prices']);prices=lock['prices'][off:]+lock['prices'][:off];expected.extend((family,role,r,'TRIGGER')for r in prices)
 assert len(games)<=len(expected)
 compiled={};physical={};counts=Counter();costs=defaultdict(Counter);choicepoints={};proofsteps=set();records={}
 for i,g in enumerate(games):
  assert g['logical_slot']==i and(g['family'],g['candidate_side'],g['ratio'],g['candidate_policy'])==expected[i]and g['opponent_ratio']==1. and g['opponent_policy']==opponent
  if g['reused_from']is not None:
   prev=games[g['reused_from']];assert prev['reused_from']is None and prev['ratio']==g['ratio']==1. and prev['candidate_policy']==g['candidate_policy']and prev['family']==g['family']and prev['physical_id']==g['physical_id']and prev['record']==g['record']and prev['candidate_side']!=g['candidate_side'];assert g['score']==(None if prev['score']is None else-prev['score']);counts['explicit_identity_role_reuses']+=1;continue
  assert g['physical_id']not in physical;physical[g['physical_id']]=g;family=g['family']
  if family not in compiled:compiled[family]=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[family]['rules']).read_text(encoding='utf-8')))
  c=compiled[family];s=GameSession(c);rec=deserialize_game_record(json.dumps(g['record']));ms=by[g['physical_id']];assert len(ms)==len(rec.actions)==g['moves'];entered=False
  for ply,(m,a)in enumerate(zip(ms,rec.actions)):
   assert s.result.status is SessionStatus.ONGOING and m['logical_slot']==i and m['ply']==ply and m['side']==s.state.position.side_to_move and m['is_candidate']==(m['side']==g['candidate_side']);assert hashlib.sha256(repr(s.state).encode()).hexdigest()==m['before_state_sha']
   assert m['choice']==action_to_dict(a);literal=dict(actor.moves(actor_state(s.state)));legal={uci(x):x for x in s.legal_actions()};assert set(literal)==set(legal)and uci(a)in legal
   assert m['proof_nodes']<=p['proof_nodes']and m['search_nodes']<=p['normal_nodes']and m['verification_nodes']<=p['verification_nodes']and m['fill_verification_nodes']<=p['verification_nodes'];lim=m['phase_limits'];assert lim['normal_nodes']==p['normal_nodes']and lim['normal_seconds']==p['normal_seconds']and lim['proof_nodes']==p['proof_nodes']and lim['proof_seconds']==p['proof_seconds']
   if task==2120 and m['proof_reason']=='certified_complete_graph_no_win':assert m['is_candidate']and g['candidate_policy']=='NEGATIVE_FILTER'and m['logical_status']=='UNKNOWN'and m['proof_nodes']==0
   if m['source']=='PROOF':assert m['logical_status']=='PROVEN_WIN'and m['verification_nodes']>0 and m['fill_verification_nodes']>0;proofsteps.add((g['physical_id'],ply));records[g['physical_id'],ply]=s.to_record()
   role='candidate'if m['is_candidate']else'opponent';group=g['candidate_policy']+'_'+str(g['ratio'])+'_'+role;cost=costs[group];cost['decisions']+=1
   for k in('proof_nodes','search_nodes','proof_seconds','normal_seconds','seconds'):cost[k]+=m[k]
   counts['depth_'+str(m['completed_depth'])]+=1;counts['source_'+m['source']]+=1;s.submit(a);assert actor_state(s.state)==literal[uci(a)]and hashlib.sha256(repr(s.state).encode()).hexdigest()==m['after_state_sha']and dict(status=s.result.status.value,winner=s.result.winner)==m['result'];counts['moves']+=1
   entered|=sum(x is not None for x in s.state.position.board)<=4
  counts['physical_entered_at_most4']+=entered;counts['physical_never_entered']+=not entered;replay=GameSession.replay(c,rec);assert _same_state(replay.state,s.state)and replay.result==s.result and hashlib.sha256(repr(s.state).encode()).hexdigest()==g['final_state_sha'];outcome='UNKNOWN'if s.result.status is SessionStatus.ONGOING else'DRAW'if s.result.winner is None else'WIN'if s.result.winner==g['candidate_side']else'LOSS';assert outcome==g['outcome']and g['score']==(None if outcome=='UNKNOWN'else 1 if outcome=='WIN'else-1 if outcome=='LOSS'else 0);counts['physical_'+outcome]+=1
 assert len(physical)==completion['physical_games']and len(games)==completion['logical_games']and counts['moves']==completion['moves'];certreceipts=[]
 if task==2134:
  certs=[json.loads(x)for x in(root/'certificates.jsonl').read_text().splitlines()];assert {(r['physical_id'],r['ply'])for r in certs}==proofsteps
  for r in certs:
   g=physical[r['physical_id']];c=compiled[g['family']];rec=deserialize_game_record(json.dumps(r['root_record']));assert _same_state(rec,records[r['physical_id'],r['ply']]);s=GameSession.replay(c,rec);cert=SessionWinCertificate(c.ruleset_fingerprint,s.to_record(),s.state,r['target'],decode(r['tree'],c.ruleset_fingerprint));vr=verify_session_certificate(s,cert,max_nodes=65536,seconds=2.);assert vr['verified'];certreceipts.append(vr)
 train=[g for g in games if g['phase']=='TRAIN'];assert all(g['phase']==('TRAIN'if i<448 else'DEV')for i,g in enumerate(games))
 def independent_select(initial):
  means={r:sum(g['score']for g in train if g['ratio']==r)/sum(g['ratio']==r for g in train)for r in p['ratios']};at=p['ratios'].index(initial);trace=[initial]
  for _ in range(7):
   nxt=next((j for j in(at-1,at+1)if 0<=j<7 and means[p['ratios'][j]]>means[p['ratios'][at]]),None)
   if nxt is None:break
   at=nxt;trace.append(p['ratios'][at])
  return dict(initial=initial,selected=p['ratios'][at],trace=trace,TRAIN_means={str(k):v for k,v in means.items()})
 paired={}
 if lock is not None:
  assert len(train)==448 and all(g['score']is not None for g in train);raw=(root/'games.jsonl').read_bytes();assert hashlib.sha256(b''.join(raw.splitlines(keepends=True)[:448])).hexdigest()==lock['source_TRAIN_games_sha'];assert [independent_select(r)for r in p['initial_ratio']]==lock['selected']==completion['selected'];assert lock['prices']==sorted({1.}|{x['selected']for x in lock['selected']})
  for price in sorted({r['selected']for r in lock['selected']}):
   dd=[]
   for family in range(32,48):
    rr=[g for g in games if g['phase']=='DEV'and g['family']==family and g['ratio']in(1.,price)]
    if len(rr)==(2 if price==1. else 4)and all(g['score']is not None for g in rr):dd.append(dict(family=family,price_gain=sum(g['score']for g in rr if g['ratio']==price)/2-sum(g['score']for g in rr if g['ratio']==1.)/2))
   paired[str(price)]=dd
 interaction=[]
 if task==2120:
  for family in families:
   rr=[g for g in games if g['family']==family]
   if len(rr)==8 and all(g['score']is not None for g in rr):
    interaction.append(dict(family=family,filter_gain_at_1=sum(g['score']for g in rr if g['ratio']==1. and g['candidate_policy']=='NEGATIVE_FILTER')/2-sum(g['score']for g in rr if g['ratio']==1. and g['candidate_policy']=='PN')/2,filter_gain_at_point25=sum(g['score']for g in rr if g['ratio']==.25 and g['candidate_policy']=='NEGATIVE_FILTER')/2-sum(g['score']for g in rr if g['ratio']==.25 and g['candidate_policy']=='PN')/2))
 result=dict(status='PASS_ACTUAL_FIXED_CONDITIONS_ROLES_BUDGET_HISTORY_AND_OUTCOMES',task=task,logical=len(games),physical=len(physical),expected_logical=len(expected),missing=len(expected)-len(games),counts=dict(counts),cost_by_physical_condition_role={k:dict(v)for k,v in costs.items()},paired_family_price_gains=paired,paired_family_filter_gains=interaction,portable_actual_certificates_verified=len(certreceipts),offline_certificate_verifier_nodes=sum(r['nodes']for r in certreceipts),seconds=time.perf_counter()-start,TRAIN_selectors_independently_checked=lock is not None,scope='Actualphysicalrecords/literalCorefrontiers anddeclaredconditionprefixindependentlychecked. Familyunit, reusedrole notindependent. Costchangesincludechangedtrajectories/ordinaryload, notnoise-freespeedup. Partialslotsretained, noimplicitDRAW/DEV/selection. Offlineverificationpaidextra notoriginaldecisionbudget. 2120didnotsaveportablecerttrees: onlyexistingliveverifierreceipts/sourcechecked, noexternalall-defensereplayclaim forit.')
 (OUT/f'result-{task}.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k!='cost_by_physical_condition_role'}),flush=True)
if __name__=='__main__':audit(int(__import__('sys').argv[1]))
