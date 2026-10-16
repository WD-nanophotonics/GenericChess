"""Independent logical/physical actual-campaign, lock and cost audit."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,time,random,sys
from results.dev_aux.task2115.publication_pins import verify_publication_pins
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _same_state
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
def selector(rows,initial,grid):
 # Independently implement the frozen strict-neighbor rule from raw records.
 means={ratio:sum(g['score']for g in rows if g['ratio']==ratio)/sum(g['ratio']==ratio for g in rows)for ratio in grid};at=grid.index(initial);path=[initial]
 for _ in range(len(grid)):
  selected=None
  for nxt in(at-1,at+1):
   if 0<=nxt<len(grid)and means[grid[nxt]]>means[grid[at]]:selected=nxt;break
  if selected is None:break
  at=selected;path.append(grid[at])
 return dict(initial=initial,selected=grid[at],trace=path,TRAIN_means={str(k):v for k,v in means.items()})
OUT=Path('results/dev_aux/task2107')
def sha(s):return hashlib.sha256(repr(s).encode()).hexdigest()
def run(task=2105,publication_projection=None):
 start=time.perf_counter();root=Path(f'results/dev_aux/task{task}');p=json.loads((root/'study-freeze.json').read_text(encoding='utf-8'));d=json.loads((root/'completion.json').read_text(encoding='utf-8'));inputs=json.loads((root/'inputs.json').read_text(encoding='utf-8'))['roots'];pins=json.loads((root/'source-pin.json').read_text(encoding='utf-8'));source_check=verify_publication_pins(pins,publication_projection);raw=(root/'games.jsonl').read_bytes();games=[json.loads(x)for x in raw.splitlines()];moves=[json.loads(x)for x in(root/'moves.jsonl').read_text(encoding='utf-8').splitlines()];by=defaultdict(list)
 for m in moves:by[m['physical_id']].append(m)
 physical={};compiled={};sources=Counter();cost=Counter();outcomes=Counter();proofwins=0;outerlate=0
 for i,g in enumerate(games):
  assert g['logical_slot']==i and g['opponent_ratio']==1.
  if g['reused_from']is not None:
   old=games[g['reused_from']];assert old['reused_from']is None and old['physical_id']==g['physical_id']and old['ratio']==g['ratio']==1 and old['record']==g['record']and old['family']==g['family']and old['candidate_side']!=g['candidate_side'];assert g['score']is None if old['score']is None else g['score']==-old['score'];continue
  assert g['physical_id']not in physical;physical[g['physical_id']]=g
  if g['family']not in compiled:compiled[g['family']]=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[g['family']]['rules']).read_text(encoding='utf-8')))
  c=compiled[g['family']];s=GameSession(c);record=deserialize_game_record(json.dumps(g['record']));steps=by[g['physical_id']];assert len(steps)==g['moves']==len(record.actions);adopted=set();actor=RoyalActor(4)
  for ply,(m,a)in enumerate(zip(steps,record.actions)):
   assert m['ply']==ply and m['logical_slot']==i and sha(s.state)==m['before_state_sha']and s.state.position.side_to_move==m['side']and s.result.status is SessionStatus.ONGOING
   assert m['proof_nodes']<=p['proof_nodes']and m['search_nodes']<=p['normal_nodes']and m['verification_nodes']<=p['verification_nodes']and m['fill_verification_nodes']<=p['verification_nodes'];limits=m['phase_limits'];assert limits['normal_nodes']==p['normal_nodes']and limits['proof_nodes']==p['proof_nodes']and limits['normal_seconds']==p['normal_seconds']
   literal=dict(actor.moves(actor_state(s.state)));public={uci(x):x for x in s.legal_actions()};assert set(literal)==set(public)and uci(a)in public
   sources[m['source']]+=1
   for k in('proof_seconds','normal_seconds','seconds','proof_nodes','search_nodes'):cost[k]+=m[k]
   if m['source']=='PROOF':adopted.add(m['side'])
   for before,after in zip(m['before_ranks'],m['after_ranks']):
    if before is not None and before>0:assert after is not None and after<before
   s.submit(public[uci(a)]);assert actor_state(s.state)==literal[uci(a)]and sha(s.state)==m['after_state_sha']and dict(status=s.result.status.value,winner=s.result.winner)==m['result'];outerlate+=m['seconds']>p['step_seconds']
  replay=GameSession.replay(c,record);assert _same_state(replay.state,s.state)and replay.result==s.result and sha(s.state)==g['final_state_sha'];outcome='UNKNOWN'if s.result.status is SessionStatus.ONGOING else'DRAW'if s.result.winner is None else'WIN'if s.result.winner==g['candidate_side']else'LOSS';assert outcome==g['outcome']and g['score']==(None if outcome=='UNKNOWN'else 1 if outcome=='WIN'else-1 if outcome=='LOSS'else 0);outcomes[outcome]+=1
  if adopted and outcome!='UNKNOWN':assert len(adopted)==1 and s.result.winner==next(iter(adopted));proofwins+=1
 assert len(physical)==d['physical_games']and len(games)==d['logical_games']and len(moves)==d['physical_moves']
 train=[g for g in games if g['phase']=='TRAIN'];lock=root/'selector-lock.json';paired={}
 if lock.exists():
  l=json.loads(lock.read_text(encoding='utf-8'));assert len(train)==320 and all(g['score']is not None for g in train);assert hashlib.sha256(b''.join(raw.splitlines(keepends=True)[:320])).hexdigest()==l['source_TRAIN_games_sha'];assert [selector(train,x,p['ratios'])for x in p['initial_ratio']]==l['selected']==d['selected']
  for chosen in l['selected']:
   ratio=chosen['selected'];dev=[g for g in games if g['phase']=='DEV'and g['candidate_policy']=='TRIGGER'];ds=[]
   for family in range(32,48):
    a=[g for g in dev if g['family']==family and g['ratio']==ratio];b=[g for g in dev if g['family']==family and g['ratio']==1]
    if len(a)==len(b)==2 and all(g['score']is not None for g in a+b):ds.append(sum(g['score']for g in a)/2-sum(g['score']for g in b)/2)
   rng=random.Random(20261016712107);boot=sorted(sum(rng.choice(ds)for _ in ds)/len(ds)for _ in range(20000))if ds else[]
   paired[str(ratio)]=dict(initial=chosen['initial'],selected=ratio,complete_family_deltas=ds,mean=sum(ds)/len(ds)if ds else None,descriptive_family_bootstrap95=[boot[int(.025*len(boot))],boot[min(len(boot)-1,int(.975*len(boot)))]]if boot else None)
 else:assert not any(g['phase']=='DEV'for g in games)
 result=dict(publication_source_check=source_check,status='PASS_COMPLETE_ACTUAL_WL_PRICE_CONTROL'if d['status']=='COMPLETE'else'PASS_PARTIAL_ORIGINAL_CAP_PRESERVED',task=task,campaign_status=d['status'],physical_games=len(physical),logical_games=len(games),explicit_identity_reuses=len(games)-len(physical),physical_moves=len(moves),physical_outcomes=dict(outcomes),source_counts=dict(sources),paid_phases=dict(cost),finished_proof_adoptions_won=proofwins,outer_late_steps=outerlate,selector_locked=lock.exists(),DEV_price_gains=paired,TRAIN_logical=len(train),DEV_logical=sum(g['phase']=='DEV'for g in games),seconds=time.perf_counter()-start,scope='ActualruleW-Lonly/recordedfullhistories/unchangedsource/explicitphysicaldedup. Familyunit16DEVbootstrapdescriptive, no universalprice/stability/strengthclaim. Distinctinitialpricesmayremain distinct. NoDEV initial4control unlessfrozenprofileincluded; selectedvsbaseline1only. Original2100andnew2105notpooled/differentfixedopponentandresourcecontexts. Per-policyfullcertificatetreesnotarchived; actualexecutedverifiercounters/strategy-rank/physicalwinningoutcomes areaudited, separate2088certificatecapsulehasindependentall-defenseverification.')
 (OUT/f'result-{task}.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run(int(sys.argv[1])if len(sys.argv)>1 else 2105)
